---
name: binaryninja-gold-re
description: Use when asked to reverse engineer a PE, ELF, or Mach-O binary — malware sample, implant, loader, unpacked payload, or native executable — and produce a validated gold-standard BNDB. Creates a case workspace, runs static-only headless Binary Ninja analysis, emits structured claims for function names/types/comments/source-tree recovery, gates every claim through a blind validator subagent, and applies only accepted claims to gold.bndb. Trigger on "analyze this binary", "make a gold BNDB", "recover types/functions", "reverse this PE/ELF". Never execute the sample. For scripts, documents, archives, APKs and firmware use the script-analyzer agent instead — that lane produces no BNDB.
---

# Binary Ninja Gold RE

## Operating Rule

Produce a gold BNDB by evidence-gated edits, not by direct speculation. You may propose claims; only **accepted** claims reach `gold.bndb`.

Do not execute the sample. Static Binary Ninja analysis is the source of truth.

**Strictly headless.** All Binary Ninja work goes through `bnpython3` scripts against `.bndb` files on disk. Do not use `binary_ninja_mcp` write tools (`rename_function`, `rename_data`, `retype_variable`, `define_types`, `set_comment`, `set_function_prototype`, …) at any point in this pipeline. Edits are applied exclusively by `bn_apply_claims.py`, and only to accepted claims.

`BNPY=/home/ubi/Applications/BinaryNinja/binaryninja/bnpython3`
`SKILL=~/.claude/skills/binaryninja-gold-re/scripts`

---

## Checkpoints

Run in order. Each writes into `CASE_DIR/` and is resumable — on re-entry, inspect what already exists and skip completed steps.

### 0 — Intake

1. `file`, `md5sum`, `sha256sum`, `ssdeep` on the sample.
2. Classify: `PE` | `ELF` | `Mach-O` | `Script` | `Document` | `APK` | `Firmware` | `Archive` | `Unknown`.
   - `Unknown` → STOP, ask the analyst.
   - `Script` / `Document` / `APK` / `Firmware` → hand off to the `script-analyzer` agent. That lane produces no BNDB and no claims. Stop here.
   - `Archive` → extract, list contents, re-enter checkpoint 0 per extracted file.
3. Spawn `enrichment-agent` for VT / MalwareBazaar by SHA-256. If APIs are not configured, note it and continue.
4. Write intake output to `triage/intake.md` once the case exists (checkpoint 3), or hold it until then.

### 1 — Unpack (conditional)

Run only if checkpoint 0 found indicators:
- entropy > 7.0, fewer than 10 imports, known packer signatures (UPX, Themida, VMProtect), section names like `UPX0` / `.packed`, tiny `.text` with a large high-entropy overlay.

**No indicators**: note "not packed" and continue.

**Indicators found**:
1. Identify the packer and state confidence.
2. Attempt automated unpacking on a copy — UPX: `upx -d`.
3. On success, register the payload so the report cannot misattribute it:
   ```bash
   python3 $SKILL/bngold_case.py add-unpacked CASE_DIR /path/to/unpacked.bin \
     --method upx --tool "upx 4.2.4" --notes "single layer"
   ```
   This writes `sample/unpacked_NN.bin`, appends a lineage entry with parent hash / method / tool, and repoints `analysis_target` at the payload. Every later checkpoint operates on the payload.
4. On failure, document what was tried, then STOP and ask: proceed packed, or attempt manual unpacking?

Registration is mandatory when unpacking succeeds. `gold.bndb` describes the payload, not the file you were handed, and the report says so only if lineage is recorded.

### 2 — Malcat triage (optional lead generator)

Spawn `malcat-reverse-engineer` (headless) against the analysis target. Save output to `triage/`.

Malcat, YARA and capa output is **heuristic leads only**. It may prioritise what you look at first. It may never be the sole evidence for a claim.

### 3 — Init case

```bash
python3 $SKILL/bngold_case.py init /path/to/sample --cases-dir ~/re-cases
```

Prints `CASE_DIR`. Override the cases root with `--cases-dir` or `BNGOLD_CASES_DIR`.

### 4 — Export facts

```bash
$BNPY $SKILL/bn_export_facts.py CASE_DIR
```

