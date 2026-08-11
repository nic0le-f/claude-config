#!/bin/bash
# claude-md-check.sh - Warn once per session if cwd git repo has no CLAUDE.md
#
# Fires on PreToolUse for Write, Edit, Bash. Checks once per session+repo pair
# so it doesn't spam. Never blocks (exit 0 always).

STATE_DIR="$HOME/.claude/state/claudemd-warned"
mkdir -p "$STATE_DIR"

INPUT=$(cat)

SESSION_ID=$(echo "$INPUT" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    print(d.get('session_id', 'default'))
except Exception:
    print('default')
" 2>/dev/null)
SESSION_ID="${SESSION_ID:-default}"

# Only check inside a git repo
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    exit 0
fi

REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null)
[[ -z "$REPO_ROOT" ]] && exit 0

# Skip ~/.claude itself — it has its own CLAUDE.md
[[ "$REPO_ROOT" == "$HOME/.claude" ]] && exit 0

# Dedup: warn once per session+repo
WARNED_KEY=$(echo "${SESSION_ID}:${REPO_ROOT}" | tr '/' '_' | tr ':' '_')
WARNED_FILE="$STATE_DIR/$WARNED_KEY"
[[ -f "$WARNED_FILE" ]] && exit 0

if [[ ! -f "$REPO_ROOT/CLAUDE.md" ]]; then
    touch "$WARNED_FILE"
    echo "SETUP [claude-md-check]: No CLAUDE.md found in '$REPO_ROOT' — run /init to create one and give future sessions instant project context."
fi

# Prune warn files older than 7 days
find "$STATE_DIR" -type f -mmin +10080 -delete 2>/dev/null

exit 0
