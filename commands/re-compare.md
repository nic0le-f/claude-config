# RE Comparison — Post-Gold

Diff two or more validated `gold.bndb` databases for shared code, shared infrastructure, and version drift.

**Cases**: $ARGUMENTS

---

Spawn the `re-compare` agent with every case directory listed above.

Expected form: `/re-compare <case1> <case2> [case3 ...]`. Resolve any sample names to case directories under `~/re-cases/` (or `$BNGOLD_CASES_DIR`).

**Precondition**: every case must have `gold/gold.bndb`. Report which cases are missing it and stop — comparing a validated case against an uncurated one measures analyst effort, not sample similarity. Run the `binaryninja-gold-re` skill on the missing samples first.

The agent writes `reports/compare_<YYYYMMDD>.md` in the first case directory and returns a summary. It is read-only across every case.
