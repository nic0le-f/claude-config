# claude-config

Personal Claude Code configuration for security research. Optimized for low overhead on day-to-day analysis work, with structured git discipline for tool development.

## Operating Modes

### Research Mode (default)
Direct execution, no planning overhead. Covers binary analysis, malware triage, vulnerability hunting, quick scripts, and PoCs. Git is optional and informal.

### Project Mode (`/dev`)
Activated by `/dev` or when building something reusable. Claude presents a bullet plan, waits for confirmation, then scaffolds a git repo with a feature worktree. All code work happens in `.worktrees/<feature-name>/` — never directly on `main`.

## Skills

| Command | Description |
|---------|-------------|
| `/dev` | Initialize a git-structured project with worktree |
| `/plan` | Expand in-conversation bullets to a persistent `PLAN.md` |
| `/research` | Append a structured findings entry to `research.md` |
| `/poc` | Generate a proof of concept |
| `/find-vulns` | Vulnerability hunting workflow |
| `/analyze-binary` | Binary analysis workflow |
| `/malware-analyst` | Malware reverse engineering session |
| `/cvss` | Calculate CVSS score |
| `/write-advisory` | Draft a vulnerability advisory |
| `/disclose` | Prepare responsible disclosure |

## Hooks

| Hook | Event | Behavior |
|------|-------|----------|
| `guard-main.sh` | `PreToolUse` (Write, Edit) | Soft-blocks code writes to `main` once the repo has commits. Docs and configs are allowed. |
| `guard-bash.sh` | `PreToolUse` (Bash) | Soft-warns on destructive commands: `rm -rf`, `git push --force`, `git reset --hard`, `git clean -f`, `git branch -D`, `dd`, `mkfs`. |
| `uncommitted-remind.sh` | `Stop` | Advisory reminder if there are uncommitted changes at session end. |

All hooks are soft blocks (exit 1) — Claude sees the warning and must resolve it, but there's no hard system lockout.

## Git Workflow

```
main
├── PLAN.md          (if /plan was used)
├── research.md      (if /research was used)
└── .worktrees/      (gitignored)
    └── <feature>/   (all active code work)
```

- `main` is protected from code writes after the initial scaffold
- Feature work lives in `.worktrees/<name>/` on branch `<name>`
- Commits use conventional prefixes: `feat:`, `fix:`, `add:`, `chore:`, `docs:`
- Merge to `main` when a feature is complete, then remove the worktree
- `git push` always requires manual approval

## What's Gitignored

Runtime and session state that stays local:
- `history.jsonl`, `projects/`, `session-env/`, `shell-snapshots/`
- `cache/`, `debug/`, `backups/`, `todos/`, `plans/`
- `settings.local.json` (local permission overrides)
- `plugins/marketplaces/` (has its own git history)
