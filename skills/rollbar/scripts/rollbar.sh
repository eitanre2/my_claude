#!/usr/bin/env bash
# Rollbar API CLI — thin wrapper around the Rollbar REST API.
# Usage: rollbar.sh <command> [options]
#
# Token resolution order:
#   1. ROLLBAR_ACCESS_TOKEN env var
#   2. ~/.cursor/mcp.json  (mcpServers.rollbar.env.ROLLBAR_ACCESS_TOKEN)

set -euo pipefail

BASE_URL="https://api.rollbar.com/api/1"

resolve_token() {
  if [[ -n "${ROLLBAR_ACCESS_TOKEN:-}" ]]; then
    echo "$ROLLBAR_ACCESS_TOKEN"
    return
  fi
  local creds_file="$HOME/.claude/credentials.json"
  if [[ -f "$creds_file" ]]; then
    local token
    token=$(python3 -c "
import json
with open('$creds_file') as f:
    print(json.load(f).get('rollbar',{}).get('access_token',''))
" 2>/dev/null)
    if [[ -n "$token" ]]; then
      echo "$token"
      return
    fi
  fi
  echo "ERROR: No Rollbar token found. Set ROLLBAR_ACCESS_TOKEN or add rollbar.access_token to ~/.claude/credentials.json" >&2
  exit 1
}

TOKEN=$(resolve_token)

api_get() {
  local path="$1"
  curl -s -L -H "X-Rollbar-Access-Token: $TOKEN" "${BASE_URL}${path}"
}

cmd_list_items() {
  local status="active" env="production" level="" limit="20" page="1" query=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --status)  status="$2"; shift 2;;
      --env)     env="$2"; shift 2;;
      --level)   level="$2"; shift 2;;
      --limit)   limit="$2"; shift 2;;
      --page)    page="$2"; shift 2;;
      --query)   query="$2"; shift 2;;
      *) echo "Unknown option: $1" >&2; exit 1;;
    esac
  done
  local url="/items/?status=${status}&environment=${env}&page=${page}"
  [[ -n "$limit" ]] && url="${url}&limit=${limit}"
  [[ -n "$level" ]] && for l in $(echo "$level" | tr ',' ' '); do url="${url}&level=${l}"; done
  [[ -n "$query" ]] && url="${url}&query=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$query'))")"
  api_get "$url" | python3 -c "
import sys, json, datetime
d = json.load(sys.stdin)
if d.get('err', 1) != 0:
    print(f'Error: {json.dumps(d)}', file=sys.stderr); sys.exit(1)
items = d['result']['items']
total = d['result'].get('total_count', '?')
print(f'Total: {total} items (showing {len(items)}, page ${page})')
print()
print(f'{\"#\":<8} {\"Level\":<9} {\"Occurrences\":>12} {\"Last Seen\":<20} {\"First Seen\":<20} Title')
print('-' * 120)
for i in items:
    last = datetime.datetime.utcfromtimestamp(i['last_occurrence_timestamp']).strftime('%Y-%m-%d %H:%M') if i.get('last_occurrence_timestamp') else '?'
    first = datetime.datetime.utcfromtimestamp(i['first_occurrence_timestamp']).strftime('%Y-%m-%d %H:%M') if i.get('first_occurrence_timestamp') else '?'
    print(f'{i[\"counter\"]:<8} {i[\"level\"]:<9} {i[\"total_occurrences\"]:>12} {last:<20} {first:<20} {i[\"title\"][:80]}')
"
}

cmd_item_details() {
  local counter="" show_trace=1
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --counter) counter="$2"; shift 2;;
      --no-trace) show_trace=0; shift;;
      *) counter="$1"; shift;;
    esac
  done
  [[ -z "$counter" ]] && { echo "Usage: rollbar.sh item <counter>" >&2; exit 1; }

  # Step 1: counter -> item id
  local item_json
  item_json=$(api_get "/item_by_counter/${counter}")
  local item_id
  item_id=$(echo "$item_json" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['result']['id'])")

  # Step 2: get item details
  local details
  details=$(api_get "/item/${item_id}")

  # Step 3: get latest occurrence
  local occurrence
  occurrence=$(api_get "/item/${item_id}/instances?page=1")

  python3 -c "
import sys, json, datetime

item = json.loads('''${details}''')['result']
occ_data = json.loads(sys.stdin.read())
instances = occ_data.get('result', {}).get('instances', [])
occ = instances[0] if instances else None

def ts(t):
    return datetime.datetime.utcfromtimestamp(t).strftime('%Y-%m-%d %H:%M:%S UTC') if t else '?'

print('=' * 100)
print(f'Item #{item[\"counter\"]}: {item[\"title\"]}')
print(f'URL: https://app.rollbar.com/a/cloudinaryltd/fix/item/Backend-Prod/{item[\"counter\"]}')
print(f'Status: {item[\"status\"]}  Level: {item[\"level\"]}  Environment: {item.get(\"environment\",\"?\")}')
print(f'Total occurrences: {item[\"total_occurrences\"]}')
print(f'First seen: {ts(item.get(\"first_occurrence_timestamp\"))}')
print(f'Last seen:  {ts(item.get(\"last_occurrence_timestamp\"))}')
print('=' * 100)

if not occ:
    print('No occurrence data available.')
    sys.exit(0)

data = occ.get('data', {})
server = data.get('server', {})
extra = data.get('extra', data.get('body', {}).get('trace', {}).get('extra', {}))
context = data.get('context', '?')