Creates `binja/base.bndb`, `work/analyst.bndb`, `work/validator.bndb` and normalises `evidence/bn_facts.json`.

For ELF, especially Go:
```bash
python3 $SKILL/elf_go_context.py CASE_DIR
python3 $SKILL/elf_go_type_layout.py CASE_DIR   # Go + DWARF only
```
Writes `evidence/file_info.txt`, `evidence/app_symbols.txt`, `evidence/go_context.json`, `evidence/go_type_layouts.{json,md}`, and `recovered_tree/source_tree.md` when DWARF line paths exist.

### 5 — Analyse and emit claims

Work from `evidence/bn_facts.json` and `work/analyst.bndb`. Emit every proposed edit as a JSONL row in `claims/claims.jsonl`. Never write to `gold/gold.bndb` directly.

`bn_facts.json` carries strings, functions, the call graph, sections and symbols. Per-function detail is queried on demand — one BNDB load answers a batch, which matters on a statically linked Go database:

```bash
$BNPY $SKILL/bn_lane_query.py CASE_DIR/work/analyst.bndb \
  --decompile 0x4658c0 --vars 0x4658c0 --xrefs 0x7967a0
```

For a function you are curating, claim the work in this order — each step makes the next one legible:
1. `function_name` — what the function is.
2. `type_definition` — the structs it operates on, with offset/size evidence.
3. `function_prototype` — the signature, naming and typing every parameter at once. Highest leverage: it propagates types to every call site.
4. `variable_type` then `variable_name` for the locals that still read as `rax_1` / `var_70`.

Do not rename every variable in a large function. Curate the ones carrying config, buffers, handles, sizes and loop state — the ones a reader needs to follow the logic.

### 6 — Validate (blind)

```bash
python3 $SKILL/bngold_case.py validate-claims CASE_DIR
```
Shape check first — it rejects malformed claims and any claim whose evidence is *entirely* lead-only sources (Malcat, YARA, capa, VirusTotal, MalwareBazaar, OTX, public reports).

Then spawn the `gold-validator` subagent for the adversarial pass. It reads only `evidence/bn_facts.json`, `claims/claims.jsonl` and `work/validator.bndb` — never your notes, never `work/analyst.bndb`. It writes `claims/verdicts.jsonl`.

Any claim citing a Windows API, flag, or constant is routed to `msdn-qa` inside this step. A misread signature or wrong constant is a rejection, not a report footnote. When `msdn-qa` disputes a constant *name*, verify the hex in the binary first — the binary is source of truth; fix the name to match the hex, not the reverse.

Re-run `validate-claims` after verdicts land to confirm counts.

### 7 — Apply

```bash
$BNPY $SKILL/bn_apply_claims.py CASE_DIR
```
Accepted claims only, applied in a fixed order that the phases depend on:

1. `type_definition` — one dependency-sorted batch, so later phases can reference the types.
2. `function_prototype` — before any variable work, because a new signature replaces the function's parameter variables.
3. variable targets are resolved to concrete variables — before the first rename, since a rename invalidates lookup by the old name.
4. `variable_type`, then `variable_name`.
5. `data_type`, `data_name`, `function_name`, comments.

Every write is read back and compared. If an edit did not take effect the run fails rather than reporting it applied — assigning `Function.type` directly, for instance, is a silent no-op in this API version, so prototypes go through `set_user_type` plus reanalysis. `reports/applied_claims.json` records what landed per phase.

### 8 — Report

```bash
python3 $SKILL/bngold_report.py CASE_DIR
```
Writes `reports/final.md` — Executive Summary, then Table of Contents, then artifacts, lineage, observed facts, claim status, accepted highlights, source tree, detection anchors, unresolved areas, checks run.

Author YARA rules — following `/malware-analyst` standards — into `reports/rules.yar`, sourced **only** from the Detection Anchors section. Never build a signature from a rejected, needs-human, or unreviewed claim.

---

## Claim Format

```json
{"claim_id":"fn_401000_name","kind":"function_name","target":"0x401000","proposed_value":"mw_config_parse_c2_list","confidence":"high","evidence":["xref to string 'c2list='","calls strtok/inet_addr","writes into config struct at +0x18"],"status":"proposed"}
```

