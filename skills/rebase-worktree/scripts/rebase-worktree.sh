#!/bin/bash
set -e

# Rebase Worktree Script
# Rebases worktree commits on top of the base branch.
# Default branch is read from .worktree.json or auto-detected (main/master).

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

get_default_branch() {
  local root="$1"
  if [ -f "$root/.worktree.json" ] && command -v python3 &>/dev/null; then
    local configured
    configured=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1])).get('default_branch',''))" "$root/.worktree.json" 2>/dev/null) || true
    if [ -n "$configured" ]; then
      echo "$configured"
      return
    fi
  fi
  if git show-ref --verify --quiet refs/heads/main 2>/dev/null; then
    echo "main"
  else
    echo "master"
  fi
}

echo -e "${YELLOW}Rebasing worktree...${NC}"

# Confirm we're in a worktree (not root)
ROOT="$(git worktree list --porcelain | head -1 | sed 's/^worktree //')"
WORKTREE="$(git rev-parse --show-toplevel)"

if [ "$ROOT" = "$WORKTREE" ]; then
  echo -e "${RED}ERROR: Already in root worktree. Cannot rebase root.${NC}"
  exit 1
fi

echo -e "${GREEN}✓${NC} In worktree: $WORKTREE"
echo ""

# Fetch latest changes from origin
echo -e "${YELLOW}Fetching latest changes from origin...${NC}"
git fetch origin
echo ""

# Detect the base branch
echo -e "${YELLOW}Detecting base branch...${NC}"
BASE_BRANCH=""
for branch in $(git for-each-ref --format='%(refname:short)' refs/heads/); do
  mb=$(git merge-base "$branch" HEAD 2>/dev/null) || continue
  timestamp=$(git log -1 --format='%ct' "$mb")
  echo "$timestamp $branch"
done | sort -rn | head -1 | {
  read timestamp branch
  BASE_BRANCH="$branch"
}

# Fallback: use configured or auto-detected default branch
if [ -z "$BASE_BRANCH" ]; then
  BASE_BRANCH=$(get_default_branch "$ROOT")
fi

echo -e "${GREEN}✓${NC} Base branch: ${GREEN}$BASE_BRANCH${NC}"
echo ""

# Update local base branch reference from origin
if git show-ref --verify --quiet "refs/remotes/origin/$BASE_BRANCH"; then
  echo -e "${YELLOW}Updating local $BASE_BRANCH from origin/$BASE_BRANCH...${NC}"
  git fetch origin "$BASE_BRANCH:$BASE_BRANCH" 2>/dev/null || {
    echo -e "${YELLOW}Note: Cannot update $BASE_BRANCH (checked out elsewhere), using origin/$BASE_BRANCH${NC}"
    BASE_BRANCH="origin/$BASE_BRANCH"
  }
  echo ""
fi

# Show what will be rebased
COMMITS_TO_REBASE=$(git rev-list --count "$BASE_BRANCH..HEAD")

if [ "$COMMITS_TO_REBASE" -eq 0 ]; then
  echo -e "${GREEN}✓${NC} Already up to date with $BASE_BRANCH"
  echo "Nothing to rebase."
  exit 0
fi

echo -e "${YELLOW}Commits to be rebased ($COMMITS_TO_REBASE):${NC}"
git log "$BASE_BRANCH..HEAD" --oneline --color=always
echo ""

# Stash uncommitted changes if needed
STASHED=false
if ! git diff-index --quiet HEAD --; then
  echo -e "${YELLOW}Uncommitted changes detected. Stashing...${NC}"
  git stash push -m "rebase-worktree: auto-stash before rebase"
  STASHED=true
  echo -e "${GREEN}✓${NC} Changes stashed"
  echo ""
fi

# Perform the rebase
echo -e "${YELLOW}Rebasing onto $BASE_BRANCH...${NC}"
if git rebase "$BASE_BRANCH"; then
  echo -e "${GREEN}✓${NC} Rebase completed successfully"
  echo ""
else
  echo -e "${RED}✗${NC} Rebase conflicts detected"
  echo ""
  echo "Please resolve conflicts manually, then:"
  echo "  git rebase --continue"
  echo ""
  if [ "$STASHED" = true ]; then
    echo "After resolving, restore stashed changes with:"
    echo "  git stash pop"
  fi
  exit 1
fi

# Restore stashed changes
if [ "$STASHED" = true ]; then
  echo -e "${YELLOW}Restoring stashed changes...${NC}"
  if git stash pop; then
    echo -e "${GREEN}✓${NC} Stashed changes restored"
  else
    echo -e "${RED}✗${NC} Conflict restoring stash"
    echo "Please resolve manually with: git stash pop"
    exit 1
  fi
  echo ""
fi

echo -e "${GREEN}✓ Rebase complete!${NC}"
echo ""
echo "Recent commits:"
git log --oneline --color=always -5
echo ""
echo "Current position:"
git log --oneline --color=always -1 HEAD
