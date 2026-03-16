---
name: merge-worktree
description: Squash-merge all changes from the current worktree back into master and remove the worktree. Use when the user asks to "merge worktree", "merge back to master", "finish worktree", "merge changes back", or mentions merging worktree work into the main branch.
---

# Merge Worktree to Master

Squash-merge all worktree commits into master with a descriptive commit message, then remove the worktree.

## Steps

1. Confirm you are in a worktree (not the root):

```bash
ROOT="$(git worktree list --porcelain | head -1 | sed 's/^worktree //')"
WORKTREE="$(git rev-parse --show-toplevel)"
```

If `$ROOT` equals `$WORKTREE`, stop — you are already on master. Tell the user.

2. Capture the worktree HEAD and the commit log that diverges from master:

```bash
WORKTREE_HEAD="$(git rev-parse HEAD)"
git log master..HEAD --oneline
```

If there are no commits ahead of master, ask for adding them.

3. Summarize the commit messages into a single merge-commit title. Use the commit subjects from step 2 to write a concise, imperative summary (e.g. "add confluence integration and fix comment rendering"). Keep it under ~72 characters. If there's only one commit, use its message directly.

4. Check for uncommitted changes in the worktree. If any exist, ask the user whether to commit them first or discard them before proceeding.

5. Switch to the root worktree and perform the squash merge:

```bash
git -C "$ROOT" merge --squash "$WORKTREE_HEAD"
git -C "$ROOT" commit -m "<your summarized title>"
```

If the merge has conflicts, stop and inform the user. Do **not** force-resolve conflicts automatically.

6. Verify the merge succeeded:

```bash
git -C "$ROOT" log -1 --oneline
```

7. Remove the worktree:

```bash
git worktree remove "$WORKTREE"
```

If removal fails (e.g. untracked files), try with `--force` after confirming with the user.

## Notes

- Always use `git -C "$ROOT"` to run commands against master from inside the worktree, so you don't need to `cd` out of the worktree before removing it.
- The squash merge collapses all worktree commits into a single commit on master.
- The worktree path is removed from disk after a successful merge.
- If the user has multiple worktrees open, confirm which one to merge.
