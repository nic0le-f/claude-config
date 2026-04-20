#!/bin/bash
# memory-remind.sh - Remind to save notable findings/decisions to memory
#
# Fires on Stop. After THRESHOLD turns, prompts once per session to consider
# saving non-obvious context to ~/.claude memory for future sessions.

THRESHOLD=15
STATE_DIR="$HOME/.claude/state/sessions"
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

REMINDED_FILE="$STATE_DIR/${SESSION_ID}.memory-reminded"
COUNTER_FILE="$STATE_DIR/$SESSION_ID"

# Only remind once per session
[[ -f "$REMINDED_FILE" ]] && exit 0

COUNT=0
[[ -f "$COUNTER_FILE" ]] && COUNT=$(cat "$COUNTER_FILE" 2>/dev/null || echo 0)

if [[ "$COUNT" -ge "$THRESHOLD" ]]; then
    touch "$REMINDED_FILE"
    echo "MEMORY [memory-remind]: Session has $COUNT turns — anything worth saving to memory? (decisions, preferences, project context)"
fi

exit 0
