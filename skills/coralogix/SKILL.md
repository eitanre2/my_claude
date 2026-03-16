---
name: coralogix
description: Query and retrieve logs from Coralogix using the DataPrime API. Use when user asks to "query Coralogix", "check Coralogix logs", "find errors in Coralogix", "show logs from Coralogix", or mentions Coralogix, DataPrime, or production log search.
---

# Coralogix Log Query

Query logs from Coralogix using the Direct Archive Query (DataPrime) API. Supports filtering by time range, severity, application, and subsystem with text, JSON, or CSV output.

## Setup

### 1. Get Your Coralogix API Key

1. Log in: https://cloudinary-production.app.cx498.coralogix.com/
2. Navigate to **Settings** > **API Keys**
3. Generate or copy a key

### 2. Configure Credentials

Add to `../../credentials.json`:

```json
{
  "coralogix": {
    "personal_key": "cxup_YourApiKeyHere",
    "api_url": "https://api.us2.coralogix.com"
  }
}
```

Alternatively, set environment variables:
```bash
export CORALOGIX_API_KEY="cxup_YourApiKeyHere"
export CORALOGIX_API_URL="https://api.us2.coralogix.com"
```

### 3. Verify Setup

```bash
python3 scripts/coralogix_client.py --query "*" --limit 10
```

## Instructions

### Step 1: Build your query

Parameters:
- `--query, -q` — Lucene query string (default: "*")
- `--hours` — Hours to look back (default: 1)
- `--limit, -l` — Maximum logs to return (default: 100)
- `--severity` — Filter by severity: ERROR, WARN, INFO, DEBUG, CRITICAL
- `--application, -a` — Filter by application name
- `--subsystem, -s` — Filter by subsystem name
- `--dataprime` — Raw DataPrime query string (advanced)

### Step 2: Choose output format

- `--format, -f` — Output format: text (default), json, csv
- `--output, -o` — Output file path (default: stdout)

### Step 3: Run the query

```bash
python3 scripts/coralogix_client.py --severity ERROR --hours 2
python3 scripts/coralogix_client.py --application rails --severity ERROR WARNING --hours 1
python3 scripts/coralogix_client.py --query "database AND timeout" --hours 12
python3 scripts/coralogix_client.py --format json --output logs.json
```

For DataPrime syntax and advanced query examples, see `references/EXAMPLES.md`.

## Examples

- "Show me the last 10 logs from Coralogix"
- "Find ERROR logs from the last 2 hours"
- "Query Coralogix for logs from the 'rails' application"
- "Search Coralogix logs for 'database timeout'"
- "Analyze error patterns in Coralogix from today"

## Troubleshooting

### Authentication Error
1. Verify your API key is correct
2. Check the environment variable: `echo $CORALOGIX_API_KEY`
3. Reload shell after setting the variable

### Connection Error
1. Verify your API URL is correct
2. Check internet connectivity
3. Ensure Coralogix URL is accessible

### No Logs Found
1. Try increasing `--hours`
2. Check query syntax
3. Try a broader query: `--query "*"`
