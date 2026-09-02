#!/usr/bin/env python3
"""Case and claim utilities for the Binary Ninja gold RE workflow."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
from pathlib import Path
from typing import Any


VALID_KINDS = {
    "function_name",
    "function_comment",
    "data_name",
    "type_definition",
    "source_file",
    # Type application. type_definition only registers a type in the database;
    # these are the kinds that make a recovered type appear in decompiled output.
    "function_prototype",
    "variable_name",
    "variable_type",
    "data_type",
}
VALID_STATUS = {"proposed", "accepted", "rejected", "needs_human"}

# Kinds that propose a symbol name.
NAME_KINDS = {"function_name", "data_name", "variable_name"}

# Whether a proposed function name is the analyst's own ("authored", requiring
# the mw_ actor prefix) or a genuine upstream symbol name read out of the
# binary's own metadata ("recovered", which must not carry the prefix).
VALID_NAME_SOURCES = {"authored", "recovered"}

IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
SYMBOL_SOURCE_TOKENS = (
    "pclntab",
    "dwarf",
    "symtab",
    "symbol table",
    "func_id",
    "funcid",
    "buildinfo",
    "go:func",
    "export table",
)

# Kinds whose target addresses a variable inside a function: "0xVA#var_name".
VARIABLE_KINDS = {"variable_name", "variable_type"}
# Kinds whose proposed_value is C type text rather than an identifier.
TYPE_TEXT_KINDS = {"type_definition", "function_prototype", "variable_type", "data_type"}

DEFAULT_CASES_DIR = os.environ.get("BNGOLD_CASES_DIR", "~/re-cases")

# Evidence sources that may prioritise work but must never be the sole backing
# for an accepted claim. Mirrors the evidence policy in SKILL.md.
LEAD_ONLY_SOURCES = ("malcat", "yara", "capa", "virustotal", "vt:", "malwarebazaar", "otx", "public report")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    with path.open(encoding="utf-8") as handle:
        for lineno, line in enumerate(handle, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{lineno}: invalid JSON: {exc}") from exc
    return rows


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def init_case(args: argparse.Namespace) -> int:
    sample = Path(args.sample).expanduser().resolve()
    if not sample.exists():
        raise FileNotFoundError(sample)
    if not stat.S_ISREG(sample.stat().st_mode):
        raise ValueError(f"not a regular file: {sample}")

    digest = sha256_file(sample)
    stem = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in sample.name)
    case_dir = Path(args.cases_dir).expanduser().resolve() / f"{stem}_{digest[:12]}"
    for subdir in (
        "sample",
        "binja",
        "work",
        "gold",
        "evidence",
        "claims",
        "reports",
        "recovered_tree",
        "triage",
    ):
        (case_dir / subdir).mkdir(parents=True, exist_ok=True)
    original = case_dir / "sample" / "original.bin"
    if not original.exists():
        shutil.copy2(sample, original)
    case = {
        "sample_name": sample.name,
        "original_path": str(sample),
        "case_dir": str(case_dir),
        "sha256": digest,
        "static_only": True,
        "format": "unknown_until_bn_export",
        # The file the gold BNDB actually describes. Rewritten by add-unpacked so
        # a report never silently claims things about a file nobody else can
        # reproduce from the delivered sample.
        "analysis_target": "sample/original.bin",
        "analysis_target_sha256": digest,
        "lineage": [],
    }
    write_json(case_dir / "case.json", case)
    for path in (case_dir / "claims" / "claims.jsonl", case_dir / "claims" / "verdicts.jsonl"):
        path.touch(exist_ok=True)
    print(case_dir)
    return 0


def add_unpacked(args: argparse.Namespace) -> int:
    """Record an unpacked payload and repoint the case at it."""
    case_dir = Path(args.case_dir).expanduser().resolve()
    case_path = case_dir / "case.json"
    case = read_json(case_path, None)
    if case is None:
        raise FileNotFoundError(case_path)

    payload = Path(args.payload).expanduser().resolve()
    if not payload.exists():
        raise FileNotFoundError(payload)
    if not stat.S_ISREG(payload.stat().st_mode):
        raise ValueError(f"not a regular file: {payload}")

    lineage = case.setdefault("lineage", [])
    index = len(lineage) + 1
    dest_rel = f"sample/unpacked_{index:02d}.bin"
    dest = case_dir / dest_rel
    shutil.copy2(payload, dest)

    digest = sha256_file(dest)
    parent_rel = case.get("analysis_target", "sample/original.bin")
    parent_sha = case.get("analysis_target_sha256", case.get("sha256", ""))

    lineage.append(
        {
            "step": index,
            "path": dest_rel,
            "sha256": digest,
            "size": dest.stat().st_size,
            "parent_path": parent_rel,
            "parent_sha256": parent_sha,
            "method": args.method,
            "tool": args.tool,
            "notes": args.notes or "",
        }
    )
    case["analysis_target"] = dest_rel
    case["analysis_target_sha256"] = digest
    write_json(case_path, case)
    print(dest)
    return 0


def validate_claim(claim: dict[str, Any], index: int) -> list[str]:
    errors = []
    prefix = f"claim[{index}]"
    for key in ("claim_id", "kind", "target", "proposed_value", "evidence", "status"):
        if key not in claim:
            errors.append(f"{prefix}: missing {key}")
    if claim.get("kind") not in VALID_KINDS:
        errors.append(f"{prefix}: invalid kind {claim.get('kind')!r}")
    if claim.get("status") not in VALID_STATUS:
        errors.append(f"{prefix}: invalid status {claim.get('status')!r}")
    evidence = claim.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        errors.append(f"{prefix}: evidence must be a non-empty list")
    elif all(
        any(source in str(item).lower() for source in LEAD_ONLY_SOURCES) for item in evidence
    ):
        errors.append(
            f"{prefix}: every evidence item is a lead-only source "
            f"({', '.join(LEAD_ONLY_SOURCES)}); needs local code evidence"
        )
    if claim.get("kind") == "type_definition" and "typedef" not in str(claim.get("proposed_value", "")) and "struct" not in str(claim.get("proposed_value", "")) and "enum" not in str(claim.get("proposed_value", "")):
        errors.append(f"{prefix}: type_definition proposed_value should contain C type text")

    kind = claim.get("kind")
    target = str(claim.get("target", ""))
    value = str(claim.get("proposed_value", "")).strip()

    # Target shape. Variable kinds carry "0xVA#var_name"; everything else is a
    # bare VA. Getting this wrong silently misapplies an edit, so it is fatal.
    if kind in VARIABLE_KINDS:
        if "#" not in target:
            errors.append(
                f"{prefix}: {kind} target must be '0xVA#current_var_name' (got {target!r})"
            )
        else:
            addr_part, _, var_part = target.partition("#")
            if not is_va_hex(addr_part):
                errors.append(f"{prefix}: target address must be VA hex (got {addr_part!r})")
            if not var_part.strip():
                errors.append(f"{prefix}: {kind} target is missing the variable name")
    elif kind in VALID_KINDS and not is_va_hex(target):
        errors.append(f"{prefix}: target must be VA hex like 0x401000 (got {target!r})")

    if kind in TYPE_TEXT_KINDS and not value:
        errors.append(f"{prefix}: {kind} needs non-empty C type text")

    # A prototype must actually look like a function signature, otherwise
    # parse_type_string quietly yields something that is not applied.
    if kind == "function_prototype" and "(" not in value:
        errors.append(
            f"{prefix}: function_prototype proposed_value must be a full C signature "
            f"with a parameter list (got {value!r})"
        )

    # Naming convention is enforced here rather than left to the validator's
    # judgement, so a convention slip never reaches gold.bndb.
    if kind in NAME_KINDS:
        name_source = str(claim.get("name_source", "authored"))
        if name_source not in VALID_NAME_SOURCES:
            errors.append(
                f"{prefix}: name_source must be one of {sorted(VALID_NAME_SOURCES)} "
                f"(got {name_source!r})"
            )
        if not value:
            errors.append(f"{prefix}: {kind} needs a non-empty name")
        else:
            # The 'mw_' prefix exists to answer one question: which functions
            # did the analyst curate, in a binary that may hold thousands of
            # stock ones. That question only applies to the global function
            # namespace, so only function_name carries the prefix. Variables
            # are function-scoped and types are read in context, and prefixing
            # them only makes decompiled output harder to read.
            if kind == "function_name":
                if name_source == "authored" and not value.startswith("mw_"):
                    errors.append(
                        f"{prefix}: a renamed function must be prefixed 'mw_' (got {value!r}); "
                        "if this is a genuine upstream symbol name, set "
                        '"name_source":"recovered" and cite the symbol source'
                    )
                if name_source == "recovered":
                    evidence_text = " ".join(str(item).lower() for item in (evidence or []))
                    if not any(token in evidence_text for token in SYMBOL_SOURCE_TOKENS):
                        errors.append(
                            f"{prefix}: name_source 'recovered' needs evidence citing a symbol "
                            f"source ({', '.join(SYMBOL_SOURCE_TOKENS)})"
                        )
                    if value.startswith("mw_"):
                        errors.append(
                            f"{prefix}: a recovered upstream name must not carry the 'mw_' "
                            f"actor prefix (got {value!r})"
                        )
            elif value.startswith("mw_"):
                errors.append(
                    f"{prefix}: {kind} takes the plain recovered name without the 'mw_' "
                    f"prefix (got {value!r}); the prefix is for functions only"
                )
            if value != value.lower():
                errors.append(f"{prefix}: name must be snake_case (got {value!r})")
            if value.endswith("_likely") or "_likely_" in value:
                errors.append(f"{prefix}: '_likely' is not allowed in a name; use claim status")
            if not IDENTIFIER_RE.match(value):
                errors.append(
                    f"{prefix}: name must be a valid C identifier (got {value!r})"
                )
    return errors


def is_va_hex(text: str) -> bool:
    text = str(text).strip()
    if not text.lower().startswith("0x"):
        return False
    try:
        int(text, 16)
    except ValueError:
        return False
    return True


def cross_claim_errors(
    claims: list[dict[str, Any]], verdicts: list[dict[str, Any]] | None = None
) -> list[str]:
    """Conflicts that are only visible across claims, not within one claim.

    Each of these produced a silent wrong result in gold.bndb rather than an
    error, which is why they are checked before the validator ever runs.

    Only claims that could still reach gold.bndb are considered. A claim the
    validator already rejected cannot conflict with anything, so counting it
    would report a conflict the analyst has no way to clear.
    """
    rejected = {
        verdict.get("claim_id")
        for verdict in (verdicts or [])
        if verdict.get("status") == "rejected"
    }
    claims = [claim for claim in claims if claim.get("claim_id") not in rejected]
    errors = []

    # Two type_definition claims defining the same type name: whichever is
    # applied last wins and the other is reported applied but discarded.
    definers: dict[str, list[str]] = {}
    for claim in claims:
        if claim.get("kind") != "type_definition":
            continue
        for name in type_names_in(str(claim.get("proposed_value", ""))):
            definers.setdefault(name, []).append(str(claim.get("claim_id")))
    for name, owners in sorted(definers.items()):
        if len(owners) > 1:
            errors.append(
                f"type name {name!r} is defined by multiple claims ({', '.join(sorted(owners))}); "
                "last write would silently win — merge them into one claim"
            )

    # A function_prototype replaces the function's parameter variables, so a
    # variable claim naming a parameter of that same function is applied
    # against a variable that no longer exists.
    proto_funcs = {
        str(claim.get("target", "")).strip().lower()
        for claim in claims
        if claim.get("kind") == "function_prototype"
    }
    for claim in claims:
        if claim.get("kind") not in VARIABLE_KINDS:
            continue
        addr_part = str(claim.get("target", "")).partition("#")[0].strip().lower()
        if addr_part in proto_funcs:
            errors.append(
                f"{claim.get('claim_id')}: targets a variable in {addr_part}, which also has a "
                "function_prototype claim; name the parameter in the prototype instead"
            )

    # Two claims of one kind on one target. Every kind but type_definition
    # writes a single slot per target, so the second application silently
    # overwrites the first and both are still reported as applied.
    for kind in sorted(VALID_KINDS - {"type_definition"}):
        seen: dict[str, str] = {}
        for claim in claims:
            if claim.get("kind") != kind:
                continue
            key = str(claim.get("target", "")).strip().lower()
            if key in seen:
                errors.append(
                    f"{claim.get('claim_id')}: duplicate {kind} for target {key} "
                    f"(already claimed by {seen[key]}); the later application would "
                    "silently overwrite the earlier — merge them into one claim"
                )
            else:
                seen[key] = str(claim.get("claim_id"))

    # function_comment and source_file both land in the same comment slot via
    # set_comment_at, so they collide across kinds on a shared target.
    comment_owner: dict[str, tuple[str, str]] = {}
    for claim in claims:
        kind = claim.get("kind")
        if kind not in ("function_comment", "source_file"):
            continue
        key = str(claim.get("target", "")).strip().lower()
        claim_id = str(claim.get("claim_id"))
        if key in comment_owner:
            prev_kind, prev_id = comment_owner[key]
            if prev_kind != kind:
                errors.append(
                    f"{claim_id}: {kind} on target {key} collides with {prev_kind} "
                    f"{prev_id}; both write the same comment via set_comment_at — "
                    "combine them into a single claim"
                )
        else:
            comment_owner[key] = (kind, claim_id)
    return errors


def type_names_in(c_code: str) -> set[str]:
    names = set(re.findall(r"\btypedef\s+struct\s+([A-Za-z_][A-Za-z0-9_]*)\b", c_code))
    names |= set(re.findall(r"\bstruct\s+([A-Za-z_][A-Za-z0-9_]*)\s*\{", c_code))
    names |= set(re.findall(r"\btypedef\s+enum\s+([A-Za-z_][A-Za-z0-9_]*)\b", c_code))
    names |= set(re.findall(r"\benum\s+([A-Za-z_][A-Za-z0-9_]*)\s*\{", c_code))
    names |= set(re.findall(r"\bunion\s+([A-Za-z_][A-Za-z0-9_]*)\s*\{", c_code))
    return names


def validate_claims(args: argparse.Namespace) -> int:
    case_dir = Path(args.case_dir).expanduser().resolve()
    claims = read_jsonl(case_dir / "claims" / "claims.jsonl")
    verdicts = read_jsonl(case_dir / "claims" / "verdicts.jsonl")
    errors = []
    seen = set()
    for index, claim in enumerate(claims, 1):
        errors.extend(validate_claim(claim, index))
        claim_id = claim.get("claim_id")
        if claim_id in seen:
            errors.append(f"claim[{index}]: duplicate claim_id {claim_id}")
        seen.add(claim_id)
    errors.extend(cross_claim_errors(claims, verdicts))

    verdict_by_id = {}
    for index, verdict in enumerate(verdicts, 1):
        claim_id = verdict.get("claim_id")
        status = verdict.get("status")
        if not claim_id:
            errors.append(f"verdict[{index}]: missing claim_id")
        if status not in {"accepted", "rejected", "needs_human"}:
            errors.append(f"verdict[{index}]: invalid status {status!r}")
        verdict_by_id[claim_id] = verdict

    counts = {"claims": len(claims), "accepted": 0, "rejected": 0, "needs_human": 0, "unreviewed": 0}
    for claim in claims:
        verdict = verdict_by_id.get(claim.get("claim_id"))
        if verdict:
            counts[verdict["status"]] += 1
        else:
            counts["unreviewed"] += 1

    summary = {"ok": not errors, "errors": errors, "counts": counts}
    write_json(case_dir / "claims" / "validation_summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if not errors else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Binary Ninja gold RE case utilities")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init", help="create a case workspace")
    p_init.add_argument("sample")
    p_init.add_argument("--cases-dir", default=DEFAULT_CASES_DIR)
    p_init.set_defaults(func=init_case)

    p_unpack = sub.add_parser(
        "add-unpacked", help="record an unpacked payload and repoint the case at it"
    )
    p_unpack.add_argument("case_dir")
    p_unpack.add_argument("payload", help="path to the unpacked file")
    p_unpack.add_argument("--method", required=True, help="e.g. upx, manual-dump, oledump")
    p_unpack.add_argument("--tool", required=True, help="e.g. 'upx 4.2.4'")
    p_unpack.add_argument("--notes", default="")
    p_unpack.set_defaults(func=add_unpacked)

    p_validate = sub.add_parser("validate-claims", help="validate claim/verdict JSONL shape")
    p_validate.add_argument("case_dir")
    p_validate.set_defaults(func=validate_claims)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
