#!/bin/bash
# guard-bash.sh - Soft-warn on destructive shell commands
#
# Fires on Bash tool calls. Checks the command string for known-dangerous
# patterns and exits 1 with a warning so Claude must confirm intent.

INPUT=$(cat)

# Extract the command from tool_input
CMD=$(echo "$INPUT" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    print(d.get('tool_input', {}).get('command', ''))
except Exception:
    print('')
" 2>/dev/null)

DANGER=""

# rm -rf / rm -fr (any flag combo containing both r and f)
if echo "$CMD" | grep -qE 'rm\s+-[a-zA-Z]*(r[a-zA-Z]*f|f[a-zA-Z]*r)[a-zA-Z]*'; then
    DANGER="rm -rf (recursive force delete)"

# git push --force / -f
elif echo "$CMD" | grep -qE 'git\s+(push|p)\s+.*(\-\-force|-f\b)'; then
    DANGER="git push --force (overwrites remote history)"

# git reset --hard
elif echo "$CMD" | grep -qE 'git\s+reset\s+--hard'; then
    DANGER="git reset --hard (discards uncommitted changes)"

# git clean -f / -fd / -fx
elif echo "$CMD" | grep -qE 'git\s+clean\s+.*-[a-zA-Z]*f'; then
    DANGER="git clean -f (permanently deletes untracked files)"

# git branch -D (force delete)
elif echo "$CMD" | grep -qE 'git\s+branch\s+.*-D'; then
    DANGER="git branch -D (force deletes branch, may lose commits)"

# dd with if= (raw disk operations)
elif echo "$CMD" | grep -qE '\bdd\b.*\bif='; then
    DANGER="dd (raw disk read/write)"

# mkfs (format a filesystem)
elif echo "$CMD" | grep -qE '\bmkfs'; then
    DANGER="mkfs (formats/destroys filesystem)"

# writes directly to block devices
elif echo "$CMD" | grep -qE '>\s*/dev/(sd|hd|nvme|disk|rd|vd)'; then
    DANGER="direct write to block device"

# chmod 777 recursively
elif echo "$CMD" | grep -qE 'chmod\s+-R\s+777|chmod\s+777\s+-R'; then
    DANGER="chmod -R 777 (world-writable permissions)"
fi

if [[ -n "$DANGER" ]]; then
    cat >&2 <<MSG
GUARDRAIL [guard-bash]: Destructive command detected — $DANGER
  Command: $CMD
Confirm this is intentional before proceeding.
MSG
    exit 1
fi

exit 0