| Kind | Target | `proposed_value` |
|---|---|---|
| `function_name` | `0xVA` | `mw_`-prefixed snake_case name |
| `function_comment` | `0xVA` | comment text |
| `data_name` | `0xVA` | `mw_`-prefixed snake_case name |
| `source_file` | `0xVA` | recovered source path |
| `type_definition` | `0xVA` | C struct/union/enum/typedef text |
| `function_prototype` | `0xVA` | full C signature — `int64_t f(struct mw_cfg* cfg, uint64_t len)` |
| `variable_type` | `0xVA#current_var_name` | C type text — `struct mw_cfg*` |
| `variable_name` | `0xVA#current_var_name` | `mw_`-prefixed snake_case name |
| `data_type` | `0xVA` | C type text |

`target` is always VA hex (`0x17F32A60`), never EA decimal. For a function claim it must be the **function start**, not an address inside the body.

`type_definition` only registers a type in the database. A recovered struct appears in decompiled output only when something is retyped to it — that is what `function_prototype`, `variable_type` and `data_type` are for. A case that defines types and applies none has not recovered them; the report says so explicitly.

### Variable targets

Variables are addressed by their **current** name in the analyst lane. Get the exact target string — and the current type — from:

```bash
$BNPY $SKILL/bn_lane_query.py CASE_DIR/work/analyst.bndb --vars 0x4658c0
```

Each row carries a ready-to-use `target`, the current `type`, `width`, `source_type` and whether it is a parameter. Do not hand-assemble a target.

Two rules the shape check enforces, because both silently corrupted `gold.bndb` before:
- A `function_prototype` claim replaces the function's parameter variables. Never pair it with a `variable_name` / `variable_type` claim on the same function — name and type the parameters inside the prototype instead.
- Two `type_definition` claims may not define the same type name. Merge them into one claim; otherwise the last applied silently wins.

## Naming

`snake_case`, every renamed symbol prefixed `mw_`. Categories:

| Category | Pattern | Example |
|---|---|---|
| C2 | `mw_c2_<action>` | `mw_c2_send_beacon` |
| Persistence | `mw_persist_<method>` | `mw_persist_reg_run_key` |
| Evasion | `mw_evasion_<technique>` | `mw_evasion_check_debugger` |
| Credentials | `mw_cred_<target>` | `mw_cred_dump_lsass` |
| Crypto | `mw_crypto_<algo>` | `mw_crypto_xor_decrypt` |
| Collection | `mw_collect_<what>` | `mw_collect_screenshot` |
| Discovery | `mw_enum_<what>` | `mw_enum_processes` |
| Injection | `mw_inject_<method>` | `mw_inject_process_hollow` |
| Config | `mw_config_<action>` | `mw_config_parse_c2_list` |
| Utility | `mw_util_<purpose>` | `mw_util_resolve_api` |
| Strings | `mw_str_<action>` | `mw_str_deobfuscate` |
| Init | `mw_init_<what>` | `mw_init_comms` |

Variables: `mw_buf_<purpose>`, `mw_h_<target>`, `mw_<what>_size` — emitted as `variable_name` claims. Data: `mw_encrypted_strings_blob`, `mw_c2_config_block`.

The `mw_` prefix, snake_case and the no-`_likely` rule are enforced by `validate-claims` for `function_name`, `data_name` and `variable_name`. A convention slip is a shape error, not a validator judgement call.

### Recovered upstream names

`mw_` marks actor-authored code. When you recover a function's **genuine** upstream name from the binary's own metadata — a Go `pclntab` entry, a `FuncID`, DWARF, a symbol table — prefixing it would falsely attribute stock runtime or library code to the actor. Declare it instead:

```json
{"claim_id":"fn_437680_name","kind":"function_name","target":"0x437680","proposed_value":"runtime_main","name_source":"recovered","confidence":"high","evidence":["pclntab records func_id 18, which is FuncID_runtime_main in the Go 1.23/1.24 abi.FuncID enum","pclntab attributes 0x437680 to proc.go"],"status":"proposed"}
```

