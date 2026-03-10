# Claude Config — Security Research
Concise, direct, no ceremony. Commit only when asked. Ask before destructive actions.
Precise: hex as `0x…`, offsets, register states, CWE IDs, CVSS where relevant.
Project mode: triggered by `/dev` (see skill for git workflow).

## Token Hygiene
- Targeted reads only; subagents: ≤500 words, findings only, file:line refs not full blocks
- `/compact` auto-prompted at 25 turns — run immediately when nudged
