# RE Deep Dive — Mode B

You are running a **targeted deep dive** on a specific question about a sample. You do not re-run triage. You read existing findings and go straight to answering the question.

**Arguments**: $ARGUMENTS
- First token: sample path (or hash prefix if sample is already in context)
- Remainder: the question or hypothesis to investigate

---

## Step 0 — Load Prior Context and Script Inventory

Before any analysis, check `__scripts__/` in the project directory and `~/.claude/scripts/`. Note existing tools — use them rather than rewriting.

Then:

1. Find `phases/` directory next to the sample.
2. Read all existing `phases/*.md` files. Build a mental model of what is already known.
3. Read `FINDINGS.md` if it exists in the project directory.
4. Read the project memory for any cross-session context on this sample or family.

If no `phases/` directory exists:
> "No prior triage found for this sample. Run `/re-triage <sample>` first, or confirm you want to dive cold."
Stop and wait for the analyst.

---

## Step 1 — Scope the Question

Restate the question in one sentence. Identify:
- Which binary/function/data structure is the focus
- What type of analysis is needed (decompilation, xrefs, string decoding, struct recovery, etc.)
- What a satisfying answer looks like (e.g., "decoded C2 strings", "call graph of the crypto routine", "confirmed hook list")

---

## Step 2 — Targeted Analysis

Run only what the question requires. Do not run a full pipeline.

**For binary questions** — spawn `binninja-agent` with a focused task:
- Specific function(s) to decompile
- Xref traces to/from a specific address
- Rename/retype/comment targets
- Return findings, do not write to disk

**For script questions** — spawn `script-analyzer` with a focused task.

**For enrichment questions** — spawn `enrichment-agent`.

**For API correctness** — spawn `msdn-qa`.

Apply `/malware-analyst` naming and confidence conventions to any annotations made.

Confidence gating — CRITICAL:
- HIGH: apply renames/retypes freely
- MEDIUM: use `_likely` suffix, add comment
- LOW: add `[TODO]` comment only, STOP and present hypothesis to analyst before making changes

---

## Step 3 — Write Findings

Write a focused findings file: `phases/phase4_<slug>.md` where `<slug>` is a 2–4 word description of the question (e.g., `phase4_string_decoder.md`, `phase4_hook_list.md`).

Structure:
```
# Deep Dive: <question restated>
Date: <YYYY-MM-DD>
Sample: <hash>

## Finding
<direct answer to the question>

## Evidence
<addresses, decompiled snippets, xref chains — keep targeted>

## Confidence
HIGH / MEDIUM / LOW — reason

## Annotations Applied
<list of renames/retypes/comments made in Binja, or "none">

## Open Questions
<anything LOW confidence or unresolved>
```

Append confirmed facts to `FINDINGS.md` (ledger format — HIGH/MEDIUM confidence only, one line per fact). If a script was created, add a `Scripts:` line to the sample's section. Detail and evidence stay in the phase file.

---

## Step 4 — Present to Analyst

Summarize the answer in plain language (no more than 10 lines). State confidence. List any open questions or LOW confidence items that need analyst input.

Do not auto-continue to other phases. Wait for the analyst's next instruction.
