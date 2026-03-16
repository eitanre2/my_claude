---
name: cloudinary-logs
description: Download and analyze worker logs from the cloudinary-logs S3 bucket. Use when user asks to "analyze logs", "check production logs", "list instances", "find errors in logs", or mentions S3 log analysis, rails worker logs, or cloudinary-logs bucket.
metadata:
  version: 1.2.0
  author: Eitan Revach
---

# Cloudinary Logs Analyzer

## Requirements

- AWS CLI configured with production profile
- Access to cloudinary-logs S3 bucket (s3://cloudinary-logs)
- Python 3

## Bucket Structure

```
s3://cloudinary-logs/{service}/{date}/{instance-id}/
```

Example: `s3://cloudinary-logs/rails/20260223/i-0b6bc08c6df232bf4/`

Common log files per instance:
- `production.YYYYMMDD-HH.log.gz` - Main Rails production logs
- `error-log-*.log.gz` - Error logs
- `syslog.gz` - System logs

For a full list of log types, see `references/log-types.md` (relative to this skill's directory).

## Instructions

All scripts below use paths relative to this skill's directory (`skills/cloudinary-logs/`).

### Step 1: List available services
```bash
python3 scripts/analyze.py --list-services
```

### Step 2: List instances for a service on a date
```bash
python3 scripts/analyze.py --service rails --date 20260223 --list-instances
```

### Step 3: List log files for an instance
```bash
python3 scripts/analyze.py --service rails --date 20260223 --instance i-0b6bc08c6df232bf4 --list-files
```

### Step 4: Download and analyze production logs
```bash
python3 scripts/analyze.py --service rails --date 20260223 --instance i-0b6bc08c6df232bf4 --analyze-production
```

To analyze specific hours:
```bash
python3 scripts/analyze.py --service rails --date 20260223 --instance i-0b6bc08c6df232bf4 --analyze-production --hours 14 15 16
```

## Output

Analysis includes:
- Total line counts
- Error/Warning/Info distribution and percentages
- Top error messages and warning patterns
- Hourly breakdown of log activity

## Examples

- "List all instances in rails service for today"
- "Analyze rails logs for instance i-0b6bc08c6df232bf4 from today"
- "Download production logs for instance X from date Y"
- "What errors are in the production logs for instance Z?"

## Troubleshooting

### AWS Access Denied
Verify your AWS production profile has access to the cloudinary-logs bucket. Re-authenticate using the Okta CLI:
```bash
okta-awscli --profile "production-readonly" --okta-profile production
```

### Large Log Files
Production logs can be 400-500MB compressed per hour. Use `--hours` to limit the scope.
