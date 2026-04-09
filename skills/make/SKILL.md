---
name: make
description: Run make targets in any project from any location. Automatically finds the project root and runs make commands. Use when the user asks to run make commands like "make restart", "make reload-safe", or "/make <target>".
---

# Make

Run make targets in any project from any location.

## Usage

Use `/make <target>` to run any make target in the project root.

## Examples

```
/make restart
/make reload-safe
/make logs
/make help
```

## How it works

- Searches for a Makefile by traversing up from the current directory
- Runs `make <target>` in the directory containing the Makefile
- Works from any subdirectory within a project
- Works with any project that has a Makefile
