#!/usr/bin/env bnpython3
"""Apply accepted claims to gold/gold.bndb."""

from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any

import binaryninja as bn


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def parse_addr(value: str) -> int:
    return int(str(value), 0)


def accepted_claims(case_dir: Path) -> list[dict[str, Any]]:
    claims = {row["claim_id"]: row for row in read_jsonl(case_dir / "claims" / "claims.jsonl")}
    verdicts = read_jsonl(case_dir / "claims" / "verdicts.jsonl")
    accepted = []
    for verdict in verdicts:
        if verdict.get("status") == "accepted" and verdict.get("claim_id") in claims:
            accepted.append(claims[verdict["claim_id"]])
    return accepted


def type_defs_in(c_code: str) -> set[str]:
    names = set(re.findall(r"\btypedef\s+struct\s+([A-Za-z_][A-Za-z0-9_]*)\b", c_code))
    names |= set(re.findall(r"\bstruct\s+([A-Za-z_][A-Za-z0-9_]*)\s*\{", c_code))
    names |= set(re.findall(r"\btypedef\s+enum\s+([A-Za-z_][A-Za-z0-9_]*)\b", c_code))
    names |= set(re.findall(r"\benum\s+([A-Za-z_][A-Za-z0-9_]*)\s*\{", c_code))
    return names


def type_refs_in(c_code: str) -> set[str]:
    refs = set(re.findall(r"\bstruct\s+([A-Za-z_][A-Za-z0-9_]*)\b", c_code))
    refs |= set(re.findall(r"\benum\s+([A-Za-z_][A-Za-z0-9_]*)\b", c_code))
    return refs - type_defs_in(c_code)


