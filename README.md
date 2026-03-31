# claude-config

Personal Claude Code configuration for security research. Optimized for low overhead on day-to-day analysis work, with structured git discipline for tool development.

## Skills

| Command | Description |
|---------|-------------|
| `/research` | Append a structured findings entry to `research.md` |
| `/malware-analyst` | Malware reverse engineering session |
| `/audit-codebase` | Security audit of a source folder |
| `/disclose` | Prepare responsible disclosure |

Planning uses native plan mode. Code work uses native worktrees (`EnterWorktree`).

## Hooks

| Hook | Event | Behavior |
|------|-------|----------|
| `guard-main.sh` | `PreToolUse` (Write, Edit) | Soft-blocks code writes to `main` once the repo has commits. Docs and configs are allowed. |
| `guard-bash.sh` | `PreToolUse` (Bash) | Soft-warns on destructive commands: `rm -rf`, `git push --force`, `git reset --hard`, `git clean -f`, `git branch -D`, `dd`, `mkfs`. |
| `uncommitted-remind.sh` | `Stop` | Advisory reminder if there are uncommitted changes at session end. |

All hooks are soft blocks (exit 1) — Claude sees the warning and must resolve it, but there's no hard system lockout.

## Git Workflow

- Code changes always go through worktrees (native `EnterWorktree`), never directly on `main`
- `guard-main.sh` enforces this as a safety net
- Commits use conventional prefixes: `feat:`, `fix:`, `add:`, `chore:`, `docs:`
- `git push` always requires manual approval

## What's Gitignored

Runtime and session state that stays local:
- `history.jsonl`, `projects/`, `session-env/`, `shell-snapshots/`
- `cache/`, `debug/`, `backups/`, `todos/`, `plans/`
- `settings.local.json` (local permission overrides)
- `plugins/marketplaces/` (has its own git history)
