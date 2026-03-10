#!/bin/bash
# compact-remind.sh - Nudge user to run /compact when session grows long
#
# Fires on Stop event. Tracks turns per session_id, warns at THRESHOLD
# and every INTERVAL turns after. Session files auto-expire after 24h.

THRESHOLD=25
INTERVAL=5
STATE_DIR="$HOME/.claude/state/sessions"
mkdir -p "$STATE_DIR"

# Parse session_id from hook input
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

COUNTER_FILE="$STATE_DIR/$SESSION_ID"

# Increment counter
COUNT=0
[[ -f "$COUNTER_FILE" ]] && COUNT=$(cat "$COUNTER_FILE" 2>/dev/null || echo 0)
COUNT=$((COUNT + 1))
echo "$COUNT" > "$COUNTER_FILE"

# Warn at threshold and every INTERVAL turns after
if [[ "$COUNT" -ge "$THRESHOLD" ]] && [[ $(( (COUNT - THRESHOLD) % INTERVAL )) -eq 0 ]]; then
    echo "CONTEXT [compact-remind]: $COUNT turns in this session — run /compact to compress history."
fi

# Prune session files older than 24h (macOS-compatible)
find "$STATE_DIR" -type f -mmin +1440 -delete 2>/dev/null

exit 0