def sort_type_claims(type_claims: list[dict[str, Any]]) -> list[dict[str, Any]]:
    defs_by_claim = {claim["claim_id"]: type_defs_in(str(claim["proposed_value"])) for claim in type_claims}
    def_owner = {}
    for claim_id, names in defs_by_claim.items():
        for name in names:
            def_owner.setdefault(name, claim_id)
    all_def_names = set(def_owner)

    deps = {}
    for claim in type_claims:
        claim_id = claim["claim_id"]
        c_code = str(claim["proposed_value"])
        refs = type_refs_in(c_code)
        refs |= set(re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\b", c_code)) & all_def_names
        refs -= defs_by_claim.get(claim_id, set())
        deps[claim_id] = {
            def_owner[ref]
            for ref in refs
            if ref in def_owner and def_owner[ref] != claim_id
        }

    pending = {claim["claim_id"]: claim for claim in type_claims}
    ordered = []
    while pending:
        ready = sorted(
            claim_id for claim_id in pending
            if not (deps.get(claim_id, set()) & pending.keys())
        )
        if not ready:
            ordered.extend(pending[claim_id] for claim_id in sorted(pending))
            break
        for claim_id in ready:
            ordered.append(pending.pop(claim_id))
    return ordered


def existing_type_names(bv: bn.BinaryView) -> set[str]:
    """Type names the database already owns before any claim is applied.

    Platform and format types (Elf64_Header, __kernel_long_t, libc typedefs)
    live in the same namespace as recovered ones. define_user_type replaces a
    name outright, so a claim that reuses one silently rewrites it — an
    Elf64_Header claim shrank the real 64-byte struct to 4 bytes in testing.
    Recovered names carry no prefix to keep them readable, so this is checked
    rather than avoided by convention.
    """
    names = set()
    user_types = getattr(bv, "user_type_container", None)
    user_names = set()
    if user_types is not None:
        for _tid, entry in user_types.types.items():
            user_names.add(str(entry[0]))
    for entry in bv.types:
        name = str(entry[0]) if isinstance(entry, tuple) else str(entry)
        if name not in user_names:
            names.add(name)
    return names


def apply_type_claims(bv: bn.BinaryView, type_claims: list[dict[str, Any]]) -> list[str]:
    if not type_claims:
        return []
    ordered = sort_type_claims(type_claims)

    preexisting = existing_type_names(bv)
    for claim in ordered:
        for name in type_defs_in(str(claim["proposed_value"])):
            if name in preexisting:
                raise RuntimeError(
                    f"claim {claim['claim_id']}: type name {name!r} already exists in the "
                    "database as a platform or format type; applying it would silently "
                    "replace that definition — pick a distinct name for the recovered type"
                )
    chunks = []
    for claim in ordered:
        text = str(claim["proposed_value"]).strip()
        if not text:
            continue
        # Binary Ninja's type parser requires a terminating semicolon after a
        # struct/union/enum definition. The claim format documented in SKILL.md
        # does not ask authors for one, so normalise here rather than rejecting
        # otherwise-valid accepted claims on punctuation.
        if not text.endswith((";", "}")):
            text += ";"
        elif text.endswith("}"):
            text += ";"
        chunks.append(text)
    combined = "\n\n".join(chunks) + "\n"
    try:
        result = bv.parse_types_from_string(combined)
    except Exception as exc:
        raise RuntimeError(
            "failed to apply accepted type definitions as a dependency-sorted batch"
        ) from exc

    # parse_types_from_string only *parses*. Without define_user_type the types
    # never reach the database, and the run would report success while gold.bndb
    # contained nothing. Register every parsed type explicitly.
    parsed = getattr(result, "types", None) or {}
    items = parsed.items() if hasattr(parsed, "items") else [
        (getattr(t, "name", None), getattr(t, "type", None)) for t in parsed
    ]
    defined = 0
    for name, type_obj in items:
        if name is None or type_obj is None:
            continue
        bv.define_user_type(name, type_obj)
        defined += 1
    if defined == 0:
        raise RuntimeError(
            f"parsed {len(chunks)} type definition(s) but registered none into the "
            "BinaryView; refusing to report them as applied"
        )

    # Confirm every type name each claim declares is now resolvable. Without
    # this, a claim whose text parsed but whose type never registered would be
    # reported as applied while gold.bndb had nothing under that name.
    for claim in ordered:
        for name in type_defs_in(str(claim["proposed_value"])):
            if bv.get_type_by_name(name) is None:
                raise RuntimeError(
                    f"claim {claim['claim_id']}: type {name!r} is not present in the "
                    "database after applying the type batch"
                )
    print(f"[bngold] registered {defined} type definition(s)", flush=True)
    return [claim["claim_id"] for claim in ordered]


def parse_var_target(target: str) -> tuple[int, str]:
    """Split a variable claim target "0xVA#var_name" into (address, name)."""
    addr_part, sep, var_part = str(target).partition("#")
    if not sep or not var_part.strip():
        raise RuntimeError(f"variable target must be '0xVA#var_name', got {target!r}")
    return parse_addr(addr_part.strip()), var_part.strip()


def require_function(bv: bn.BinaryView, addr: int, claim_id: str):
    func = bv.get_function_at(addr)
    if func is None:
        raise RuntimeError(f"function not found for claim {claim_id}: {hex(addr)}")
    return func


def parse_type_text(bv: bn.BinaryView, text: str, claim_id: str):
    """Parse claim type text into a Type.

    parse_type_string raises on an unknown named type, so a claim referring to a
    struct that was never defined fails here instead of silently applying a
    degraded type.
    """
    try:
        parsed_type, _ = bv.parse_type_string(str(text).strip())
    except Exception as exc:
        raise RuntimeError(
            f"claim {claim_id}: could not parse type text {text!r} "
            f"(is the struct defined by an accepted type_definition claim?)"
        ) from exc
    return parsed_type


def apply_prototype_claims(bv: bn.BinaryView, claims: list[dict[str, Any]]) -> list[str]:
    """Set full function signatures.

    Assigning Function.type is a silent no-op in this API version; the edit only
    lands via set_user_type followed by reanalysis. Applied before any variable
    claim because a new signature replaces the function's parameter variables.
    """
    applied = []
    for claim in claims:
        claim_id = claim["claim_id"]
        func = require_function(bv, parse_addr(claim["target"]), claim_id)
        proto = parse_type_text(bv, claim["proposed_value"], claim_id)
        func.set_user_type(proto)
        func.reanalyze()
        applied.append(claim_id)
    if applied:
        bv.update_analysis_and_wait()
    for claim in claims:
        func = require_function(bv, parse_addr(claim["target"]), claim["claim_id"])
        want = str(parse_type_text(bv, claim["proposed_value"], claim["claim_id"]))
        if str(func.type).replace(" ", "") != want.replace(" ", ""):
            raise RuntimeError(
                f"claim {claim['claim_id']}: prototype did not take effect on "
                f"{claim['target']}; wanted {want!r}, database has {str(func.type)!r}"
            )
    return applied


def resolve_variables(
    bv: bn.BinaryView, claims: list[dict[str, Any]]
) -> dict[str, tuple[Any, Any]]:
    """Resolve every variable claim target to a concrete Variable up front.

    Variables are addressed by their current name, but applying a rename changes
    that name. Resolving all targets before any rename is applied keeps a second
    claim against the same function from looking up a name that no longer exists.
    """
    resolved: dict[str, tuple[Any, Any]] = {}
    for claim in claims:
        claim_id = claim["claim_id"]
        addr, var_name = parse_var_target(claim["target"])
        func = require_function(bv, addr, claim_id)
        var = func.get_variable_by_name(var_name)
        if var is None:
            available = sorted(v.name for v in func.vars)[:20]
            raise RuntimeError(
                f"claim {claim_id}: no variable named {var_name!r} in {hex(addr)} "
                f"({func.name}); available: {', '.join(available) or 'none'}"
            )
        resolved[claim_id] = (func, var)
    return resolved


def apply_variable_type_claims(
    bv: bn.BinaryView, claims: list[dict[str, Any]], resolved: dict[str, tuple[Any, Any]]
) -> list[str]:
    applied = []
    for claim in claims:
        claim_id = claim["claim_id"]
        _, var = resolved[claim_id]
        new_type = parse_type_text(bv, claim["proposed_value"], claim_id)
        var.type = new_type
        if str(var.type).replace(" ", "") != str(new_type).replace(" ", ""):
            raise RuntimeError(
                f"claim {claim_id}: retype did not take effect on {claim['target']}; "
                f"wanted {str(new_type)!r}, database has {str(var.type)!r}"
            )
        applied.append(claim_id)
    return applied


def apply_variable_name_claims(
    claims: list[dict[str, Any]], resolved: dict[str, tuple[Any, Any]]
) -> list[str]:
    applied = []
    for claim in claims:
        claim_id = claim["claim_id"]
        func, var = resolved[claim_id]
        wanted = str(claim["proposed_value"])
        var.name = wanted
        if func.get_variable_by_name(wanted) is None:
            raise RuntimeError(
                f"claim {claim_id}: rename to {wanted!r} did not take effect on {claim['target']}"
            )
        applied.append(claim_id)
    return applied


def apply_claim(bv: bn.BinaryView, claim: dict[str, Any]) -> None:
    kind = claim["kind"]
    target = claim["target"]
    value = claim["proposed_value"]
    claim_id = claim["claim_id"]
    if kind == "function_name":
        func = require_function(bv, parse_addr(target), claim_id)
        func.name = str(value)
        if func.name != str(value):
            raise RuntimeError(f"claim {claim_id}: rename to {value!r} did not take effect")
    elif kind == "function_comment":
        bv.set_comment_at(parse_addr(target), str(value))
    elif kind == "data_name":
        bv.define_user_symbol(bn.Symbol(bn.SymbolType.DataSymbol, parse_addr(target), str(value)))
    elif kind == "data_type":
        addr = parse_addr(target)
        new_type = parse_type_text(bv, value, claim_id)
        bv.define_user_data_var(addr, new_type)
        data_var = bv.get_data_var_at(addr)
        if data_var is None or str(data_var.type).replace(" ", "") != str(new_type).replace(" ", ""):
            have = str(data_var.type) if data_var is not None else "no data variable"
            raise RuntimeError(
                f"claim {claim_id}: data retype did not take effect at {target}; "
                f"wanted {str(new_type)!r}, database has {have!r}"
            )
    elif kind in ("type_definition", "function_prototype", "variable_name", "variable_type"):
        raise RuntimeError(f"{kind} claims are applied in their own ordered phase")
    elif kind == "source_file":
        comment = f"Recovered source file: {value}\nEvidence: {'; '.join(map(str, claim.get('evidence', [])))}"
        bv.set_comment_at(parse_addr(target), comment)
    else:
        raise RuntimeError(f"unsupported claim kind: {kind}")


def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    if len(argv) != 1:
        print(f"usage: {sys.argv[0]} CASE_DIR", file=sys.stderr)
        return 2
    case_dir = Path(argv[0]).expanduser().resolve()
    base = case_dir / "binja" / "base.bndb"
    gold = case_dir / "gold" / "gold.bndb"
    if not base.exists():
        raise FileNotFoundError(base)
    gold.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(base, gold)
    bv = bn.load(str(gold))
    if bv is None:
        raise RuntimeError(f"failed to load {gold}")
    claims = accepted_claims(case_dir)

    def of_kind(kind: str) -> list[dict[str, Any]]:
        return [claim for claim in claims if claim.get("kind") == kind]

    # Phase order matters and is not arbitrary:
    #   1. types must exist before anything can reference them
    #   2. prototypes replace parameter variables, so they precede variable work
    #   3. variable targets are resolved to concrete Variables before the first
    #      rename, because a rename invalidates lookup by the old name
    #   4. retype before rename, so failures still report the original name
    applied: dict[str, list[str]] = {}
    applied["type_definition"] = apply_type_claims(bv, of_kind("type_definition"))
    applied["function_prototype"] = apply_prototype_claims(bv, of_kind("function_prototype"))

    var_claims = [claim for claim in claims if claim.get("kind") in ("variable_name", "variable_type")]
    resolved = resolve_variables(bv, var_claims)
    applied["variable_type"] = apply_variable_type_claims(bv, of_kind("variable_type"), resolved)
    applied["variable_name"] = apply_variable_name_claims(of_kind("variable_name"), resolved)

    phased = {"type_definition", "function_prototype", "variable_name", "variable_type"}
    applied["other"] = []
    for claim in claims:
        if claim.get("kind") in phased:
            continue
        apply_claim(bv, claim)
        applied["other"].append(claim["claim_id"])

    counts = {key: len(value) for key, value in applied.items() if value}
    print(f"[bngold] applied {sum(counts.values())} accepted claim(s): {counts}", flush=True)
    bv.update_analysis_and_wait()
    if not bv.create_database(str(gold)):
        raise RuntimeError(f"failed to save {gold}")
    report_path = case_dir / "reports" / "applied_claims.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(applied, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(gold)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
