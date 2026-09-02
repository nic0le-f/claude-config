# Claude Config — Security Research
Concise, direct, no ceremony. Commit only when asked. Ask before destructive actions.
Precise: hex as `0x…`, offsets, register states, CWE IDs, CVSS where relevant.

## Git Workflow
- Always use worktrees for code changes in existing repos. Use `EnterWorktree` to create an isolated worktree before writing code.
- Never commit code directly to `main` — work on feature branches via worktrees.
- Docs and configs (*.md, .gitignore, etc.) are fine on `main`.
- Conventional prefixes: `feat:`, `fix:`, `add:`, `chore:`, `docs:`

## RE Analysis
- Reports must open with an Executive Summary, then a Table of Contents, before any other sections.
- Every function or script analysis must include a call graph. For long functions, break into labeled phases with address ranges (e.g., "Phase 1 — Entry (`0x17F000`–`0x17F080`)").
- All addresses in VA hex format (`0x17F32A60`), never EA decimal.
- Native binaries go through the `binaryninja-gold-re` pipeline via `re-agent`. Strictly headless — never use `binary_ninja_mcp` write tools.
- Only accepted claims reach `gold.bndb`. Propose claims with local code evidence; the blind `gold-validator` decides. Malcat, YARA, capa, VT, MalwareBazaar and OTX are leads and never back a claim.
- Use `malcat-reverse-engineer` for headless Malcat triage. Scripts, documents, archives, APKs and firmware go to `script-analyzer` — that lane produces no BNDB and no claims.
- `msdn-qa` runs inside validation on any claim citing a Win32 API or constant; a misread signature is a rejection. Also run it standalone on any finished report containing Windows API calls.
- After `gold.bndb` exists: `/re-triage`, `/re-dive`, `/re-compare`. All three are read-only.
- When `msdn-qa` flags a constant name: verify the hex value in the binary first — the binary is source of truth; fix the name to match the hex, not the other way around.

## Token Hygiene
- Targeted reads only; file:line refs not full blocks

## Session Hygiene
- Run `/compact` when compact-remind fires — don't defer it.
- At session end, save anything non-obvious to memory: decisions, preferences, project context that won't be obvious from reading the code.

## Backlog
- When the user says "add to backlog: X" or "backlog: X", immediately invoke `/backlog add X` — do not ask for confirmation.
- When the user says "what's in my backlog" or "show backlog", invoke `/backlog list`.
