# Coralogix Skill - Usage Examples

This skill uses the Coralogix Direct Archive Query (DataPrime) API to retrieve logs.

## With Claude Code (Natural Language)

Simply ask Claude to query Coralogix:

```
show me the last 10 logs from coralogix
```

```
find ERROR logs from the last 2 hours in coralogix
```

```
get logs from the rails application in coralogix
```

```
query coralogix and save as JSON
```

```
show me WARNING logs from nginx application
```

## Command Line Examples

### 1. Basic Queries

Get all recent logs:
```bash
python3 ~/.claude/skills/coralogix/coralogix_client.py
```

Get logs from last 24 hours:
```bash
python3 ~/.claude/skills/coralogix/coralogix_client.py --hours 24
```

Limit results:
```bash
python3 ~/.claude/skills/coralogix/coralogix_client.py --limit 50
```

### 2. Text Search

Search for specific text in log content:
```bash
python3 ~/.claude/skills/coralogix/coralogix_client.py --query "database"
```

Search for errors:
```bash
python3 ~/.claude/skills/coralogix/coralogix_client.py --query "error"
```

**Note**: Text search looks within the log userData field. For complex queries, use raw DataPrime syntax (see section 11 below).

### 3. Filter by Severity

Only errors:
```bash
python3 ~/.claude/skills/coralogix/coralogix_client.py --severity ERROR
```

Errors and warnings:
```bash
python3 ~/.claude/skills/coralogix/coralogix_client.py --severity ERROR WARNING
```

All severity levels:
```bash
python3 ~/.claude/skills/coralogix/coralogix_client.py --severity ERROR WARNING INFO DEBUG
```

Critical only:
```bash
python3 ~/.claude/skills/coralogix/coralogix_client.py --severity CRITICAL --hours 24
```

### 4. Filter by Application/Subsystem

Specific application:
```bash
python3 ~/.claude/skills/coralogix/coralogix_client.py --application rails
```

Specific subsystem:
```bash
python3 ~/.claude/skills/coralogix/coralogix_client.py --subsystem nginx-rails
```

Combined filters:
```bash
python3 ~/.claude/skills/coralogix/coralogix_client.py --application rails --severity ERROR --hours 2
```

### 5. Output Formats

Plain text (default):
```bash
python3 ~/.claude/skills/coralogix/coralogix_client.py --format text
```

JSON format:
```bash
python3 ~/.claude/skills/coralogix/coralogix_client.py --format json
```

CSV format:
```bash
python3 ~/.claude/skills/coralogix/coralogix_client.py --format csv
```

### 6. Save to File

Save as JSON:
```bash
python3 ~/.claude/skills/coralogix/coralogix_client.py --query "error" --format json --output errors.json
```

Save as CSV:
```bash
python3 ~/.claude/skills/coralogix/coralogix_client.py --severity ERROR --format csv --output errors.csv
```

Save text output:
```bash
python3 ~/.claude/skills/coralogix/coralogix_client.py --hours 24 --output daily-logs.txt
```

### 7. Raw DataPrime Queries

For advanced filtering, use raw DataPrime query syntax:

Filter by severity:
```bash
python3 ~/.claude/skills/coralogix/coralogix_client.py \
  --dataprime "source logs | filter \$m.severity == Severity.ERROR | limit 50"
```

Multiple conditions:
```bash
python3 ~/.claude/skills/coralogix/coralogix_client.py \
  --dataprime "source logs | filter \$m.severity == Severity.ERROR && \$l.applicationname == 'rails' | limit 100"
```

OR conditions:
```bash
python3 ~/.claude/skills/coralogix/coralogix_client.py \
  --dataprime "source logs | filter \$m.severity == Severity.ERROR || \$m.severity == Severity.WARNING | limit 200"
```

Filter by subsystem:
```bash
python3 ~/.claude/skills/coralogix/coralogix_client.py \
  --dataprime "source logs | filter \$l.subsystemname == 'nginx-rails' | limit 50"
```

