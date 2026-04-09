# claude-config

Personal Claude Code configuration for security research. Optimized for low overhead on day-to-day analysis work, with structured git discipline for tool development.

## Agents

Defined in `agents/`. Visible via `/agents` dialog.

| Agent | Model | Description |
|-------|-------|-------------|
| `re-agent` | opus | Autonomous RE pipeline — 8-phase analysis from intake to report. Spawns subagents, writes structured reports, tracks progress across sessions via project memory. `acceptEdits` permission mode, 100 turn cap. |
| `binninja-agent` | opus | Binary Ninja MCP specialist — triage, decompile, rename, retype, xrefs. Follows `mw_` naming and confidence conventions. |
| `script-analyzer` | opus | Malicious script analysis — deobfuscation, call graphs, IOC extraction. Supports PS, Python, JS, VBA, shell. |
| `enrichment-agent` | sonnet | Threat intel enrichment — VirusTotal, MalwareBazaar, Shodan lookups. |
| `msdn-qa` | sonnet | Validates Windows API calls in analysis reports against MSDN documentation. |
| `intezer-triage-agent` | opus | Intezer alert investigation — fetches alert data via API, enriches IOCs (VT/Shodan), validates automated classifications. Spawned by `/intezer-triage` for deep investigation. |

`re-agent` is the main entry point for full-pipeline analysis. It orchestrates the other 4 as subagents.

## Skills

| Command | Description |
|---------|-------------|
| `/malware-analyst` | Malware RE conventions (Binary Ninja MCP, naming, confidence, YARA, reporting). Used standalone for quick focused binary work, or referenced by `re-agent` for its standards. |
| `/audit-codebase` | Security audit of a source folder |
| `/disclose` | Prepare responsible disclosure |
| `/intezer-triage` | Intezer alert triage — validate automated classification, suggest fixes (jq filter, agent instructions, or bug report). Spawns `intezer-triage-agent` for deep investigation. |
| `/intezer-alert-jq` | Generate jq `select(...)` queries to classify/filter Intezer alert JSON objects from natural-language criteria. |

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