`name_source` is `authored` (the default — requires the `mw_` prefix) or `recovered` (must **not** carry the prefix, and the evidence must cite the symbol source). This is the one sanctioned way to name a function without `mw_`; do not use it to smuggle a guessed name past the prefix rule.

**No `_likely` suffix.** Uncertainty lives in `claim.status` and the validator's `needs_human` verdict, not in the symbol name. A name is either supported by evidence and applied, or it is not applied.

Avoid vague names — `handle_data`, `process_buffer`, `do_work` — and never copy a name from a heuristic hit without code evidence.

## Evidence Policy

A claim needs local code evidence: strings, imports, constants, xrefs, call-graph position, data flow, side effects.

These prioritise work but never back a claim on their own:
- Malcat, YARA, capa output
- VirusTotal, MalwareBazaar, OTX
- Public report text
- Analyst intuition

`type_definition` claims need offset/size/access evidence, allocation size, ABI/API signatures, or consistent data flow. `source_file` claims need clusters — call relationships, shared state or types, common API families, protocol boundaries.

Type-application claims need evidence tying the type to *that* storage location:
- `variable_type` — the accesses through the variable: offsets read or written, the width of each access, the allocation size it came from, or the signature of the callee it is passed to.
- `function_prototype` — per-parameter evidence. Register/stack position plus how each argument is used at every call site. A parameter typed on one call site alone is a `needs_human`, not an accept.
- `data_type` — the access pattern at that address, its size, and the routines that read it.

"It is passed to something that looks like a parser" types nothing. Cite the offsets.

## Workspace

```text
CASE_DIR/
  case.json                     sample identity, lineage, analysis_target
  sample/original.bin
  sample/unpacked_NN.bin        when unpacking occurred
  binja/base.bndb
  work/analyst.bndb
  work/validator.bndb
  gold/gold.bndb
  evidence/bn_facts.json
  evidence/go_context.json      ELF/Go
  evidence/go_type_layouts.json ELF/Go + DWARF
  claims/claims.jsonl
  claims/verdicts.jsonl
  claims/validation_summary.json
  reports/final.md
  reports/rules.yar
  recovered_tree/
  triage/
```

Do not use unrelated project directories as fixtures or prior art unless the user names them.

## PE and ELF Coverage

**PE**: imports/exports, resources, TLS callbacks, service/registry/network/crypto/process APIs, packer artifacts, overlay, suspicious section permissions.

**ELF**: dynamic symbols, PLT/GOT usage, init/fini arrays, interpreter, RPATH/RUNPATH, libc/OpenSSL/curl/pthread/syscall usage, embedded paths, stripped symbols, unusual segment permissions.

Normalise evidence so claim and validation logic is shared across both.

## Go ELF Handling

When `file` or Binary Ninja indicates Go:
- DWARF line paths and Go symbols are primary evidence for source-tree recovery.
- Separate application package symbols from Go runtime, stdlib and third-party dependencies before choosing targets. Use `evidence/app_symbols.txt` and `evidence/go_context.json`.
- Claim application-owned packages first. Do not curate the Go runtime unless asked.
- Statically linked Go binaries have very large function counts. Focus on package clusters, command handlers, protocol handlers, config/build metadata, network client setup, persistence/service logic, crypto and compression.
- Do not claim struct layout recovery just because DWARF type names exist. Field-offset claims need `elf_go_type_layout.py` output or equivalent offset/access evidence, plus validator acceptance.

## Output Standard

Report:
- path to `gold/gold.bndb`
- accepted / rejected / needs-human / unreviewed counts
- sample lineage if unpacking occurred
- high-value recovered functions, types, source tree
- unresolved areas and why
- checks and scripts run

Every function analysis includes a call graph. Break long functions into labelled phases with address ranges — "Phase 1 — Entry (`0x17F000`–`0x17F080`)".

Never claim every type or function is resolved unless the unresolved list is empty and the validator accepted the relevant claims.

## After Gold

Once `gold.bndb` exists and the validator has run, the downstream agents take over: `/re-triage` for a capability fingerprint and family verdict, `/re-dive` for a targeted question, `/re-compare` for cross-sample analysis. They read the gold BNDB; they do not create claims.
