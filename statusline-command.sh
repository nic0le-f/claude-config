#!/usr/bin/env bash
input=$(cat)
model=$(echo "$input" | jq -r '.model.display_name // "Unknown"')
GREEN=$'\033[0;32m'; YELLOW=$'\033[0;33m'; RED=$'\033[0;31m'; RESET=$'\033[0m'
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
branch=$(git -C "$(echo "$input" | jq -r '.workspace.current_dir')" --no-optional-locks symbolic-ref --short HEAD 2>/dev/null)
[ -z "$branch" ] && branch=$(git -C "$(echo "$input" | jq -r '.workspace.current_dir')" --no-optional-locks rev-parse --short HEAD 2>/dev/null)
cwd=$(echo "$input" | jq -r '.workspace.current_dir // .cwd // empty')
short_cwd=$(echo "$cwd" | sed "s|^$HOME|~|")
five_pct=$(echo "$input" | jq -r '.rate_limits.five_hour.used_percentage // empty')
if [ -n "$five_pct" ]; then
  five_int=$(printf "%.0f" "$five_pct")
  if [ "$five_int" -gt 80 ]; then five_str="${RED}5h:${five_int}%${RESET}"
  else five_str="5h:${five_int}%"; fi
else five_str=""; fi
week_pct=$(echo "$input" | jq -r '.rate_limits.seven_day.used_percentage // empty')
if [ -n "$week_pct" ]; then
  week_int=$(printf "%.0f" "$week_pct")
  if [ "$week_int" -gt 80 ]; then week_str="${RED}7d:${week_int}%${RESET}"
  else week_str="7d:${week_int}%"; fi
else week_str=""; fi
rate_str=""
[ -n "$five_str" ] && rate_str="$five_str"
[ -n "$week_str" ] && rate_str="${rate_str:+$rate_str }$week_str"
parts=""; [ -n "$short_cwd" ] && parts="$short_cwd"
[ -n "$branch" ] && parts="$parts | $branch"
parts="$parts | $model"
[ -n "$rate_str" ] && parts="$parts | $ctx_str | $rate_str" || parts="$parts | $ctx_str"
printf "%s" "$parts"
