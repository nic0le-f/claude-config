#!/bin/bash
# uncommitted-remind.sh - Advisory reminder at session end
#
# Fires on Stop event. If there are uncommitted changes in the current
# git repo, prints a reminder to the user. Never blocks.

# Only relevant inside a git repo
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    exit 0
fi

# Check for uncommitted changes
if [[ -n "$(git status --porcelain 2>/dev/null)" ]]; then
    REPO=$(basename "$(git rev-parse --show-toplevel 2>/dev/null)")
    BRANCH=$(git branch --show-current 2>/dev/null)
    echo "Reminder: uncommitted changes in '$REPO' (branch: $BRANCH). Commit before closing the session?"
fi

exit 0
