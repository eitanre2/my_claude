#!/bin/bash
set -e

# Find the project root by traversing up to find a Makefile
find_makefile() {
  local dir="$PWD"
  while [ "$dir" != "/" ]; do
    if [ -f "$dir/Makefile" ]; then
      echo "$dir"
      return 0
    fi
    dir=$(dirname "$dir")
  done
  return 1
}

# Get the make target from arguments
TARGET="$1"

if [ -z "$TARGET" ]; then
  echo "Usage: /make <target>"
  echo ""
  echo "Examples:"
  echo "  /make restart"
  echo "  /make reload-safe"
  echo "  /make logs"
  exit 1
fi

# Find project root
PROJECT_ROOT=$(find_makefile)

if [ -z "$PROJECT_ROOT" ]; then
  echo "Error: No Makefile found in current directory or any parent directory"
  exit 1
fi

# Run make in the project root
echo "Running: make $TARGET in $PROJECT_ROOT"
cd "$PROJECT_ROOT" && make "$TARGET"
