#!/usr/bin/env python3
"""
Redash API Client for Claude Code
Query and manage Redash analytics platform
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Any

try:
    import requests
except ImportError:
    print("Error: requests library not installed. Install with: pip3 install requests[socks]")
    sys.exit(1)


class RedashClient:
    """Client for interacting with Redash API"""

    def __init__(self, api_key: str, base_url: str, proxy: Optional[str] = None):
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.proxy = proxy
        self.headers = {
            'Authorization': f'Key {api_key}',
            'Content-Type': 'application/json'
        }
        self.proxies = {'http': proxy, 'https': proxy} if proxy else None

    def _request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make HTTP request with proxy support. Retries without proxy if proxy fails."""
        url = f"{self.base_url}{endpoint}"
        kwargs['headers'] = self.headers
        if self.proxies:
            kwargs['proxies'] = self.proxies

        try:
            response = requests.request(method, url, **kwargs)
            response.raise_for_status()
            return response
        except (requests.exceptions.ConnectionError, requests.exceptions.ProxyError) as e:
            # If we used a proxy and it failed (e.g. connection refused), retry without proxy
            if self.proxies:
                self.proxies = None
                kwargs.pop('proxies', None)
                response = requests.request(method, url, **kwargs)
                response.raise_for_status()
                return response
            raise

    def list_queries(self, limit: int = 25, page: int = 1) -> Dict[str, Any]:
        """List available queries"""
        params = {'page': page, 'page_size': limit}
        response = self._request('GET', '/api/queries', params=params)
        return response.json()

    def list_data_sources(self) -> List[Dict[str, Any]]:
        """List all data sources"""
        response = self._request('GET', '/api/data_sources')
        return response.json()

    def get_query(self, query_id: int) -> Dict[str, Any]:
        """Get query details by ID"""
        response = self._request('GET', f'/api/queries/{query_id}')
        return response.json()

    def create_query(self, query: str, data_source_id: int, name: str = "New Query",
                     is_draft: bool = True) -> Dict[str, Any]:
        """Create a new query"""
        data = {
            'query': query,
            'data_source_id': data_source_id,
            'name': name,
            'is_draft': is_draft
        }
        response = self._request('POST', '/api/queries', json=data)
        return response.json()

    def execute_query(self, query_id: int, parameters: Optional[Dict] = None) -> Dict[str, Any]:
        """Execute a query and return results"""
        # Start query execution
        data = parameters if parameters else {}
        response = self._request('POST', f'/api/queries/{query_id}/results', json=data)
        job = response.json()

        job_id = job['job']['id']

        # Poll for results
        max_attempts = 60
        for attempt in range(max_attempts):
            time.sleep(1)
            response = self._request('GET', f'/api/jobs/{job_id}')
            job_status = response.json()

            status = job_status['job']['status']
            if status == 3:  # Success
                query_result_id = job_status['job']['query_result_id']
                return self.get_query_result(query_result_id)
            elif status == 4:  # Failed
                error = job_status['job'].get('error', 'Unknown error')
                raise Exception(f"Query failed: {error}")

        raise Exception("Query timeout: exceeded maximum wait time")

    def get_query_result(self, query_result_id: int) -> Dict[str, Any]:
        """Get query result by ID"""
        response = self._request('GET', f'/api/query_results/{query_result_id}')
        return response.json()

    def run_adhoc_query(self, query: str, data_source_id: int) -> Dict[str, Any]:
        """Create and execute an ad-hoc query"""
        # Create the query
        query_data = self.create_query(query, data_source_id,
                                       name=f"Ad-hoc: {query[:50]}")
        query_id = query_data['id']

        # Execute it
        try:
            result = self.execute_query(query_id)
            return result
        finally:
            # Optionally delete the ad-hoc query
            pass

    def search_queries(self, search_term: str, limit: int = 25) -> List[Dict[str, Any]]:
        """Search for queries by name or keywords"""
        response = self._request('GET', '/api/queries',
                                params={'q': search_term, 'page_size': limit})
        return response.json()


