---
name: merge-worktree
description: Squash-merge all changes from the current worktree back into the default branch and remove the worktree. Use when the user asks to "merge worktree", "merge back to master", "finish worktree", "merge changes back", or mentions merging worktree work into the main branch.
---

# Merge Worktree

Squash-merge all worktree commits into the default branch with a descriptive commit message, then remove the worktree.

## Usage

Simply run the merge script:

```bash
~/.claude/skills/merge-worktree/scripts/merge-worktree.sh
```

The script will:
1. Verify you're in a worktree (not the root)
2. Detect the default branch (from `.worktree.json` config, or auto-detect `main`/`master`)
3. Show commits that will be merged
4. Check for uncommitted changes (warns but continues)
5. Generate a commit message automatically
6. Squash merge to the default branch
7. Remove the worktree (with --force if needed)

## What it does

- **Default branch detection**: Reads `default_branch` from `.worktree.json` in the project root. If not configured, checks if `main` exists, otherwise falls back to `master`.
- **Single commit**: Uses that commit's message directly
- **Multiple commits**: Uses the first commit's message as title, lists all commits in body
- **Uncommitted changes**: Warns but continues (they won't be included in merge)
- **Untracked files**: Forces worktree removal if needed
- **Adds co-author**: Automatically adds Claude as co-author

## Notes

- Always use `git -C "$ROOT"` to run commands against the default branch from inside the worktree, so you don't need to `cd` out of the worktree before removing it.
- The squash merge collapses all worktree commits into a single commit on the default branch.
- The worktree path is removed from disk after a successful merge.
- If the user has multiple worktrees open, confirm which one to merge.
