#!/usr/bin/env bash
input=$(cat)
model=$(echo "$input" | jq -r '.model.display_name // "Unknown"')
GREEN=$'\033[0;32m'; YELLOW=$'\033[0;33m'; RED=$'\033[0;31m'; CYAN=$'\033[0;36m'; RESET=$'\033[0m'

# Context window bar
used=$(echo "$input" | jq -r '.context_window.used_percentage // empty')
if [ -n "$used" ]; then
  filled=$(printf "%.0f" "$(echo "$used * 10 / 100" | bc -l)")
  empty=$((10 - filled)); bar=""
  for i in $(seq 1 "$filled"); do bar="${bar}█"; done
  for i in $(seq 1 "$empty"); do bar="${bar}░"; done
  used_int=$(printf "%.0f" "$used")
  if [ "$used_int" -lt 30 ]; then ctx_str="${GREEN}${used_int}% [${bar}]${RESET}"
  elif [ "$used_int" -lt 45 ]; then ctx_str="${YELLOW}${used_int}% [${bar}]${RESET}"
  else ctx_str="${RED}${used_int}% [${bar}]${RESET}"; fi
else ctx_str="ctx: --"; fi

# Git branch + cwd
branch=$(git -C "$(echo "$input" | jq -r '.workspace.current_dir')" --no-optional-locks symbolic-ref --short HEAD 2>/dev/null)
[ -z "$branch" ] && branch=$(git -C "$(echo "$input" | jq -r '.workspace.current_dir')" --no-optional-locks rev-parse --short HEAD 2>/dev/null)
cwd=$(echo "$input" | jq -r '.workspace.current_dir // .cwd // empty')
short_cwd=$(echo "$cwd" | sed "s|^$HOME|~|")

# Rate limits (non-enterprise only — present in JSON when available)
five_pct=$(echo "$input" | jq -r '.rate_limits.five_hour.used_percentage // empty')
week_pct=$(echo "$input" | jq -r '.rate_limits.seven_day.used_percentage // empty')
rate_str=""
if [ -n "$five_pct" ] || [ -n "$week_pct" ]; then
  if [ -n "$five_pct" ]; then
    five_int=$(printf "%.0f" "$five_pct")
    if [ "$five_int" -gt 80 ]; then rate_str="${RED}5h:${five_int}%${RESET}"
    else rate_str="5h:${five_int}%"; fi
  fi
  if [ -n "$week_pct" ]; then
    week_int=$(printf "%.0f" "$week_pct")
    if [ "$week_int" -gt 80 ]; then week_str="${RED}7d:${week_int}%${RESET}"
    else week_str="7d:${week_int}%"; fi
    rate_str="${rate_str:+$rate_str }$week_str"
  fi
else
  # Enterprise: show cache hit % + today's messages from stats-cache
  stats_file="$HOME/.claude/stats-cache.json"
  if [ -f "$stats_file" ]; then
    # Cache hit ratio across all models
    cache_hit=$(jq -r '
      .modelUsage | to_entries | map(.value) |
      { read: (map(.cacheReadInputTokens) | add // 0),
        total: (map(.cacheReadInputTokens + .inputTokens) | add // 0) } |
      if .total > 0 then ((.read / .total) * 100 | floor) else 0 end
    ' "$stats_file" 2>/dev/null)

    # Today message count
    today=$(date +%Y-%m-%d)
    today_msgs=$(jq -r --arg d "$today" '
      (.dailyActivity | to_entries[] | select(.value.date == $d) | .value.messageCount) // 0
    ' "$stats_file" 2>/dev/null)
    today_msgs=${today_msgs:-0}

    if [ -n "$cache_hit" ]; then
      if [ "$cache_hit" -ge 80 ]; then cache_str="${GREEN}cache:${cache_hit}%${RESET}"
      elif [ "$cache_hit" -ge 50 ]; then cache_str="${YELLOW}cache:${cache_hit}%${RESET}"
      else cache_str="${RED}cache:${cache_hit}%${RESET}"; fi
    fi

    if [ "$today_msgs" -ge 100 ]; then msgs_str="${RED}msgs:${today_msgs}${RESET}"
    elif [ "$today_msgs" -ge 50 ]; then msgs_str="${YELLOW}msgs:${today_msgs}${RESET}"
    else msgs_str="${CYAN}msgs:${today_msgs}${RESET}"; fi

    [ -n "$cache_str" ] && rate_str="$cache_str"
    [ -n "$msgs_str" ] && rate_str="${rate_str:+$rate_str }$msgs_str"
  fi
fi

# Assemble
parts=""; [ -n "$short_cwd" ] && parts="$short_cwd"
[ -n "$branch" ] && parts="$parts | $branch"
parts="$parts | $model"
[ -n "$rate_str" ] && parts="$parts | $ctx_str | $rate_str" || parts="$parts | $ctx_str"
printf "%s" "$parts"
