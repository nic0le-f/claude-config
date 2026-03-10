#!/bin/bash
# agent-verbosity-check.sh - Warn when an Agent subagent returns an oversized response
#
# Fires on PostToolUse for the Agent tool. Prints an advisory if the
# tool_response exceeds CHAR_THRESHOLD. Never blocks.

CHAR_THRESHOLD=3000

INPUT=$(cat)

RESP_LEN=$(echo "$INPUT" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    resp = d.get('tool_response', '')
    if not isinstance(resp, str):
        resp = json.dumps(resp)
    print(len(resp))
except Exception:
    print(0)
" 2>/dev/null)

RESP_LEN="${RESP_LEN:-0}"

if [[ "$RESP_LEN" -gt "$CHAR_THRESHOLD" ]]; then
    echo "TOKEN WARNING [agent-verbosity]: Agent returned ${RESP_LEN} chars (threshold: ${CHAR_THRESHOLD}). Remind agents: summarize findings only, no raw output."
fi

exit 0
