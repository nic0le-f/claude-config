# RE Triage — Mode A

You are running a **cold triage** on a malware sample. Your job is Phases 0–2 only: classify the sample, check for packing, and produce a triage summary. You stop after Phase 2 — you do not deep dive.

**Sample**: $ARGUMENTS

---

## Step 0 — Resume Check and Script Inventory

Before doing anything:
1. Check `__scripts__/` in the project directory and `~/.claude/scripts/`. Note what tools already exist — use them rather than rewriting.
2. Check for an existing `phases/` directory next to the sample.

- If `phases/phase2_triage.md` exists: read it, then tell the analyst:
  > "Prior triage found (date from file). Re-run, or skip to `/re-dive` or `/re-compare`?"
  Stop here and wait for the answer.
- If no prior triage exists: proceed.

---

## Phase 0 — Intake & Classification

1. Run `file` on the sample — magic bytes, type.
2. Compute `md5sum`, `sha256sum`, `ssdeep` (if available).
3. Classify: `PE` | `ELF` | `Mach-O` | `Script` | `Document` | `APK` | `Firmware` | `Archive` | `Unknown`.
   - If `Unknown`: STOP, ask the analyst.
   - If `Archive`: extract, list contents, note each item. Recurse on each extracted file from Phase 0.
4. Spawn `enrichment-agent` to query VT and MalwareBazaar by SHA256. If APIs not configured, note it and continue.
5. Create `phases/phase0_intake.md` next to the sample. Write: filename, hashes, file type, enrichment results, any packer indicators observed.

---

## Phase 1 — Unpacking & Deobfuscation (conditional)

Run only if Phase 0 found packing/obfuscation indicators:
- PE/ELF: entropy > 7.0, fewer than 10 imports, known packer signatures (UPX, Themida, VMProtect), section names like `UPX0` / `.packed`
- Scripts: base64 blobs, `-EncodedCommand`, `chr()` / `String.fromCharCode()` arrays
- Documents: obfuscated macros, embedded OLE objects

**If no indicators**: write `phases/phase1_unpack.md` with "Not packed — skipped." Proceed.

**If indicators found**:
1. Identify packer/method. State confidence.
2. Attempt automated unpacking:
   - UPX: `upx -d` on a copy
   - Scripts: spawn `script-analyzer` to decode layers
   - Documents: extract macros with `olevba`, embedded objects with `oleobj`
3. If unpacking succeeds: note original vs unpacked. Continue with unpacked sample.
4. If unpacking fails: document what was tried.
   - STOP: present findings, ask analyst — proceed packed or try manual unpacking?
5. Write result to `phases/phase1_unpack.md`.

---

## Phase 2 — Triage

Route by sample type from Phase 0.

### Native Binary (PE / ELF / Mach-O)
Spawn `binninja-agent`:
- `get_binary_status` — arch, platform, format, analysis state
- `list_segments` — memory layout, unusual sections
- `list_imports` and `list_exports` — capability fingerprint
- `list_methods` — **summary mode**: return total function count + any functions with meaningful names (skip bare `sub_*`). Full list only if total < 50.

### Script
Spawn `script-analyzer`:
- Interpreter and version markers
- Structure: functions, classes, entry point
- All strings (URLs, IPs, paths, registry keys, commands)
- Call graph from entry point

### Document
- Extract macros (`olevba`), embedded objects (`oleobj`), streams
- Note document metadata (author, creation date, template)
- For each extracted artifact: classify and note (do not recurse fully — flag for analyst)

Write triage summary to `phases/phase2_triage.md`. Include: architecture, format, import/export count, capability fingerprint, notable functions or strings, packer/obfuscation assessment.

After writing the phase file, append confirmed facts to `FINDINGS.md` (ledger format — one fact per line, HIGH/MEDIUM confidence only). Typical triage facts: file type, architecture, stripped/not stripped, build ID, import/export count, packer status, enrichment verdict.

---

## Pause — End of Mode A

After writing `phases/phase2_triage.md`, STOP.

Present a structured summary (max 10 lines):
- File type and architecture
- Family / verdict if identifiable from triage alone (with confidence)
- Top 3–5 capability signals from imports/strings
- Packing status
- Enrichment hit (if any)

Then ask:
> "Triage complete. Next step:
> - `/re-dive <sample> "<question>"` — targeted deep dive
> - `/re-compare <sample1> <sample2> ...` — compare with other samples
> - Re-run triage: say 're-run'"

Do not continue unless the analyst responds.
