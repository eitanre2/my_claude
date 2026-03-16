---
name: jenkins-reader
description: Read and analyze Jenkins job outputs, console logs, and build failures. Use when user asks to "analyze jenkins", "check jenkins", "jenkins job", mentions a build number, asks about test failures, or any Jenkins-related request.
metadata:
  version: 1.2.0
  author: Eitan Revach
---

# Jenkins Job Reader

Read Jenkins job outputs, console logs, and build history from Cloudinary's Jenkins instance.

## Configuration

- **Jenkins URL**: https://jenkins.cloudinary.com/
- **Username**: eitan.revach@cloudinary.com
- **Proxy**: SOCKS5 proxy at `socks5h://localhost:8080`
- **Credentials**: Automatically searched in `credentials.json` — JSON format: `{"jenkins": {"key": "JENKINS=TOKEN"}}`
- **Local cache**: `/tmp/jenkins_builds/<JOB_NAME>/<BUILD_NUMBER>/` with `console.txt`, `info.json`, `reports/`

CRITICAL: If curl commands fail with connection errors, ask the user to check if the proxy is running.

## Known Jobs

- `Staging2-CI-PR` — Staging CI Pull Request builds

## Instructions

### Step 1: Parse the request

Identify job name (from known jobs or user-provided), build number (default: "lastBuild"), and what to retrieve (console output, status, history). Check local cache first before fetching from Jenkins.

### Step 2: Read credentials

Search for credentials in order:
- `~/.claude/credentials.json`
- `<project-name>/.claude/credentials.json`

Extract token: `TOKEN=$(cat /path/credentials.json | jq -r '.jenkins.key' | cut -d'=' -f2)`

### Step 3: Fetch information

CRITICAL: Always use the full token value directly in curl commands. Do NOT use command substitution.

Save output to local cache folder.

```bash
# Console output
curl -x socks5h://localhost:8080 -s -u "eitan.revach@cloudinary.com:TOKEN_VALUE" \
  "https://jenkins.cloudinary.com/job/{JOB_NAME}/{BUILD_NUMBER}/consoleText"

# Build info
curl -x socks5h://localhost:8080 -s -u "eitan.revach@cloudinary.com:TOKEN_VALUE" \
  "https://jenkins.cloudinary.com/job/{JOB_NAME}/{BUILD_NUMBER}/api/json"

# Job history (last 10 builds)
curl -x socks5h://localhost:8080 -s -u "eitan.revach@cloudinary.com:TOKEN_VALUE" \
  "https://jenkins.cloudinary.com/job/{JOB_NAME}/api/json?tree=builds[number,result,timestamp,duration,url]{0,9}"
```

### Step 4: Present results

- Console output: show last 100 lines by default
- Build status: show build number, result, duration, timestamp
- History: show a table of recent builds

### Step 5: Analyze failures (when requested)

Run analysis scripts from `scripts/` directory. For detailed script documentation, see `references/analysis-scripts.md`.

```bash
CONSOLE_FILE="path/to/console.txt"

python3 scripts/extract_test_summary.py $CONSOLE_FILE
python3 scripts/analyze_error_patterns.py $CONSOLE_FILE
python3 scripts/categorize_failures.py $CONSOLE_FILE
python3 scripts/identify_test_groups.py $CONSOLE_FILE
```

Present comprehensive report: executive summary, breakdown by area, root causes by frequency, top failing test groups, and recommendations.

For error pattern details, see `references/error-patterns.md`.
For API endpoints and build search, see `references/api-reference.md`.

## Examples

- "Show me the console output for Staging2-CI-PR build 456"
- "What's the status of the last Staging2-CI-PR build?"
- "Analyze jenkins job 95060, go over ALL tests, categorize all errors"
- "Find the Jenkins job for PR #21634"
- "Find the build for commit cf17a9e96f"

## Troubleshooting

### Connection Errors
Ask user: "Please check if the SOCKS5 proxy is running on your laptop at localhost:8080"

### Authentication Errors (401/403)
Verify the Jenkins token in credentials.json is correct and has the structure: `{"jenkins": {"key": "JENKINS=TOKEN"}}`

### Credentials Not Found
Ask user to provide the Jenkins API token or confirm the credentials file location.

### Token Extraction Issues
ALWAYS use the Read tool to get credentials first. Use the extracted token value directly in curl commands (no command substitution).
