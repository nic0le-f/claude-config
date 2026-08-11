# claude-config

Personal Claude Code configuration for security research. Optimized for low overhead on day-to-day analysis work, with structured git discipline for tool development.

## Agents

Defined in `agents/`. Visible via `/agents` dialog.

| Agent | Model | Description |
|-------|-------|-------------|
| `re-agent` | opus | Autonomous RE pipeline — 8-phase analysis from intake to report. Spawns subagents, writes structured reports, tracks progress across sessions via project memory. `acceptEdits` permission mode, 100 turn cap. |
| `malcat-reverse-engineer` | opus | Binary analysis via Malcat MCP — file format parsing, strings, entropy, YARA, anomalies, transform/decrypt chains, decompilation. Use for breadth-first structural analysis. |
| `binninja-agent` | sonnet | Binary Ninja MCP specialist — deep decompilation, renaming, retyping, xrefs. Follows `mw_` naming and confidence conventions. Use for surgical depth on specific functions. |
| `script-analyzer` | opus | Malicious script analysis — deobfuscation, call graphs, IOC extraction. Supports PS, Python, JS, VBA, shell. Standalone or subagent mode. |
| `enrichment-agent` | sonnet | Threat intel enrichment — VirusTotal, MalwareBazaar, Shodan lookups. |
| `msdn-qa` | sonnet | Validates Windows API calls in analysis reports against MSDN documentation. Standalone or subagent mode. |

`re-agent` is the main entry point for full-pipeline analysis. It orchestrates the other agents as subagents. Malcat and Binary Ninja agents are complementary — use Malcat for breadth (format, strings, anomalies), BN for depth (decompilation, annotation).

## Skills

| Command | Description |
|---------|-------------|
| `/re-triage` | Cold triage — classify sample, check for packing, produce triage summary (Phases 0–2 only). Pass sample path as argument. |
| `/re-dive` | Targeted deep dive on a specific question about a sample. Reads existing findings, skips re-triage. |
| `/re-compare` | Multi-sample comparative analysis — shared code, infrastructure overlap, lineage. |
| `/malware-analyst` | Full analyst role activation for open-ended investigation. |
| `/audit-codebase` | Security audit of a source folder. |
| `/disclose` | Prepare responsible disclosure. |

Planning uses native plan mode. Code work uses native worktrees (`EnterWorktree`).

## Typical Session Flow

Always `cd` into the specific sample folder before starting Claude. This scopes reports and agent memory to the investigation.

```
cd ~/Downloads/samples/sample-xyz/
claude
```

```
1. /re-triage [path]       → enrichment (VT/MalwareBazaar) + format triage + packing check
                              malcat-reverse-engineer handles binary structure if Malcat is open

2. Open Malcat, Ctrl+M     → start MCP server
   /re-dive "<question>"   → malcat-reverse-engineer for breadth:
                              file format, sections, entropy, strings, YARA, anomalies,
                              transform/decrypt chains, carved/embedded files

3. Specific function?      → /re-dive "decompile and annotate 0x<VA>"
                              binninja-agent for depth:
                              decompilation, CFG, bulk renaming/typing, xref tracing

4. Script found?           → script-analyzer spawned automatically
                              writes to reports/ if standalone

5. Report written?         → msdn-qa runs automatically (per CLAUDE.md)
                              validates all Windows API calls, returns corrections
```

**Malcat MCP note**: start Malcat and enable the MCP server (`Ctrl+M`) before launching Claude. If Claude starts without it, use `/mcp` to deactivate and reactivate the server after Malcat is running.

## Hooks

| Hook | Event | Behavior |
|------|-------|----------|
| `guard-main.sh` | `PreToolUse` (Write, Edit) | Soft-blocks code writes to `main` once the repo has commits. Docs and configs are allowed. |
| `guard-bash.sh` | `PreToolUse` (Bash) | Soft-warns on destructive commands: `rm -rf`, `git push --force`, `git reset --hard`, `git clean -f`, `git branch -D`, `dd`, `mkfs`. |
| `uncommitted-remind.sh` | `Stop` | Advisory reminder if there are uncommitted changes at session end. |

All hooks are soft blocks (exit 1) — Claude sees the warning and must resolve it, but there's no hard system lockout.

## Backlog

Feature requests and bug reports for this config repo are tracked in `BACKLOG.md`.

| Command | Description |
|---------|-------------|
| `/backlog` or `/backlog list` | Show open items sorted by priority |
| `/backlog add <text>` | Add an item — type and priority are inferred from the text |
| `/backlog done <id>` | Mark an item closed |
| `/backlog work` | Pick the top open item, implement it in a worktree, commit, and close it |

You can also say **"add to backlog: X"** mid-session without typing the command — Claude will invoke `/backlog add` automatically.

`BACKLOG.md` is git-tracked. `/backlog work` always uses a worktree for code changes and stops at commit — no auto-push.

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
- `plugins/installed_plugins.json`, `plugins/known_marketplaces.json` (per-machine install state)

## Scope

This repo is the personal harness only — RE agents, skills, hooks, statusline. Work-specific
tooling lives in the relevant employer plugin and is installed via `/plugin`, so it stays
version-controlled by the team that owns it and never lands here.
