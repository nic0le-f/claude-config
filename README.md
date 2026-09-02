# claude-config

Personal Claude Code configuration for security research. Optimized for low overhead on day-to-day analysis work, with structured git discipline for tool development.

## Agents

Defined in `agents/`. Visible via `/agents` dialog.

| Agent | Model | Description |
|-------|-------|-------------|
| `re-agent` | opus | Orchestrates the gold RE pipeline end to end — intake, unpack, case init, fact export, claim emission, blind validation, apply, report. `acceptEdits`, 150 turn cap. |
| `gold-validator` | opus | Blind adversarial validator. Attacks each proposed claim from clean evidence and writes accepted/rejected/needs_human verdicts. Never sees analyst notes. |
| `malcat-reverse-engineer` | opus | Headless Malcat static triage — format, sections, entropy, signature hits, strings, carved files. Lead generator only. |
| `script-analyzer` | opus | Owns the non-binary lane — scripts, documents (olevba/oleobj), archives with recursion, APK and firmware. Produces no BNDB and no claims. |
| `enrichment-agent` | sonnet | Threat intel enrichment — VirusTotal, MalwareBazaar, Shodan. Leads only. |
| `msdn-qa` | sonnet | Win32 API validation. Mode A rules on claims inside the validator; Mode B audits a finished report. |
| `re-triage` | opus | Post-gold capability fingerprint and family verdict. Read-only. |
| `re-dive` | opus | Post-gold targeted deep dive on one question. Read-only. |
| `re-compare` | opus | Post-gold comparison across two or more validated cases. Read-only. |

`re-agent` is the entry point for native binaries. The three `re-*` agents run afterwards, against a validated `gold.bndb`.

## The Gate

Only accepted claims reach `gold.bndb`. Every proposed edit — name, comment, type, data label, source-file assignment — is written as a JSONL claim with its evidence, ruled on by a blind validator working from clean evidence, and applied only if accepted. Analysis is strictly headless: `bnpython3` scripts against `.bndb` files, never the Binary Ninja MCP write tools.

Malcat, YARA, capa, VirusTotal, MalwareBazaar and OTX are leads. They prioritise what you look at; they never back a claim.

## Skills

| Command | Description |
|---------|-------------|
| `binaryninja-gold-re` | The pipeline. Case workspace, claims, blind validation, gold BNDB, report. Invoked by `re-agent`. |
| `/re-triage` | Post-gold capability fingerprint and family verdict. Pass a case dir or sample name. |
| `/re-dive` | Post-gold deep dive. `/re-dive <case> "<question>"`. |
| `/re-compare` | Post-gold comparison across validated cases. |
| `/malware-analyst` | Analyst conventions — naming, evidence policy, YARA standards, report format. |
| `/audit-codebase` | Security audit of a source folder. |
| `/disclose` | Prepare responsible disclosure. |

Planning uses native plan mode. Code work uses native worktrees (`EnterWorktree`).

## Typical Session Flow

```
1. Native binary?      → re-agent drives binaryninja-gold-re:
                           0 intake      hashes, classify, VT/MalwareBazaar
                           1 unpack      entropy>7.0, <10 imports, UPX/Themida/VMP
                                         → bngold_case.py add-unpacked records lineage
                           2 malcat      headless triage → CASE_DIR/triage/ (leads)
                           3 init        bngold_case.py init → CASE_DIR/
                           4 facts       bn_export_facts.py → evidence/bn_facts.json
                                         ELF/Go: elf_go_context.py, elf_go_type_layout.py
                           5 analyse     emit claims/claims.jsonl
                           6 validate    gold-validator (blind) + msdn-qa → verdicts.jsonl
                           7 apply       bn_apply_claims.py → gold/gold.bndb
                           8 report      bngold_report.py → reports/final.md

2. Script / doc /      → script-analyzer owns the lane end to end.
   archive / APK?        No case dir, no claims, no BNDB.

3. Gold BNDB exists?   → /re-triage   capability fingerprint + family verdict
                         /re-dive     one targeted question
                         /re-compare  cross-sample analysis
```

Cases live in `~/re-cases/` by default; override with `BNGOLD_CASES_DIR` or `--cases-dir`.

**Setup**: the pipeline shells out to Binary Ninja's bundled Python. `settings.json` is untracked, so add the allowlist entry locally:

```json
{ "permissions": { "allow": ["Bash(/home/ubi/Applications/BinaryNinja/binaryninja/bnpython3:*)"] } }
```

There is no `FINDINGS.md` and no `phases/` directory. Accepted claims in `claims/verdicts.jsonl` are the confirmed-facts ledger, with evidence attached per fact; `reports/final.md` is the narrative.

## Hooks

| Hook | Event | Behavior |
|------|-------|----------|
| `guard-main.sh` | `PreToolUse` (Write, Edit) | Soft-blocks code writes to `main` once the repo has commits. Docs and configs are allowed. |
| `guard-bash.sh` | `PreToolUse` (Bash) | Soft-warns on destructive commands: `rm -rf`, `git push --force`, `git reset --hard`, `git clean -f`, `git branch -D`, `dd`, `mkfs`. |
| `uncommitted-remind.sh` | `Stop` | Advisory reminder if there are uncommitted changes at session end. |

Git hooks live in `git-hooks/`, wired in globally via `core.hooksPath`:

| Hook | Behavior |
|------|----------|
| `commit-msg` | Strips Claude/Anthropic attribution trailers from every commit message. |
| `pre-commit` | Hard-blocks commits staging runtime/secret paths, secret-shaped strings, employer material, or a work email as author. **Scoped to `~/.claude` only** — inert in every other repo, since a global `core.hooksPath` fires everywhere. Override with `--no-verify`. |

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
