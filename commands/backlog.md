---
name: backlog
description: Manage the ~/.claude config backlog. Add features/bugs, list open items, mark done, or work the top item end-to-end. Invoke automatically when the user says "add to backlog: X", "backlog: X", "what's in my backlog", or "show backlog".
allowed-tools: Read Edit Bash
---

# Backlog

Manage `~/.claude/BACKLOG.md`. Parse `$ARGUMENTS` for a subcommand. Default to `list` if empty.

---

## Subcommands

### `add <text>`

Add a new item. Infer type and priority from the text — do not ask if the inference is unambiguous.

**Inference rules:**
- "fix", "broken", "doesn't", "fails", "not working", "wrong" → `bug`
- "add", "implement", "support", "create", "build" → `feat`
- "update", "refactor", "clean", "migrate", "remove" → `chore`
- "document", "README", "comment", "docs" → `docs`
- "urgent", "blocking", "critical" → priority `high`; default → `med`
- If type is still ambiguous, default to `feat`

**Steps:**
1. Read `~/.claude/BACKLOG.md`.
2. Find the highest existing ID in the Open table. New ID = max + 1. If no rows exist, start at 1.
3. Insert a new row at the **top** of the Open table (below the header):
   `| <id> | <priority> | <type> | open | <text> | |`
4. Confirm in one line: `Added #<id> [<priority>/<type>]: <text>`

---

### `list`

List open items sorted by priority.

**Steps:**
1. Read `~/.claude/BACKLOG.md`.
2. Parse all rows from the Open table with status `open` or `wip`.
3. Sort: high → med → low. Within same priority, preserve file order (FIFO — highest ID last added, so show ascending by ID within tier).
4. Print:
   ```
   BACKLOG (N open)
   [high] #4  bug   guard-bash.sh does not fire on agents
   [med]  #2  feat  Add PostToolUse hook for error logging
   [low]  #1  docs  Add session flow diagram
   ```
5. If empty: `BACKLOG: empty`

---

### `done <id>`

Close an item.

**Steps:**
1. Read `~/.claude/BACKLOG.md`.
2. Find the row with ID `<id>` in the Open table. Error if not found.
3. Remove the row from Open.
4. Append to Done: `| <id> | <priority> | <type> | <item text> | <YYYY-MM-DD> |`
5. Confirm: `Closed #<id>: <item text>`

---

### `wip <id>`

Mark an item in-progress.

**Steps:**
1. Find the row with ID `<id>` in the Open table.
2. Update its Status cell from `open` to `wip`.
3. Confirm: `#<id> → wip`

---

### `work`

Pick the top open item, implement it, and close it. This runs a full implementation session.

**Steps:**
1. Read `~/.claude/BACKLOG.md`. Pick the highest-priority open item (high > med > low; `bug` before `feat` at equal priority). If nothing open, say so and stop.
2. Show the selected item and confirm with the user before proceeding (one-line summary + "Proceed? [y/n]" — wait for confirmation).
3. Read the relevant files (the skill, hook, agent, or config targeted by this item) to understand current state.
4. Use `EnterWorktree` to create an isolated branch for code changes (per CLAUDE.md git workflow). Skip for doc-only changes (`*.md`, `.gitignore`, `settings.json`).
5. Implement the change.
6. Commit with the appropriate conventional prefix (`feat:`, `fix:`, `chore:`, `docs:`).
7. Mark the item done: edit BACKLOG.md to move the row from Open to Done with today's date.
8. Report the branch name (if a worktree was used) so the user can review and merge.
