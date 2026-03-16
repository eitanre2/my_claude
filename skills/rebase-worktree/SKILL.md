---
name: rebase-worktree
description: Rebase the current worktree's commits on top of its base branch to incorporate upstream changes. Use when the user asks to "rebase worktree", "update worktree", "sync worktree", "rebase on master", or mentions rebasing, syncing, or updating the worktree with latest changes from the base branch.
---

# Rebase Worktree

Rebase the worktree's commits on top of the latest base branch so the worktree stays up to date.

## Steps

1. Confirm you are in a worktree (not the root):

```bash
ROOT="$(git worktree list --porcelain | head -1 | sed 's/^worktree //')"
WORKTREE="$(git rev-parse --show-toplevel)"
```

If `$ROOT` equals `$WORKTREE`, stop — you are already in the root worktree. Tell the user.

2. Detect the base branch. Find which local branch has the most recent common ancestor with HEAD:

```bash
for branch in $(git for-each-ref --format='%(refname:short)' refs/heads/); do
  mb=$(git merge-base "$branch" HEAD 2>/dev/null) || continue
  echo "$(git log -1 --format='%ct' "$mb") $branch"
done | sort -rn | head -1 | awk '{print $2}'
```

If no branch is found, fall back to `master`. Show the detected base branch to the user and confirm before proceeding.

3. Show what will be rebased:

```bash
BASE_BRANCH="<detected branch>"
git log "$BASE_BRANCH..HEAD" --oneline
```

If there are no commits ahead of the base branch, stop — nothing to rebase.

4. Check for uncommitted changes. If any exist, stash them automatically before rebasing:

```bash
git stash push -m "rebase-worktree: auto-stash before rebase"
```

5. Perform the rebase:

```bash
git rebase "$BASE_BRANCH"
```

If conflicts occur, stop and inform the user. Let them resolve conflicts manually, then continue with `git rebase --continue`. Do **not** force-resolve conflicts.

6. If changes were stashed in step 4, restore them:

```bash
git stash pop
```

7. Verify the result:

```bash
git log --oneline -5
```

Confirm to the user that the rebase succeeded and show the updated commit history.

## Notes

- Worktrees in this project typically use detached HEADs. `git rebase` works on detached HEAD — it replays commits and leaves you at a new detached HEAD.
- The base-branch detection picks the branch sharing the most recent common ancestor with HEAD. This works well when worktrees are forked from a known branch like `master`.
- If the detection picks the wrong branch, the user confirmation in step 2 gives them a chance to correct it.
- Auto-stashing ensures uncommitted work is not lost during the rebase.
