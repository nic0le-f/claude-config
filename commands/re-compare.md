# RE Comparative Analysis — Mode C

You are running a **multi-sample comparative analysis**. Your job is to identify relationships between samples: shared code, infrastructure overlap, lineage, evolution over time.

**Samples**: $ARGUMENTS
(space-separated sample paths or hash prefixes)

---

## Step 0 — Load Prior Context and Script Inventory

Check `__scripts__/` and `~/.claude/scripts/` for existing tools before creating anything new.

For each sample in the list:
1. Find its `phases/` directory. Read all `phases/*.md` files.
2. If no `phases/` directory exists for a sample, note it:
   > "No prior triage for <hash>. Run `/re-triage <sample>` first, or skip this sample."
   Continue with the samples that do have prior triage. Do not run triage inline.
3. Read `FINDINGS.md` in the project directory.
4. Read project memory for family/campaign links from prior sessions.

Build a per-sample summary table before starting comparison:
| Sample | Type | Arch | Exports | Imports | Family (if known) | Triage date |
|---|---|---|---|---|---|---|

---

## Step 1 — Comparison Axes

Run the following comparisons. Skip any axis where fewer than 2 samples have the relevant data.

### Code similarity
- Shared exported function names (exact and fuzzy)
- Shared internal function patterns (same capability categories from triage)
- If samples are open in Binary Ninja: spawn `binninja-agent` to check function-level similarity on specific functions of interest (do not run a full diff — pick 3–5 key functions)

### Infrastructure overlap
- Shared C2 domains / IPs / ports
- Shared paths, mutex names, service names, scheduled task names
- Shared user-agent strings or protocol fingerprints

### Config format
- Same config structure with different values (evolution indicator)
- Same encryption/encoding scheme for config

### Build artifacts
- Shared compiler flags or toolchain markers
- Build timestamps (if available and not stripped)
- Shared debug strings or PDB paths

### Behavioral delta
- Capabilities present in some samples but not others
- Hook count changes (for rootkits)
- Export additions/removals across versions

---

## Step 2 — Lineage Assessment

Based on the comparison, group samples into lineages:
- **Same lineage**: strong code reuse + shared config format + overlapping infrastructure
- **Related lineage**: partial code reuse or config evolution with infrastructure divergence
- **Distinct**: minimal overlap — may be different families or false positive YARA match

State confidence (HIGH / MEDIUM / LOW) and evidence for each grouping.

If chronological ordering is possible (VT first-seen, build timestamps), show evolution timeline.

---

## Step 3 — Write Comparison Report

Write to `phases/compare_<YYYYMMDD>.md` in the project directory (not per-sample):

```
# Comparative Analysis
Date: <YYYY-MM-DD>
Samples: <list>

## Sample Summary Table
<table from Step 0>

## Lineage Assessment
<groupings with confidence and evidence>

## Shared Artifacts
<code, infrastructure, config — concrete evidence only>

## Evolution Timeline
<chronological delta if available>

## Open Questions
<LOW confidence items, samples missing triage, suggested next dives>
```

Append confirmed comparative facts to `FINDINGS.md` under `## Comparative` (ledger format — one line per confirmed cross-sample finding, HIGH/MEDIUM confidence only).

---

## Step 4 — Present to Analyst

Summarize findings in plain language (max 15 lines):
- How many lineages found
- Strongest evidence for each grouping
- Any samples that didn't fit
- Suggested next steps (specific `/re-dive` questions that would resolve open items)

Wait for analyst instruction.
