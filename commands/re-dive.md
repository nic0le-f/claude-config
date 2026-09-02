# RE Deep Dive — Post-Gold

Answer one targeted question against a validated `gold.bndb`.

**Case and question**: $ARGUMENTS

---

Spawn the `re-dive` agent with the case directory and the question.

Expected form: `/re-dive <case_dir_or_sample> "<question>"`. If `$ARGUMENTS` names a sample rather than a case directory, resolve it under `~/re-cases/` (or `$BNGOLD_CASES_DIR`). If no question was given, ask for one before spawning — a dive without a question is a triage.

**Precondition**: the case must have `gold/gold.bndb`. If it does not, tell the analyst to run the `binaryninja-gold-re` skill first, and stop.

The agent writes `CASE_DIR/reports/dive_<slug>.md` and returns the answer. It is read-only: findings that deserve a name or type come back as recommendations, and the analyst re-enters the pipeline to propose them as claims.