print()
print('--- Latest Occurrence ---')
print(f'Timestamp:  {ts(occ.get(\"timestamp\"))}')
print(f'Context:    {context}')
print(f'Host:       {server.get(\"host\", \"?\")}')
print(f'Instance:   {server.get(\"instance_id\", \"?\")}')
print(f'PID:        {server.get(\"pid\", \"?\")}')
print(f'Code ver:   {data.get(\"code_version\", \"?\")}')
print(f'Geo:        {data.get(\"geo\", \"?\")}')
print(f'Role:       {data.get(\"role\", \"?\")}')

req = data.get('request', extra)
if isinstance(req, dict) and req.get('url'):
    print(f'Request:    {req.get(\"method\",\"?\")} {req[\"url\"]}')
    params = req.get('params', {})
    if params:
        print(f'Params:     {json.dumps(params)}')
    team = extra.get('team', '?') if isinstance(extra, dict) else '?'
    req_id = extra.get('request_id', req.get('request_id', '?')) if isinstance(extra, dict) else '?'
    print(f'Team:       {team}')
    print(f'Request ID: {req_id}')

trace = data.get('body', {}).get('trace', {})
if trace and ${show_trace}:
    exc = trace.get('exception', {})
    print()
    print(f'--- Exception ---')
    print(f'{exc.get(\"class\", \"?\")}: {exc.get(\"message\", \"?\")}')
    print()
    print('--- Stack Trace (application frames only) ---')
    frames = trace.get('frames', [])
    app_frames = [f for f in frames if '/vendor/' not in f.get('filename','') and f.get('filename','').startswith('/opt/cloudinary')]
    for f in reversed(app_frames):
        fn = f['filename'].replace('/opt/cloudinary/current/', '')
        print(f'  {fn}:{f.get(\"lineno\",\"?\")} in {f.get(\"method\",\"?\")}')
" <<< "$occurrence"
}

cmd_top_items() {
  local env="production"
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --env) env="$2"; shift 2;;
      *) echo "Unknown option: $1" >&2; exit 1;;
    esac
  done
  api_get "/reports/top_active_items?environment=${env}&hours=24" | python3 -c "
import sys, json
d = json.load(sys.stdin)
if d.get('err', 1) != 0:
    print(f'Error: {json.dumps(d)}', file=sys.stderr); sys.exit(1)
items = d['result']
print(f'{\"#\":<8} {\"Occurrences\":>12} Title')
print('-' * 90)
for i in items:
    item = i.get('item', {})
    print(f'{item.get(\"counter\",\"?\"):<8} {i.get(\"item_count\",\"?\"):>12} {item.get(\"title\",\"?\")[:70]}')
"
}

cmd_deploys() {
  local limit="10" page="1"
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --limit) limit="$2"; shift 2;;
      --page)  page="$2"; shift 2;;
      *) echo "Unknown option: $1" >&2; exit 1;;
    esac
  done
  api_get "/deploys?page=${page}" | python3 -c "
import sys, json, datetime
d = json.load(sys.stdin)
if d.get('err', 1) != 0:
    print(f'Error: {json.dumps(d)}', file=sys.stderr); sys.exit(1)
deploys = d['result']['deploys'][:${limit}]
print(f'{\"Revision\":<15} {\"Environment\":<15} {\"Status\":<10} {\"Started\":<22} {\"Finished\":<22} User')
print('-' * 100)
for dep in deploys:
    started = datetime.datetime.utcfromtimestamp(dep['start_time']).strftime('%Y-%m-%d %H:%M:%S') if dep.get('start_time') else '?'
    finished = datetime.datetime.utcfromtimestamp(dep['finish_time']).strftime('%Y-%m-%d %H:%M:%S') if dep.get('finish_time') else '?'
    print(f'{str(dep.get(\"revision\",\"?\"))[:14]:<15} {dep.get(\"environment\",\"?\"):<15} {dep.get(\"status\",\"?\"):<10} {started:<22} {finished:<22} {dep.get(\"local_username\",\"?\")}')
"
}

cmd_occurrence() {
  local occ_id=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --id) occ_id="$2"; shift 2;;
      *) occ_id="$1"; shift;;
    esac
  done
  [[ -z "$occ_id" ]] && { echo "Usage: rollbar.sh occurrence <occurrence_id>" >&2; exit 1; }
  api_get "/instance/${occ_id}" | python3 -m json.tool
}

cmd_help() {
  cat <<'HELP'
Rollbar CLI — Query the Rollbar API

Commands:
  list    [options]        List items (errors)
    --status STATUS          active|resolved|muted (default: active)
    --env ENV                Environment (default: production)
    --level LEVELS           Comma-separated: error,critical,warning
    --limit N                Items per page (default: 20)
    --page N                 Page number (default: 1)
    --query TEXT             Search by title/content

  item    <counter>        Get item details + stack trace
    --no-trace               Skip stack trace output

  top     [options]        Top active items (last 24h)
    --env ENV                Environment (default: production)

  deploys [options]        Recent deployments
    --limit N                Number of deploys (default: 10)

  occurrence <id>          Get raw occurrence JSON

  help                     Show this help
HELP
}

case "${1:-help}" in
  list)       shift; cmd_list_items "$@";;
  item)       shift; cmd_item_details "$@";;
  top)        shift; cmd_top_items "$@";;
  deploys)    shift; cmd_deploys "$@";;
  occurrence) shift; cmd_occurrence "$@";;
  help|--help|-h) cmd_help;;
  *) echo "Unknown command: $1. Run 'rollbar.sh help' for usage." >&2; exit 1;;
esac
