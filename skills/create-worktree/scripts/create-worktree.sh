#!/bin/bash
set -e

# Create a new git worktree with optional symlinks and setup commands.
# Configuration is read from .worktree.json in the project root (if present).
# Usage: create-worktree.sh [branch_name]

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

BRANCH_NAME="$1"

echo -e "${YELLOW}Creating worktree...${NC}"

# Locate root worktree
ROOT="$(git worktree list --porcelain | head -1 | sed 's/^worktree //')"
WORKTREE="$(git rev-parse --show-toplevel)"

if [ "$ROOT" != "$WORKTREE" ]; then
  echo "Warning: Not in root worktree. Creating from current location: $WORKTREE"
  ROOT="$WORKTREE"
fi

echo "Root: $ROOT"

# Get current branch or commit
CURRENT_BRANCH="$(git rev-parse --abbrev-ref HEAD)"
if [ "$CURRENT_BRANCH" = "HEAD" ]; then
  CURRENT_COMMIT="$(git rev-parse HEAD)"
  echo "Branch: detached HEAD at $CURRENT_COMMIT"
else
  echo "Branch: $CURRENT_BRANCH"
fi

# Generate worktree ID (3 random alphanumeric characters)
WORKTREE_ID="$(cat /dev/urandom | tr -dc 'a-z0-9' | fold -w 3 | head -n 1)"
echo "Worktree ID: $WORKTREE_ID"

# Ensure .claude/worktrees is in .gitignore (shared — applies to all users)
if ! grep -q "^\.claude/worktrees" "$ROOT/.gitignore" 2>/dev/null; then
  echo ".claude/worktrees" >> "$ROOT/.gitignore"
  echo "Added .claude/worktrees to .gitignore"
fi

# Ensure .worktree.json is in .git/info/exclude (local-only — per-developer setup prefs)
if [ -f "$ROOT/.worktree.json" ]; then
  EXCLUDE_FILE="$(git rev-parse --git-common-dir)/info/exclude"
  if [ -f "$EXCLUDE_FILE" ] && ! grep -q "^\.worktree\.json$" "$EXCLUDE_FILE" 2>/dev/null; then
    echo ".worktree.json" >> "$EXCLUDE_FILE"
    echo "Added .worktree.json to .git/info/exclude (local-only)"
  fi
fi

# Create worktree
WORKTREE_BASE="$ROOT/.claude/worktrees"
mkdir -p "$WORKTREE_BASE"
WORKTREE_PATH="$WORKTREE_BASE/$WORKTREE_ID"

if [ "$CURRENT_BRANCH" = "HEAD" ]; then
  git worktree add --detach "$WORKTREE_PATH" "$CURRENT_COMMIT"
else
  git worktree add --detach "$WORKTREE_PATH" "$CURRENT_BRANCH"
fi

cd "$WORKTREE_PATH"

# Create branch if name was provided
if [ -n "$BRANCH_NAME" ]; then
  echo -e "\n${YELLOW}Creating branch: $BRANCH_NAME${NC}"
  git checkout -b "$BRANCH_NAME"
  echo -e "${GREEN}✓${NC} Branch created and checked out"
fi

# --- Project-specific setup from .worktree.json ---
CONFIG="$ROOT/.worktree.json"
HAS_CONFIG=false
if [ -f "$CONFIG" ] && command -v python3 &>/dev/null; then
  HAS_CONFIG=true
fi

# Create symbolic links from config
echo -e "\n${YELLOW}Creating symbolic links...${NC}"
LINK_COUNT=0

if [ "$HAS_CONFIG" = true ]; then
  SYMLINKS_JSON=$(python3 -c "
import json, sys
cfg = json.load(open(sys.argv[1]))
for s in cfg.get('symlinks', []):
    if isinstance(s, str):
        print(s + '\t' + s)
    elif isinstance(s, dict):
        print(s['target'] + '\t' + s['source'])
" "$CONFIG" 2>/dev/null) || true

  while IFS=$'\t' read -r target source; do
    [ -z "$target" ] && continue
    SOURCE_PATH="$ROOT/$source"
    TARGET_PATH="$WORKTREE_PATH/$target"

    if [ -e "$SOURCE_PATH" ]; then
      TARGET_DIR=$(dirname "$TARGET_PATH")
      [ ! -d "$TARGET_DIR" ] && mkdir -p "$TARGET_DIR"
      ln -s "$SOURCE_PATH" "$TARGET_PATH"
      echo -e "${GREEN}✓${NC} Linked $target → $source"
      LINK_COUNT=$((LINK_COUNT + 1))
    else
      echo -e "${YELLOW}⚠${NC} Skipped $source (not found in root)"
    fi
  done <<< "$SYMLINKS_JSON"
fi

if [ "$LINK_COUNT" -eq 0 ]; then
  echo "  No symlinks configured"
fi

# Post-create commands
echo -e "\n${YELLOW}Running post-create setup...${NC}"
SETUP_RAN=false

if [ "$HAS_CONFIG" = true ]; then
  POST_CREATE=$(python3 -c "
import json, sys
cfg = json.load(open(sys.argv[1]))
for cmd in cfg.get('post_create', []):
    print(cmd)
" "$CONFIG" 2>/dev/null) || true

  if [ -n "$POST_CREATE" ]; then
    while IFS= read -r cmd; do
      [ -z "$cmd" ] && continue
      echo -e "  Running: ${cmd}"
      eval "$cmd"
      echo -e "${GREEN}✓${NC} Done"
      SETUP_RAN=true
    done <<< "$POST_CREATE"
  fi
fi

# Fallback: auto-detect package managers if no post_create in config
if [ "$SETUP_RAN" = false ]; then
  if [ -f "$WORKTREE_PATH/package.json" ]; then
    echo "Installing npm packages..."
    npm install --silent 2>/dev/null
    echo -e "${GREEN}✓${NC} npm packages installed"
  fi

  if [ -f "$WORKTREE_PATH/Gemfile" ]; then
    echo "Installing Ruby gems..."
    bundle install --quiet
    echo -e "${GREEN}✓${NC} Ruby gems installed"
  fi

  if [ -f "$WORKTREE_PATH/requirements.txt" ]; then
    echo "Installing Python packages..."
    pip install -r requirements.txt --quiet
    echo -e "${GREEN}✓${NC} Python packages installed"
  fi
fi

# Display summary
echo -e "\n${GREEN}✓ Worktree created successfully!${NC}"
echo ""
echo "Worktree path: $WORKTREE_PATH"
echo "Worktree ID: $WORKTREE_ID"
[ -n "$BRANCH_NAME" ] && echo "Branch: $BRANCH_NAME"
echo ""

# Output machine-readable values
echo "WORKTREE_PATH=$WORKTREE_PATH"
echo "WORKTREE_ID=$WORKTREE_ID"
[ -n "$BRANCH_NAME" ] && echo "WORKTREE_BRANCH=$BRANCH_NAME"
