---
name: handoff
description: Produce a structured session handoff so a new agent can resume without context loss — covers discussion summary, files changed, open issues, goals, and next steps.
allowed-tools: Read Bash Glob Grep TaskList
---

# Session Handoff

Produce a handoff document from the current session so a new agent can pick up with zero context loss.

## Steps

### 1 — Gather ground truth

Run these in parallel:

```sh
git status --short
git diff --stat HEAD
git log --oneline -10
```

Also check for open tasks:
- Call `TaskList` to surface any tracked tasks and their status.
- Check for plan files: `ls ~/.claude/plans/ 2>/dev/null` and read any that are active.

Pick the output path: write into the directory the user launched Claude Code from (the current working directory):

```sh
handoff_path="$(pwd)/handoff-$(date +%Y-%m-%d-%H%M).md"
```

### 2 — Synthesize from conversation

Review the full conversation context. Extract:

- **What was discussed** — the core topic(s), decisions made, and rationale. One sentence per decision.
- **Files created or modified** — confirm against `git status` / `git diff`. For each: path + one-line description of what changed and why.
- **Issues encountered** — errors hit, things that didn't work, known limitations, deferred problems.
- **Current goals** — what the user is trying to achieve overall (not just this session).
- **Next steps** — concrete actions remaining. Be specific: file to edit, command to run, decision to make.

Do not hallucinate. If something is uncertain, say so.

### 3 — Output

Write the handoff document to `$handoff_path` (resolved in step 1), then also print it directly in the conversation. After writing, print the saved path so the next agent can find it.

Use this structure:

```
# Session Handoff — <date>

## Summary
<2–4 sentences: what the session was about and what was accomplished>

## Files Changed
| File | Change |
|------|--------|
| path/to/file | what changed and why |

## Decisions Made
- <decision> — <rationale>

## Open Issues
- <issue> — <context or workaround if any>

## Goals
<what the user is working toward, in their own terms>

## Next Steps
1. <specific action>
2. <specific action>
...

## Context for New Agent
<anything non-obvious a new agent needs to know to not repeat mistakes or redo work — repo layout quirks, constraints, preferred approach, what was already tried>
```

Keep it tight — a new agent should be able to read it in under 60 seconds and know exactly where to start.
