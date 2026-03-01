#!/bin/bash
# guard-main.sh - Soft-block code writes to main/master branch
#
# Fires on Write and Edit tool calls. If the repo has commits and we're
# on main/master, warns Claude and exits 1 so it must create a worktree
# or branch before proceeding. Doc files are allowed on main.

INPUT=$(cat)

# Extract tool name and file path in one pass
RESULT=$(echo "$INPUT" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    tool = d.get('tool_name', '')
    params = d.get('tool_input', {})
    filepath = params.get('file_path', params.get('path', ''))
    print(tool)
    print(filepath)
except Exception:
    print('')
    print('')
" 2>/dev/null)

TOOL=$(echo "$RESULT" | head -1)
FILE=$(echo "$RESULT" | tail -1)

# Only guard Write and Edit
if [[ "$TOOL" != "Write" && "$TOOL" != "Edit" ]]; then
    exit 0
fi

# Only relevant inside a git repo
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    exit 0
fi

# Allow writes on a new repo with no commits yet (initial scaffold phase)
if ! git rev-parse HEAD > /dev/null 2>&1; then
    exit 0
fi

# Check current branch
BRANCH=$(git branch --show-current 2>/dev/null)
if [[ "$BRANCH" != "main" && "$BRANCH" != "master" ]]; then
    exit 0
fi

# Allow doc/config files directly on main
BASENAME=$(basename "$FILE")
case "$BASENAME" in
    *.md|*.txt|*.rst|.gitignore|.gitattributes|LICENSE*)
        exit 0
        ;;
esac

# Soft block — Claude sees this message and must resolve before retrying
cat >&2 <<MSG
GUARDRAIL [guard-main]: Attempted to write '$FILE' on '$BRANCH'.
Code files must live in a feature worktree, not main.
  → Run /dev to initialize a worktree, or:
  → git worktree add .worktrees/<name> -b <name>
Docs and configs (*.md, .gitignore, etc.) are allowed on main.
MSG

exit 1