**DataPrime Syntax Reference:**
- `$m.severity` - Metadata severity field (use `Severity.ERROR`, `Severity.WARNING`, etc.)
- `$l.applicationname` - Label application name
- `$l.subsystemname` - Label subsystem name
- `$d.userData` - Log data content
- `&&` - AND operator
- `||` - OR operator

### 8. Monitoring Use Cases

Recent critical errors:
```bash
python3 ~/.claude/skills/coralogix/coralogix_client.py --severity ERROR --hours 1 --limit 20
```

Application health check:
```bash
python3 ~/.claude/skills/coralogix/coralogix_client.py --application rails --severity ERROR WARNING --hours 1
```

Real-time monitoring (run periodically):
```bash
watch -n 30 'python3 ~/.claude/skills/coralogix/coralogix_client.py --hours 0.5 --severity ERROR'
```

Check specific application errors:
```bash
python3 ~/.claude/skills/coralogix/coralogix_client.py \
  --dataprime "source logs | filter \$l.applicationname == 'nginx' && \$m.severity == Severity.ERROR | limit 100"
```

### 9. Export for Analysis

Export all errors from today:
```bash
python3 ~/.claude/skills/coralogix/coralogix_client.py --severity ERROR --hours 24 --format json --output today-errors.json
```

Export specific app logs:
```bash
python3 ~/.claude/skills/coralogix/coralogix_client.py --application rails --hours 168 --format csv --output week-logs.csv
```

Export with DataPrime query:
```bash
python3 ~/.claude/skills/coralogix/coralogix_client.py \
  --dataprime "source logs | filter \$m.severity == Severity.CRITICAL | limit 500" \
  --format json --output critical.json
```

### 10. Integration Examples

Pipe to grep for further filtering:
```bash
python3 ~/.claude/skills/coralogix/coralogix_client.py --hours 24 | grep -i "database"
```

Count log entries:
```bash
python3 ~/.claude/skills/coralogix/coralogix_client.py --severity ERROR --hours 24 | grep -c "^\["
```

Extract specific fields with jq:
```bash
python3 ~/.claude/skills/coralogix/coralogix_client.py --format json --limit 10 | \
  jq '.[] | {time: .timestamp, app: .applicationName, severity: .severity}'
```

Send to email (with mail command):
```bash
python3 ~/.claude/skills/coralogix/coralogix_client.py --severity ERROR --hours 24 | \
  mail -s "Daily Error Report" admin@example.com
```

## Automation Examples

### Daily Error Report Script

```bash
#!/bin/bash
# daily_report.sh
DATE=$(date +%Y-%m-%d)
python3 ~/.claude/skills/coralogix/coralogix_client.py \
  --severity ERROR \
  --hours 24 \
  --format csv \
  --output "error-report-$DATE.csv"
echo "Report saved to error-report-$DATE.csv"
```

### Alert on Critical Errors

```bash
#!/bin/bash
# check_critical.sh
ERRORS=$(python3 ~/.claude/skills/coralogix/coralogix_client.py --query "critical OR fatal" --hours 1 --limit 1000)
COUNT=$(echo "$ERRORS" | wc -l)

if [ $COUNT -gt 10 ]; then
  echo "ALERT: $COUNT critical errors in the last hour!"
  echo "$ERRORS"
fi
```

### Cron Job Setup

Add to crontab (`crontab -e`):

```cron
# Daily error report at 9 AM
0 9 * * * cd /home/ubuntu/a && ./daily_report.sh

# Check for critical errors every 15 minutes
*/15 * * * * cd /home/ubuntu/a && ./check_critical.sh
```

## Tips

1. **Start broad, then narrow**: Begin with `--query "*"` to see what data is available, then refine your query
2. **Use time ranges wisely**: Large time ranges with many logs may be slow
3. **Combine filters**: Use severity, application, and query together for precise results
4. **Export for analysis**: Use JSON/CSV format to analyze logs with other tools
5. **Test queries**: Always test with `--limit 10` first to verify your query works

## Need Help?

- See README.md for setup instructions
- Run `python3 ~/.claude/skills/coralogix/coralogix_client.py --help` for all options
- Ask Claude: "help me query coralogix for X"
