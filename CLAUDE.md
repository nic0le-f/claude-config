# Claude Config — Security Research
Concise, direct, no ceremony. Commit only when asked. Ask before destructive actions.
Precise: hex as `0x…`, offsets, register states, CWE IDs, CVSS where relevant.

## Git Workflow
- Always use worktrees for code changes in existing repos. Use `EnterWorktree` to create an isolated worktree before writing code.
- Never commit code directly to `main` — work on feature branches via worktrees.
- Never merge worktree branches locally — push the branch to remote and let the PR merge on GitHub.
- Docs and configs (*.md, .gitignore, etc.) are fine on `main`.
- Conventional prefixes: `feat:`, `fix:`, `add:`, `chore:`, `docs:`

## Token Hygiene
- Targeted reads only; file:line refs not full blocks

## Session Hygiene
- Run `/compact` when compact-remind fires — don't defer it.
- At session end, save anything non-obvious to memory: decisions, preferences, project context that won't be obvious from reading the code.
