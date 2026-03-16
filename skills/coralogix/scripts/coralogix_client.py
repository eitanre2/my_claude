#!/usr/bin/env python3
"""
Coralogix API Client for querying and retrieving logs
"""

import os
import sys
import json
import argparse
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
import urllib.request
import urllib.parse
import urllib.error


class CoralogixClient:
    """Client for interacting with Coralogix API"""

    def __init__(self, api_key: Optional[str] = None, api_url: Optional[str] = None):
        self.api_key = api_key or os.getenv('CORALOGIX_API_KEY')
        self.api_url = api_url or os.getenv('CORALOGIX_API_URL', 'https://api.us2.coralogix.com')

        # Try to load from credentials.json if API key not provided
        if not self.api_key:
            credentials_path = os.path.expanduser('~/.claude/credentials.json')
            try:
                with open(credentials_path, 'r') as f:
                    credentials = json.load(f)
                    coralogix_creds = credentials.get('coralogix', {})
                    # Support both 'personal_key' and 'peronal_key' (typo)
                    self.api_key = coralogix_creds.get('personal_key') or coralogix_creds.get('peronal_key')
                    # Also try to get API URL from credentials
                    self.api_url = coralogix_creds.get('api_url', self.api_url)
            except (FileNotFoundError, json.JSONDecodeError, KeyError):
                pass

        if not self.api_key:
            raise ValueError(
                "Coralogix API key not found. Please set it in one of these ways:\n"
                "1. Environment variable: export CORALOGIX_API_KEY='your-key'\n"
                "2. Add to ~/.claude/credentials.json: {\"coralogix\": {\"personal_key\": \"your-key\"}}\n"
                "3. Pass api_key parameter to this function\n\n"
                "Get your API key from: https://cloudinary-production.app.cx498.coralogix.com/ → Settings → API Keys"
            )

    def _make_request(self, endpoint: str, method: str = 'POST', data: Optional[Dict] = None) -> Dict:
        """Make HTTP request to Coralogix API"""
        url = f"{self.api_url}{endpoint}"
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Coralogix-Client/1.0)'
        }

        req_data = json.dumps(data).encode('utf-8') if data else None
        request = urllib.request.Request(url, data=req_data, headers=headers, method=method)

        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                response_text = response.read().decode('utf-8')

                # Coralogix API returns NDJSON (Newline Delimited JSON)
                # Parse each line as a separate JSON object
                lines = response_text.strip().split('\n')
                result = {}
                for line in lines:
                    if line.strip():
                        parsed = json.loads(line)
                        result.update(parsed)

                return result
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8')
            raise Exception(f"HTTP {e.code}: {error_body}")
        except urllib.error.URLError as e:
            raise Exception(f"Connection error: {e.reason}")

    def query_logs(
        self,
        query: str = "*",
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
        severity: Optional[List[str]] = None,
        application: Optional[str] = None,
        subsystem: Optional[str] = None,
        raw_dataprime: Optional[str] = None
    ) -> Dict:
        """
        Query logs from Coralogix

        Args:
            query: Text search query (searches in log content)
            start_time: Start of time range (default: 1 hour ago)
            end_time: End of time range (default: now)
            limit: Maximum number of logs to return
            severity: Filter by severity levels (e.g., ['ERROR', 'WARN'])
            application: Filter by application name
            subsystem: Filter by subsystem name
            raw_dataprime: Raw DataPrime query string (overrides all other filters)

        Returns:
            Dictionary containing query results
        """
        if start_time is None:
            start_time = datetime.now(timezone.utc) - timedelta(hours=1)
        if end_time is None:
            end_time = datetime.now(timezone.utc)

        # Use raw DataPrime query if provided
        if raw_dataprime:
            dataprime_query = raw_dataprime
        else:
            # Build DataPrime query
            dataprime_query = "source logs"

            # Add filters
            filters = []
            if query and query != "*":
                # Search in userData field using contains (case-insensitive)
                filters.append(f'$d.userData.string_value.contains({repr(query)})')
            if severity:
                # Normalize severity names (WARN -> WARNING)
                severity_map = {'WARN': 'WARNING'}
                normalized_severity = [severity_map.get(sev.upper(), sev.upper()) for sev in severity]
                severity_filter = ' || '.join([f'$m.severity == Severity.{sev}' for sev in normalized_severity])
                filters.append(f'({severity_filter})')
            if application:
                filters.append(f'$l.applicationname == {repr(application)}')
            if subsystem:
                filters.append(f'$l.subsystemname == {repr(subsystem)}')

            if filters:
                dataprime_query += ' | filter ' + ' && '.join(filters)

            dataprime_query += f' | limit {limit}'

        payload = {
            "query": dataprime_query,
            "metadata": {
                "syntax": "QUERY_SYNTAX_DATAPRIME",
                "startDate": start_time.strftime('%Y-%m-%dT%H:%M:%S.00Z'),
                "endDate": end_time.strftime('%Y-%m-%dT%H:%M:%S.00Z'),
                "defaultSource": "logs"
            }
        }

        response = self._make_request('/api/v1/dataprime/query', data=payload)

        # Parse the Coralogix response format
        results = response.get('result', {}).get('results', [])

        # Transform to a more usable format
        logs = []
        for result in results:
            log_entry = {}

            # Extract metadata
            metadata = {item['key']: item['value'] for item in result.get('metadata', [])}
            log_entry['timestamp'] = metadata.get('timestamp', '')
            log_entry['severity'] = metadata.get('severity', '')

            # Extract labels
            labels = {item['key']: item['value'] for item in result.get('labels', [])}
            log_entry['applicationName'] = labels.get('applicationname', '')
            log_entry['subsystemName'] = labels.get('subsystemname', '')

            # Parse userData JSON string
            user_data_str = result.get('userData', '{}')
            try:
                user_data = json.loads(user_data_str)
                log_entry['text'] = user_data.get('message', user_data_str[:200])
                log_entry['userData'] = user_data
            except json.JSONDecodeError:
                log_entry['text'] = user_data_str[:200]
                log_entry['userData'] = {}

            logs.append(log_entry)

        return {'logs': logs, 'queryId': response.get('queryId', {})}

    def format_logs(self, logs: List[Dict], format_type: str = 'text') -> str:
        """Format logs for display"""
        if format_type == 'json':
            return json.dumps(logs, indent=2)
        elif format_type == 'csv':
            if not logs:
                return "timestamp,severity,application,message\n"

            lines = ["timestamp,severity,application,message"]
            for log in logs:
                timestamp = log.get('timestamp', '')
                severity = log.get('severity', '')
                app = log.get('applicationName', '')
                message = log.get('text', '').replace('"', '""')
                lines.append(f'{timestamp},{severity},{app},"{message}"')
            return '\n'.join(lines)
        else:  # text
            if not logs:
                return "No logs found."

            lines = []
            for log in logs:
                # Parse ISO timestamp format
                timestamp_str = log.get('timestamp', '')
                try:
                    if timestamp_str:
                        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M:%S')
                    else:
                        timestamp = 'unknown'
                except (ValueError, AttributeError):
                    timestamp = timestamp_str[:19] if len(timestamp_str) >= 19 else timestamp_str

                # Map severity numbers to names
                severity_map = {'1': 'VERBOSE', '2': 'DEBUG', '3': 'INFO', '4': 'WARN', '5': 'ERROR', '6': 'CRITICAL'}
                severity = severity_map.get(log.get('severity', ''), log.get('severity', 'INFO'))

                app = log.get('applicationName', 'unknown')
                message = log.get('text', '')
                lines.append(f"[{timestamp}] {severity:8s} [{app}] {message}")
            return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description='Query Coralogix logs')
    parser.add_argument('--query', '-q', default='*', help='Text search query')
    parser.add_argument('--dataprime', '-d', help='Raw DataPrime query (overrides other filters)')
    parser.add_argument('--hours', type=int, default=1, help='Hours to look back (default: 1)')
    parser.add_argument('--limit', '-l', type=int, default=100, help='Maximum logs to return')
    parser.add_argument('--severity', nargs='+', help='Filter by severity (ERROR, WARNING, INFO, DEBUG, VERBOSE, CRITICAL)')
    parser.add_argument('--application', '-a', help='Filter by application name')
    parser.add_argument('--subsystem', '-s', help='Filter by subsystem name')
    parser.add_argument('--format', '-f', choices=['text', 'json', 'csv'], default='text', help='Output format')
    parser.add_argument('--output', '-o', help='Output file (default: stdout)')

    args = parser.parse_args()

    try:
        client = CoralogixClient()

        start_time = datetime.now(timezone.utc) - timedelta(hours=args.hours)
        end_time = datetime.now(timezone.utc)

        if args.dataprime:
            print(f"Querying Coralogix with DataPrime: '{args.dataprime[:50]}...'", file=sys.stderr)
        else:
            print(f"Querying Coralogix: '{args.query}' (last {args.hours} hour(s))", file=sys.stderr)

        result = client.query_logs(
            query=args.query,
            start_time=start_time,
            end_time=end_time,
            limit=args.limit,
            severity=args.severity,
            application=args.application,
            subsystem=args.subsystem,
            raw_dataprime=args.dataprime
        )

        logs = result.get('logs', [])
        print(f"Found {len(logs)} logs", file=sys.stderr)

        formatted_output = client.format_logs(logs, args.format)

        if args.output:
            with open(args.output, 'w') as f:
                f.write(formatted_output)
            print(f"Output saved to {args.output}", file=sys.stderr)
        else:
            print(formatted_output)

        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
