Append a structured entry to the research log for the current session or project.

## Behavior

Maintain a `research.md` file in the current working directory. Each invocation appends a new dated entry — never overwrites existing content.

## Entry Format

```markdown
---

## YYYY-MM-DD — <target or subject>

**Type**: <malware analysis | vuln research | reverse engineering | recon | tooling>
**Target**: <binary name, CVE, product, URL, or sample hash>

### Findings
- <key finding 1>
- <key finding 2>

### Technical Details
<relevant offsets, code snippets, decompiled logic, IOCs, crash details, etc.>

### Open Questions
- <what still needs investigation>

### Next Steps
- <concrete next actions>
```

## Steps

1. If `research.md` does not exist, create it with this header:
   ```markdown
   # Research Log
   ```

2. Infer the entry content from the current conversation context — what was analyzed, what was found, what's unclear. Ask the user to fill in anything missing before writing.

3. Append the entry to the end of `research.md`.

4. Confirm to the user that the entry was saved and where.

## Notes

- Keep findings factual and specific: offsets, function names, hashes, behaviors.
- `research.md` is informal — bullet points and fragments are fine.
- In a project repo, `research.md` lives alongside `PLAN.md` in the repo root.
- In an ad-hoc directory (no git), it's just a local scratch file.
- If there is a git repo and the file is new or has meaningful changes, offer to commit it.
