Expand the current project context into a persistent PLAN.md file committed to the repo.

## When This Is Invoked
The user has run /plan or explicitly asked for a detailed plan. There may already be a bullet plan in conversation — expand it. If there is no prior context, generate both bullets and a full plan draft, then ask the user to confirm before committing.

## Step 1: Draft PLAN.md
Write a PLAN.md with this exact structure:

```markdown
# <Project Name>

## Goal
One paragraph: what this project does and why it exists.

## Approach
- Key technical decision or method 1
- Key technical decision or method 2
- ...

## Tasks
- [ ] Task A: brief description
- [ ] Task B: brief description
- [ ] Task C: brief description

## Notes
<!-- Discoveries, gotchas, and decisions made during implementation -->
```

## Step 2: Place and Commit
PLAN.md lives in the **repo root on main**, not inside a worktree:

```bash
# Write to repo root
<repo-root>/PLAN.md

# Commit to main directly (docs are allowed on main)
git -C <repo-root> add PLAN.md
git -C <repo-root> commit -m "docs: add PLAN.md"
```

## Step 3: Keep It Updated
As work progresses during this and future sessions:
- Check off completed tasks: `- [x] Task A`
- Add discoveries or blockers to the Notes section
- Re-commit after meaningful changes: `git -C <repo-root> commit -am "docs: update PLAN.md"`

## On Session Resume
When starting a new session in an existing project repo:
1. Read PLAN.md to restore context
2. Identify which tasks are done (checked) and which are next
3. Confirm the active worktree or create one if needed
4. Resume from where work left off
