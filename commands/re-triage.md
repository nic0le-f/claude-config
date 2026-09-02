# RE Triage — Post-Gold

Capability fingerprint and family verdict from a validated `gold.bndb`.

**Case**: $ARGUMENTS

---

Spawn the `re-triage` agent against the case directory above.

If `$ARGUMENTS` names a sample rather than a case directory, resolve it: look under `~/re-cases/` (or `$BNGOLD_CASES_DIR`) for a directory matching `<name>_<sha256[:12]>`.

**Precondition**: the case must have `gold/gold.bndb`. If it does not, the pipeline has not run or has not reached checkpoint 7 — tell the analyst to run the `binaryninja-gold-re` skill first, and stop. Do not fall back to analysing the raw sample.

The agent writes `CASE_DIR/reports/triage.md` and returns a summary. It is read-only: it never renames, retypes, or writes claims.