def load_credentials() -> Dict[str, str]:
    """Load credentials from environment or config file"""
    # Try environment variables first
    api_key = os.getenv('REDASH_API_KEY')
    base_url = os.getenv('REDASH_BASE_URL')
    proxy = os.getenv('REDASH_PROXY')

    # Try credentials file if env vars not set
    if not api_key or not base_url or proxy is None:
        creds_file = Path.home() / '.claude' / 'credentials.json'
        if creds_file.exists():
            with open(creds_file) as f:
                creds = json.load(f)
                redash_creds = creds.get('redash', {})
                api_key = api_key or redash_creds.get('api_key')
                base_url = base_url or redash_creds.get('base_url')
                # Only use proxy from file if env didn't set it (use proxy on EC2, skip locally)
                if proxy is None:
                    proxy = redash_creds.get('proxy')

    if not api_key or not base_url:
        raise ValueError(
            "Missing credentials. Set REDASH_API_KEY and REDASH_BASE_URL "
            "environment variables or add to ~/.claude/credentials.json"
        )

    return {
        'api_key': api_key,
        'base_url': base_url,
        'proxy': proxy
    }


def format_output(data: Any, format_type: str = 'text') -> str:
    """Format output data"""
    if format_type == 'json':
        return json.dumps(data, indent=2)
    elif format_type == 'text':
        if isinstance(data, dict):
            if 'query_result' in data:
                # Format query results
                result = data['query_result']['data']
                rows = result['rows']
                if not rows:
                    return "No results"

                columns = [col['name'] for col in result['columns']]

                # Simple table format
                output = []
                output.append(' | '.join(columns))
                output.append('-' * (sum(len(c) for c in columns) + len(columns) * 3))

                for row in rows[:50]:  # Limit to 50 rows for display
                    values = [str(row.get(col, '')) for col in columns]
                    output.append(' | '.join(values))

                if len(rows) > 50:
                    output.append(f"\n... and {len(rows) - 50} more rows")

                return '\n'.join(output)
            else:
                return json.dumps(data, indent=2)
        else:
            return json.dumps(data, indent=2)
    else:
        return str(data)


def main():
    parser = argparse.ArgumentParser(description='Redash API Client')

    # Query operations
    parser.add_argument('--query', help='SQL query to execute')
    parser.add_argument('--data-source-id', type=int, help='Data source ID')
    parser.add_argument('--query-id', type=int, help='Execute existing query by ID')

    # List operations
    parser.add_argument('--list-queries', action='store_true', help='List available queries')
    parser.add_argument('--list-data-sources', action='store_true',
                       help='List available data sources')
    parser.add_argument('--search', help='Search for queries')

    # Output options
    parser.add_argument('--format', choices=['text', 'json'], default='text',
                       help='Output format')
    parser.add_argument('--output', help='Output file path')
    parser.add_argument('--limit', type=int, default=25, help='Limit results')

    args = parser.parse_args()

    try:
        # Load credentials
        creds = load_credentials()
        client = RedashClient(creds['api_key'], creds['base_url'], creds.get('proxy'))

        result = None

        # Execute operations
        if args.list_data_sources:
            result = client.list_data_sources()
        elif args.list_queries:
            result = client.list_queries(limit=args.limit)
        elif args.search:
            result = client.search_queries(args.search, limit=args.limit)
        elif args.query_id:
            result = client.execute_query(args.query_id)
        elif args.query and args.data_source_id:
            result = client.run_adhoc_query(args.query, args.data_source_id)
        else:
            parser.print_help()
            return

        # Format and output
        output = format_output(result, args.format)

        if args.output:
            with open(args.output, 'w') as f:
                f.write(output)
            print(f"Output written to {args.output}")
        else:
            print(output)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
