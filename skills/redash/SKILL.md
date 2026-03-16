---
name: redash
description: Execute SQL queries and retrieve data from Redash analytics platform. Use when user asks to "query Redash", "run a SQL query", "search Redash", "list data sources", mentions Redash, or asks database questions like "how many customers" or "show me users".
---

# Redash Query Tool

Execute SQL queries, list queries, get query results, and manage data sources on the Redash analytics platform.

## Setup

1. Add credentials to `../../credentials.json`:

```json
{
  "redash": {
    "api_key": "your_redash_api_key",
    "base_url": "https://redash.cloudinary.com",
    "proxy": "socks5h://localhost:8080"
  }
}
```

Alternatively, set environment variables:
```bash
export REDASH_API_KEY="your_api_key"
export REDASH_BASE_URL="https://redash.cloudinary.com"
export REDASH_PROXY="socks5h://localhost:8080"
```

2. Install dependencies:

```bash
pip3 install requests[socks]
```

## Usage

The skill supports:
- **Executing SQL queries** on any data source
- **Listing available queries** and data sources
- **Getting query results** by query ID
- **Creating new ad-hoc queries**
- **Searching for queries** by name or keywords

## Examples

### Using Claude Code
Ask naturally:
- "Query Redash for the first 10 users"
- "Show me all data sources in Redash"
- "Run query 1234 from Redash"
- "Search Redash for queries about accounts"
- "Create a Redash query to count customers"
- "How many customers are in the database?"

### Command Line Examples
```bash
# Execute a SQL query on a specific data source
python3 scripts/redash_client.py \
  --data-source-id 2 \
  --query "SELECT * FROM accounts LIMIT 10"

# List available queries
python3 scripts/redash_client.py --list-queries

# Get results of a specific query
python3 scripts/redash_client.py --query-id 1234

# List data sources
python3 scripts/redash_client.py --list-data-sources

# Search for queries
python3 scripts/redash_client.py --search "accounts"

# Output as JSON
python3 scripts/redash_client.py \
  --list-queries \
  --format json \
  --output queries.json
```

## API Details

- **Base URL**: Configurable (e.g., https://redash.cloudinary.com)
- **Authentication**: API Key via Authorization header
- **Proxy Support**: SOCKS5 proxy for network access. If the proxy is unreachable (e.g. connection refused), the client automatically retries without proxy and uses direct connection for the rest of the session.
- **Response Format**: JSON

## Common Data Sources
- shard1_slave (ID: 2) - Main production database
- shard11_slave (ID: 7)
- shard12_slave (ID: 9)
- shard13_slave (ID: 12)
- See full list with `--list-data-sources`

## Troubleshooting

### Proxy Connection Issues
- Ensure the SOCKS proxy is running on localhost:8080
- Check that the proxy supports SOCKS5h protocol (DNS resolution through proxy)
- Verify network connectivity to Redash server

### Authentication Errors
- Verify your API key is correct in credentials.json
- Check that the API key has appropriate permissions
- Ensure the base_url points to the correct Redash instance

### Query Timeout
- Large queries may take longer than the default timeout
- Consider adding LIMIT clauses to large queries
- Check query complexity and optimize if needed
