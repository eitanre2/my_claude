---
name: rollbar
description: Query and investigate Rollbar error items, view stack traces, check deployments, and find top errors. Use when the user asks to "check Rollbar", "find errors", "investigate Rollbar items", "show recent errors", "list Rollbar items", "get error details", "check deployments", or mentions Rollbar, error tracking, or production errors.
---

# Rollbar Error Investigation

Query Rollbar via the REST API using `scripts/rollbar.sh` (relative to this skill's directory).

Token is auto-resolved from `ROLLBAR_ACCESS_TOKEN` env var or `~/.claude/credentials.json` (`rollbar.access_token`).

## Commands

### List items

```bash
bash scripts/rollbar.sh list [options]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--status` | `active` | `active`, `resolved`, `muted` |
| `--env` | `production` | Environment filter |
| `--level` | all | Comma-separated: `error,critical,warning` |
| `--limit` | `20` | Items per page |
| `--page` | `1` | Page number |
| `--query` | | Search title/content |

### Get item details + stack trace

```bash
bash scripts/rollbar.sh item <counter>
bash scripts/rollbar.sh item <counter> --no-trace
```

Returns: item metadata, latest occurrence context (host, instance, PID, request URL, params, request_id, team), exception details, and application-only stack trace (vendor frames filtered out).

The `counter` is the item number shown in Rollbar URLs and list output (NOT the internal item ID).

### Top active items (last 24h)

```bash
bash scripts/rollbar.sh top [--env production]
```

### Recent deployments

```bash
bash scripts/rollbar.sh deploys [--limit 10]
```

### Raw occurrence JSON

```bash
bash scripts/rollbar.sh occurrence <occurrence_id>
```

## Common Workflows

### Triage recent errors

```bash
bash scripts/rollbar.sh list --limit 10
bash scripts/rollbar.sh item 86392
```

### Correlate related errors

1. List items with `--query "NoMethodError"` to find related items
2. Run `item <counter>` for each, compare:
   - **Same host/instance/PID?** — bad worker
   - **Same code path in trace?** — code bug
   - **Same code_version?** — deployment regression
   - **Same time window?** — check `deploys` for correlation

### Deployment impact

```bash
bash scripts/rollbar.sh deploys --limit 5
bash scripts/rollbar.sh list --limit 20
```

Compare `first_occurrence_timestamp` of new items against deployment times.

## Presentation

- Use tables for item lists
- Convert unix timestamps to human-readable (the script does this automatically)
- When comparing multiple items, highlight shared host/instance/PID/code paths
- Include Rollbar URLs from item detail output
