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

# git push on a worktree branch (non-main) — user pushes manually
elif echo "$CMD" | grep -qE 'git\s+(push|p)\b'; then
    BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)
    if [[ -n "$BRANCH" && "$BRANCH" != "main" && "$BRANCH" != "master" ]]; then
        DANGER="git push on branch '$BRANCH' (worktree branches must not be pushed — hand off to user)"
    fi

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

# rm targeting pipeline sample/report directories (catches plain rm, not just rm -rf)
elif echo "$CMD" | grep -qE '\brm\b.*(/workspace/samples|/workspace/cti-reports)'; then
    DANGER="rm on protected pipeline directory (/workspace/samples or /workspace/cti-reports)"
fi

if [[ -n "$DANGER" ]]; then
    cat >&2 <<MSG
GUARDRAIL [guard-bash]: Destructive command detected — $DANGER
  Command: $CMD
Confirm this is intentional before proceeding.
MSG
    exit 1
fi

# git commit carrying Claude/Anthropic attribution — block before it runs.
# Complements the commit-msg hook (which strips it post-hoc) and the
# includeCoAuthoredBy=false setting (which prevents it). This catches an
# explicit attempt to embed a byline via -m/heredoc.
if echo "$CMD" | grep -qE 'git\s+(commit|c)\b' \
   && echo "$CMD" | grep -qiE 'Co-Authored-By:[[:space:]]*Claude|Co-authored-by:.*anthropic|Generated with .*Claude Code|noreply@anthropic\.com'; then
    cat >&2 <<MSG
GUARDRAIL [guard-bash]: git commit includes Claude/Anthropic attribution.
  Per user policy, Claude must not appear as a contributor.
  Remove the Co-Authored-By / "Generated with Claude Code" line from the commit message.
MSG
    exit 1
fi

exit 0
