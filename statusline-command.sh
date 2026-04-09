#!/usr/bin/env bash
# Claude Code status line script
# Receives JSON via stdin with session/model/context data
# Mirrors p10k prompt elements: dir + vcs + model + context

input=$(cat)

# Extract fields
cwd=$(echo "$input" | jq -r '.workspace.current_dir // .cwd // ""')
model=$(echo "$input" | jq -r '.model.display_name // ""')
used_pct=$(echo "$input" | jq -r '.context_window.used_percentage // empty')
vim_mode=$(echo "$input" | jq -r '.vim.mode // empty')

# Shorten cwd: replace $HOME with ~
cwd="${cwd/#$HOME/\~}"

# ANSI color codes (dimmed-friendly)
RESET='\033[0m'
DIM='\033[2m'
CYAN='\033[36m'
YELLOW='\033[33m'
GREEN='\033[32m'
RED='\033[31m'
BLUE='\033[34m'
MAGENTA='\033[35m'

# Git branch/status (mirrors p10k vcs segment)
git_part=""
if git_dir=$(git -C "$cwd" rev-parse --git-dir --no-optional-locks 2>/dev/null | head -1); then
    branch=$(git -C "$cwd" symbolic-ref --short HEAD 2>/dev/null || git -C "$cwd" rev-parse --short HEAD 2>/dev/null)
    if [ -n "$branch" ]; then
        # Check for dirty state
        if git -C "$cwd" diff --quiet --no-optional-locks 2>/dev/null && \
           git -C "$cwd" diff --cached --quiet --no-optional-locks 2>/dev/null; then
            git_part=" $(printf "${GREEN}${branch}${RESET}")"
        else
            git_part=" $(printf "${YELLOW}${branch}*${RESET}")"
        fi
    fi
fi

# Build context usage indicator
ctx_part=""
if [ -n "$used_pct" ]; then
    used_int=${used_pct%.*}
    if [ "$used_int" -ge 80 ]; then
        ctx_color="$RED"
    elif [ "$used_int" -ge 50 ]; then
        ctx_color="$YELLOW"
    else
        ctx_color="$GREEN"
    fi
    ctx_part=" $(printf "${ctx_color}ctx:${used_int}%%${RESET}")"
fi

# Vim mode indicator
vim_part=""
if [ -n "$vim_mode" ]; then
    if [ "$vim_mode" = "INSERT" ]; then
        vim_part=" $(printf "${GREEN}[INSERT]${RESET}")"
    else
        vim_part=" $(printf "${YELLOW}[NORMAL]${RESET}")"
    fi
fi

printf "${DIM}${CYAN}%s${RESET}%s ${DIM}%s${RESET}%s%s" \
    "$cwd" \
    "$git_part" \
    "$model" \
    "$ctx_part" \
    "$vim_part"
