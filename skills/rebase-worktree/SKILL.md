---
name: rebase-worktree
description: Rebase the current worktree's commits on top of its base branch to incorporate upstream changes. Use when the user asks to "rebase worktree", "update worktree", "sync worktree", "rebase on master", or mentions rebasing, syncing, or updating the worktree with latest changes from the base branch.
---

# Rebase Worktree

Rebase the worktree's commits on top of the latest base branch so the worktree stays up to date.

## Usage

Run the rebase-worktree script:

```bash
~/.claude/skills/rebase-worktree/scripts/rebase-worktree.sh
```

The script will:
1. Confirm you're in a worktree (not root)
2. Fetch latest changes from origin
3. Detect the base branch automatically (most recent common ancestor, or falls back to configured/auto-detected default branch)
4. Show commits that will be rebased
5. Auto-stash any uncommitted changes
6. Perform the rebase
7. Restore stashed changes (if any)
8. Display the result

**If already up to date:** The script exits with a success message.

**If conflicts occur:** The script stops and instructs you to resolve conflicts manually with `git rebase --continue`, then restore stashed changes with `git stash pop` if needed.

## Branch Detection

The script detects the base branch in this order:
1. Finds the branch with the most recent common ancestor with HEAD
2. Falls back to `default_branch` from `.worktree.json` config (if present)
3. Auto-detects: uses `main` if it exists, otherwise `master`

## Notes

- Worktrees typically use detached HEADs. `git rebase` works on detached HEAD — it replays commits and leaves you at a new detached HEAD.
- Auto-stashing ensures uncommitted work is not lost during the rebase.
- The base-branch detection picks the branch sharing the most recent common ancestor with HEAD.
