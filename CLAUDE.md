# CLAUDE.md

This file provides guidance to AI assistants (Claude Code, Cursor, etc.) when working in this repository.

**Author:** Eitan Revach, Architect at Cloudinary.

## Structure

- `skills/` — Agent skills (self-contained modules with SKILL.md, scripts, and references)
- `credentials.json` — API keys and secrets (never commit or display contents)

## Main Skills

| Skill | Purpose |
|-------|---------|
| cloudinary-logs | Download and analyze workter logs from the cloudinary-logs S3 bucket |
| coralogix | Query production logs via the DataPrime API |
| jenkins-reader | Read and analyze Jenkins build outputs and test failures |
| redash | Execute SQL queries against Redash data sources |
| telegram | Send/receive messages via Telegram Bot API |
| twilio | Send SMS and WhatsApp messages via Twilio API |

## Rules
Additional rules are stored in the `rules` folder. Read only the description of each rule; load the full content only when relevant to the current task.

- **Credentials are sensitive.** Never print, log, or expose contents of `credentials.json`.
- When adding a new skill, follow the existing pattern: `skills/<name>/SKILL.md` with optional `scripts/` and `references/` subdirectories.
- After modifying skills or credentials, run `make sync` to propagate changes to devenv2 and Google Drive.
