#!/bin/bash
set -e

# Merge Worktree Script
# Squash-merge worktree commits to the default branch and remove worktree.
# Default branch is read from .worktree.json or auto-detected (main/master).

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
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

echo -e "${YELLOW}Checking worktree status...${NC}"

ROOT="$(git worktree list --porcelain | head -1 | sed 's/^worktree //')"
WORKTREE="$(git rev-parse --show-toplevel)"

if [ "$ROOT" = "$WORKTREE" ]; then
    echo -e "${RED}ERROR: Already on the default branch, not in a worktree${NC}"
    exit 1
fi

DEFAULT_BRANCH=$(get_default_branch "$ROOT")

echo -e "${GREEN}✓${NC} Root: $ROOT"
echo -e "${GREEN}✓${NC} Worktree: $WORKTREE"
echo -e "${GREEN}✓${NC} Target branch: $DEFAULT_BRANCH"
echo ""

WORKTREE_HEAD="$(git rev-parse HEAD)"
echo "Worktree HEAD: $WORKTREE_HEAD"
echo ""

echo "Commits to merge:"
git log "$DEFAULT_BRANCH..HEAD" --oneline
COMMIT_COUNT=$(git rev-list --count "$DEFAULT_BRANCH..HEAD")
echo ""

if [ "$COMMIT_COUNT" -eq 0 ]; then
    echo -e "${RED}No commits to merge${NC}"
    exit 1
fi

# Check for uncommitted changes
UNCOMMITTED=$(git status --short)
if [ -n "$UNCOMMITTED" ]; then
    echo -e "${YELLOW}Warning: Uncommitted changes detected:${NC}"
    echo "$UNCOMMITTED"
    echo ""
    echo "These will NOT be included in the merge."
    read -p "Continue? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Generate commit message from the commits
if [ "$COMMIT_COUNT" -eq 1 ]; then
    TITLE=$(git log -1 --format=%s)
    BODY=$(git log -1 --format=%b)
else
    FIRST_COMMIT=$(git log "$DEFAULT_BRANCH..HEAD" --format=%s | tail -1)
    TITLE="$FIRST_COMMIT"
    BODY=$(git log "$DEFAULT_BRANCH..HEAD" --format="- %s" | tac)
fi

echo "Merge commit message:"
echo "---"
echo "$TITLE"
if [ -n "$BODY" ]; then
    echo ""
    echo "$BODY"
fi
echo "---"
echo ""

# Perform squash merge
echo -e "${YELLOW}Squash merging to $DEFAULT_BRANCH...${NC}"
git -C "$ROOT" merge --squash "$WORKTREE_HEAD"

FULL_MESSAGE="$TITLE"
if [ -n "$BODY" ]; then
    FULL_MESSAGE="$TITLE

$BODY"
fi

git -C "$ROOT" commit -m "$FULL_MESSAGE

Co-Authored-By: Claude <noreply@anthropic.com>"

echo -e "${GREEN}✓${NC} Merge committed"
echo ""

git -C "$ROOT" log -1 --oneline
echo ""

# Remove worktree
echo -e "${YELLOW}Removing worktree...${NC}"
if git worktree remove "$WORKTREE" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} Worktree removed cleanly"
else
    echo -e "${YELLOW}Worktree has untracked files, forcing removal...${NC}"
    git worktree remove --force "$WORKTREE"
    echo -e "${GREEN}✓${NC} Worktree removed (forced)"
fi

echo ""
echo -e "${GREEN}✓ Merge complete!${NC}"
echo ""
echo "Remaining worktrees:"
git -C "$ROOT" worktree list
