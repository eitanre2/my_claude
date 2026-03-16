# Jenkins API Reference

Official docs: https://www.jenkins.io/doc/book/using/remote-access-api/

## Endpoints

- Job info: `/job/{JOB_NAME}/api/json`
- Build info: `/job/{JOB_NAME}/{BUILD_NUMBER}/api/json`
- Console output: `/job/{JOB_NAME}/{BUILD_NUMBER}/consoleText`
- Latest build: Use `lastBuild`, `lastSuccessfulBuild`, or `lastFailedBuild` as build number

## Build Number Shortcuts

- `lastBuild` - Most recent build
- `lastSuccessfulBuild` - Most recent successful build
- `lastFailedBuild` - Most recent failed build
- Or specific build number (e.g., 123)

## Finding Builds by PR or Commit

1. Get latest build number:
   ```bash
   curl -x socks5h://localhost:8080 -s -u "eitan.revach@cloudinary.com:$TOKEN" \
     "https://jenkins.cloudinary.com/job/Staging2-CI-PR/lastBuild/api/json?tree=number"
   ```

2. Search recent builds using Python:
   ```python
   import requests, json

   with open('/home/ubuntu/.claude/credentials.json') as f:
       creds = json.load(f)
   token = creds['jenkins']['key'].split('=')[1]

   auth = ("eitan.revach@cloudinary.com", token)
   proxies = {"http": "socks5h://localhost:8080", "https": "socks5h://localhost:8080"}

   for build_num in range(latest_build, latest_build - 30, -1):
       url = f"https://jenkins.cloudinary.com/job/Staging2-CI-PR/{build_num}/api/json"
       r = requests.get(url, auth=auth, proxies=proxies, timeout=5)
       data = r.json()
       params = [p for a in data.get('actions', []) if 'parameters' in a for p in a['parameters']]
       pr = next((p['value'] for p in params if p['name'] == 'ghprbPullId'), None)
       commit = next((p['value'] for p in params if p['name'] == 'ghprbActualCommit'), None)

       if pr == 'TARGET_PR' or (commit and commit.startswith('TARGET_COMMIT')):
           print(f"Found: Build #{build_num}")
           break
   ```

3. Key fields: `ghprbPullId` (PR number), `ghprbActualCommit` (commit hash), `ghprbTriggerAuthorLogin` (trigger author), `result` (build status, null = still running).
