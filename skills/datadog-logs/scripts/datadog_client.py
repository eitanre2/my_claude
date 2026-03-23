#!/usr/bin/env python3
"""Datadog Logs Search API v2 client for querying and retrieving logs."""

import os
import sys
import json
import argparse
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
import urllib.request
import urllib.error


class DatadogClient:
    """Client for querying Datadog Logs Search API v2."""

    def __init__(self, api_key: Optional[str] = None, app_key: Optional[str] = None, site: Optional[str] = None):
        self.api_key = api_key or os.getenv('DD_API_KEY')
        self.app_key = app_key or os.getenv('DD_APP_KEY')
        self.site = site or os.getenv('DD_SITE', 'datadoghq.com')

        if not self.api_key or not self.app_key:
            self._load_credentials()

        if not self.api_key or not self.app_key:
            raise ValueError(
                "Datadog credentials not found. Configure in one of these ways:\n"
                "1. Add to ~/.claude/credentials.json:\n"
                '   {"datadog": {"api_key": "...", "app_key": "...", "site": "datadoghq.com"}}\n'
                "2. Environment variables: DD_API_KEY, DD_APP_KEY, DD_SITE\n"
            )

    def _load_credentials(self):
        credentials_path = os.path.expanduser('~/.claude/credentials.json')
        try:
            with open(credentials_path, 'r') as f:
                creds = json.load(f).get('datadog', {})
                self.api_key = self.api_key or creds.get('api_key')
                self.app_key = self.app_key or creds.get('app_key')
                self.site = creds.get('site', self.site)
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            pass

    def _request(self, endpoint: str, data: Dict) -> Dict:
        url = f"https://api.{self.site}{endpoint}"
        headers = {
            'Content-Type': 'application/json',
            'DD-API-KEY': self.api_key,
            'DD-APPLICATION-KEY': self.app_key,
        }
        body = json.dumps(data).encode('utf-8')
        req = urllib.request.Request(url, data=body, headers=headers, method='POST')
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8')
            raise Exception(f"HTTP {e.code}: {error_body}")
        except urllib.error.URLError as e:
            raise Exception(f"Connection error: {e.reason}")

    def search_logs(
        self,
        query: str = "*",
        from_time: Optional[str] = None,
        to_time: Optional[str] = None,
        hours: int = 1,
        limit: int = 100,
        status: Optional[List[str]] = None,
        service: Optional[str] = None,
        host: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> List[Dict]:
        """Search logs with automatic pagination up to `limit` results."""
        query_parts = [query] if query and query != "*" else []

        if status:
            status_filter = ' OR '.join(f'status:{s}' for s in status)
            query_parts.append(f'({status_filter})' if len(status) > 1 else f'status:{status[0]}')
        if service:
            query_parts.append(f'service:{service}')
        if host:
            query_parts.append(f'host:{host}')
        if tags:
            for tag in tags:
                query_parts.append(f'tags:{tag}')

        final_query = ' '.join(query_parts) if query_parts else '*'

        if not from_time:
            from_time = (datetime.now(timezone.utc) - timedelta(hours=hours)).strftime('%Y-%m-%dT%H:%M:%S+00:00')
        if not to_time:
            to_time = 'now'

        all_logs = []
        cursor = None
        page_size = min(limit, 1000)

        while len(all_logs) < limit:
            remaining = limit - len(all_logs)
            current_page_size = min(remaining, page_size)

            payload = {
                "filter": {
                    "query": final_query,
                    "from": from_time,
                    "to": to_time,
                },
                "sort": "-timestamp",
                "page": {"limit": current_page_size},
            }
            if cursor:
                payload["page"]["cursor"] = cursor

            response = self._request('/api/v2/logs/events/search', payload)

            data = response.get('data', [])
            if not data:
                break

            for entry in data:
                attrs = entry.get('attributes', {})
                all_logs.append({
                    'id': entry.get('id', ''),
                    'timestamp': attrs.get('timestamp', ''),
                    'status': attrs.get('status', ''),
                    'service': attrs.get('service', ''),
                    'host': attrs.get('host', ''),
                    'message': attrs.get('message', ''),
                    'tags': attrs.get('tags', []),
                    'attributes': attrs.get('attributes', {}),
                })

            cursor = response.get('meta', {}).get('page', {}).get('after')
            if not cursor:
                break

        return all_logs

    def format_logs(self, logs: List[Dict], fmt: str = 'text') -> str:
        if fmt == 'json':
            return json.dumps(logs, indent=2)

        if fmt == 'csv':
            lines = ['timestamp,status,service,host,message']
            for log in logs:
                msg = log.get('message', '').replace('"', '""').replace('\n', ' ')[:500]
                lines.append(f'{log["timestamp"]},{log["status"]},{log["service"]},{log["host"]},"{msg}"')
            return '\n'.join(lines)

        if not logs:
            return "No logs found."

        lines = []
        for log in logs:
            ts = log.get('timestamp', '')
            try:
                ts = datetime.fromisoformat(ts.replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M:%S')
            except (ValueError, AttributeError):
                pass
            status = (log.get('status', '') or 'info').upper()
            service = log.get('service', '-')
            host = log.get('host', '-')
            msg = log.get('message', '').replace('\n', ' ')[:300]
            lines.append(f"[{ts}] {status:8s} [{service}] [{host}] {msg}")
        return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description='Search Datadog logs')
    parser.add_argument('--query', '-q', default='*', help='Datadog search query (default: "*")')
    parser.add_argument('--hours', type=int, default=1, help='Hours to look back (default: 1)')
    parser.add_argument('--from-time', help='Start time (ISO-8601 or relative like "now-2h")')
    parser.add_argument('--to-time', help='End time (ISO-8601 or relative like "now")')
    parser.add_argument('--limit', '-l', type=int, default=100, help='Max logs to return (default: 100)')
    parser.add_argument('--status', nargs='+', help='Filter by status (error, warn, info, debug, critical, alert, emergency)')
    parser.add_argument('--service', '-s', help='Filter by service name')
    parser.add_argument('--host', help='Filter by host')
    parser.add_argument('--tags', help='Filter by tags (comma-separated)')
    parser.add_argument('--format', '-f', choices=['text', 'json', 'csv'], default='text', help='Output format')
    parser.add_argument('--output', '-o', help='Output file (default: stdout)')

    args = parser.parse_args()

    try:
        client = DatadogClient()

        tag_list = [t.strip() for t in args.tags.split(',')] if args.tags else None

        print(f"Querying Datadog: '{args.query}' (last {args.hours}h, limit {args.limit})", file=sys.stderr)

        logs = client.search_logs(
            query=args.query,
            from_time=args.from_time,
            to_time=args.to_time,
            hours=args.hours,
            limit=args.limit,
            status=args.status,
            service=args.service,
            host=args.host,
            tags=tag_list,
        )

        print(f"Found {len(logs)} logs", file=sys.stderr)

        output = client.format_logs(logs, args.format)

        if args.output:
            with open(args.output, 'w') as f:
                f.write(output)
            print(f"Output saved to {args.output}", file=sys.stderr)
        else:
            print(output)

        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
