---
name: create-worktree
description: Create a new worktree from the current branch with optional project-specific setup. Optionally creates a new branch if details are provided. Use when the user asks to "create worktree", "make a worktree", "new worktree", or mentions creating a worktree from the current branch.
---

# Create Worktree

Create a new git worktree from the current branch. If the project has a `.worktree.json` config file, the script will create symbolic links and run setup commands defined there.

## Pre-flight: Ensure `.worktree.json` exists

Before running the script, check if `.worktree.json` exists in the project root.

**If it does NOT exist**, ask the user the following questions to create it:

1. **Default branch** — Which branch do you merge into? (e.g., `master`, `main`)
2. **Symlinks** — Are there files or directories that should be shared (symlinked) from the root into each worktree? Common examples: `.env`, config files. For each one, ask whether the path is the same in the worktree or different (e.g., root's `.env` linked as `backend/.env`).
3. **Post-create commands** — Any setup commands to run after the worktree is created? (e.g., `npm install`, `bundle install`, `pip install -r requirements.txt`). If none are specified, the script will auto-detect common package managers.

Once you have the answers, write the `.worktree.json` file to the project root. Then proceed with creating the worktree — the script will add `.worktree.json` to `.git/info/exclude` (per-repo, local-only — the file contains each developer's setup preferences and shouldn't be shared via the committed `.gitignore`).

**If it already exists**, skip straight to running the script.

## Usage

Run the create-worktree script with an optional branch name:

```bash
# Without branch (stays in detached HEAD)
~/.claude/skills/create-worktree/scripts/create-worktree.sh

# With branch for feature development
~/.claude/skills/create-worktree/scripts/create-worktree.sh feature/my-feature
```

**Important:** When the user provides details about the feature or worktree purpose, create a descriptive branch name and pass it to the script. If no details are provided, ask the user for a branch name before running the script.

The script will:
1. Check if you're in the root worktree (warns if not)
2. Get the current branch or commit
3. Generate a random 3-character worktree ID
4. Ensure `.claude/worktrees` is in .gitignore (shared) and `.worktree.json` is in `.git/info/exclude` (local-only)
5. Create the worktree under `.claude/worktrees/<id>`
6. Create a new branch (if branch name provided)
7. Create symbolic links defined in `.worktree.json` (if config exists)
8. Run post-create commands from `.worktree.json`, or auto-detect package managers (npm, bundle, pip) if no config
9. Display summary with worktree path, ID, and branch name

## Project Configuration (`.worktree.json`)

Projects can place a `.worktree.json` file in their root to customize worktree setup. All fields are optional:

```json
{
  "default_branch": "master",
  "symlinks": [
    ".env",
    { "source": ".env", "target": "backend/.env" }
  ],
  "post_create": [
    "cd backend && npm install --silent"
  ]
}
```

| Field | Description |
|-------|-------------|
| `default_branch` | Branch to merge into / rebase from. Auto-detected (`main` or `master`) if omitted. |
| `symlinks` | Files/directories to symlink from root into the worktree. A string means same path; an object `{"source": "X", "target": "Y"}` links root's X to worktree's Y. |
| `post_create` | Shell commands to run after worktree creation (e.g., install dependencies). If omitted, the script auto-detects package managers. |

## Output

The script outputs:
- `WORKTREE_PATH=/path/to/worktree` - full path to the new worktree
- `WORKTREE_ID=abc` - the 3-character identifier
- `WORKTREE_BRANCH=branch-name` - the branch name (only if branch was created)

Parse these to get the worktree location and branch information.

**IMPORTANT:** After running the script, you MUST change to the worktree directory using `cd $WORKTREE_PATH`. Stay in the worktree directory for all subsequent work until the user asks to merge or exit the worktree.

## Notes

- Worktrees are created in `<project-root>/.claude/worktrees/<id>`
- The worktree ID is a 3-character random string (e.g., "cke", "uzs")
- The `.claude/worktrees` directory is automatically added to .gitignore
- Worktrees are created in detached HEAD state, then a new branch is created if a branch name is provided
- **Best practice:** Always provide a branch name when doing feature work to make commits trackable
- Packages are automatically installed (npm, bundle, pip) when no `post_create` config is present
- The root worktree remains unchanged and can continue to be used
- Each worktree has its own working directory but shares the same .git database
- **After creation:** Always `cd` to the worktree directory and stay there until merging/exiting

## Troubleshooting

- If the worktree path already exists, the script will fail - remove the old worktree first
- If symbolic link creation fails, check that the source files exist in the root
- Use `git worktree list` to view all worktrees
- Use `git worktree remove <path>` to remove a worktree when done
