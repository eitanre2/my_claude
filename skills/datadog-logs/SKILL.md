---
name: datadog-logs
description: Query and search Datadog logs for investigating and troubleshooting production issues. Use when user asks to "query Datadog", "check Datadog logs", "search Datadog", "find errors in Datadog", or mentions Datadog, DD logs, or production log investigation.
---

# Datadog Logs

Query logs from Datadog using the Logs Search API v2. Supports filtering by time range, status, service, host, and arbitrary facets with text, JSON, or CSV output. Includes automatic pagination for large result sets.

## Setup

### Credentials

Add to `~/.claude/credentials.json`:

```json
{
  "datadog": {
    "api_key": "YOUR_DD_API_KEY",
    "app_key": "YOUR_DD_APPLICATION_KEY",
    "site": "datadoghq.com"
  }
}
```

### Verify Setup

```bash
python3 scripts/datadog_client.py --query "*" --limit 5
```

## Instructions

All scripts use paths relative to this skill's directory (`skills/datadog-logs/`).

### Step 1: Build your query

Parameters:
- `--query, -q` — Datadog search query (default: "*"). Uses [Datadog search syntax](https://docs.datadoghq.com/logs/explorer/search_syntax/)
- `--hours` — Hours to look back (default: 1)
- `--from-time` — Explicit start time (ISO-8601 or relative like "now-2h")
- `--to-time` — Explicit end time (ISO-8601 or relative like "now")
- `--limit, -l` — Maximum logs to return (default: 100, max: 5000 with pagination)
- `--status` — Filter by status: error, warn, info, debug, emergency, alert, critical
- `--service, -s` — Filter by service name
- `--host` — Filter by host name
- `--tags` — Filter by tags (comma-separated)

### Step 2: Choose output format

- `--format, -f` — Output format: text (default), json, csv
- `--output, -o` — Output file path (default: stdout)

### Step 3: Run the query

```bash
# Recent errors
python3 scripts/datadog_client.py --status error --hours 2

# Errors from a specific service
python3 scripts/datadog_client.py --service rails --status error --hours 1

# Free-text search
python3 scripts/datadog_client.py --query "timeout OR connection refused" --hours 6

# Filter by host
python3 scripts/datadog_client.py --host i-0abc123 --status error --hours 4

# Complex Datadog query
python3 scripts/datadog_client.py --query "@http.status_code:500 service:web" --hours 1

# Export to JSON
python3 scripts/datadog_client.py --status error --format json --output errors.json

# Large result set with pagination
python3 scripts/datadog_client.py --query "exception" --hours 12 --limit 2000
```

## Query Syntax Quick Reference

Datadog uses its own search syntax:

| Pattern | Example |
|---------|---------|
| Free text | `timeout` |
| Attribute match | `@http.status_code:500` |
| Service filter | `service:web` |
| Host filter | `host:i-0abc123` |
| Status filter | `status:error` |
| Wildcard | `service:web*` |
| Negation | `-status:info` |
| Range | `@duration:>1000` |
| Combination | `service:web AND status:error` |
| Grouping | `(status:error OR status:critical) service:api` |

## Search Hints

### Searching by controller and action

When asked about a specific controller action, use the `action` and `controller` fields in the query. The controller name should match the Ruby class name (e.g., `UsersController`, not `users_controller`).

```bash
# Requests to the "invite" action in UsersController
python3 scripts/datadog_client.py --query "action:invite AND controller:UsersController"

# Requests to the "create" action in AddonController
python3 scripts/datadog_client.py --query "action:create AND controller:AddonController"
```

### Searching by HTTP status code

Use both `status` and `response` fields combined with `OR`. The `response` field typically appears in nginx log records, while `status` appears in requests that reached Rails code.

```bash
# Requests with HTTP 502
python3 scripts/datadog_client.py --query "status:502 OR response:502"

# Requests with HTTP 429 in the last 6 hours
python3 scripts/datadog_client.py --query "status:429 OR response:429" --hours 6
```

## Examples

- "Show me errors from the last hour in Datadog"
- "Search Datadog for timeout errors in the rails service"
- "Query Datadog logs for 500 errors from the last 6 hours"
- "Find all critical logs from host i-0abc123"
- "Check Datadog for database connection issues today"

## Troubleshooting

### 403 Forbidden
Verify both API key and Application key are correct and have log read permissions.

### No Logs Found
1. Try increasing `--hours`
2. Check query syntax — use `--query "*"` to confirm connectivity
3. Verify the service/host names are correct
