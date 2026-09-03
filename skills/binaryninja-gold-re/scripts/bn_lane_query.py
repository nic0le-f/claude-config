#!/usr/bin/env bnpython3
"""Read-only batch queries against any BNDB lane (base/analyst/validator).

`bn_gold_query.py` deliberately only opens `gold/gold.bndb`, which does not
exist during checkpoint 5. This script fills that gap for the analysis phase:
it opens one BNDB once and answers a batch of queries, so a 40MB+ statically
linked Go database is not reloaded per question.

Read-only. Never calls create_database or any mutating API.

Usage:
    bn_lane_query.py BNDB --decompile 0x401000 0x402000
    bn_lane_query.py BNDB --vars 0x4658c0
    bn_lane_query.py BNDB --disasm 0x4658dc --disasm-count 40
    bn_lane_query.py BNDB --xrefs 0x8f0000
    bn_lane_query.py BNDB --data-xrefs 0x68b000
    bn_lane_query.py BNDB --strings-grep 'https?://'
    bn_lane_query.py BNDB --const 0x8277ec0b
    bn_lane_query.py BNDB --batch spec.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import binaryninja as bn


def resolve_addr(text: Any) -> int:
    if isinstance(text, int):
        return text
    return int(text, 16) if str(text).lower().startswith("0x") else int(str(text), 0)


def func_at(bv: bn.BinaryView, addr: int):
    fns = bv.get_functions_containing(addr) or []
    if fns:
        return fns[0]
    fns = bv.get_functions_at(addr) or []
    return fns[0] if fns else None


def do_decompile(bv: bn.BinaryView, addr: int, raw_hlil: bool = False) -> dict[str, Any]:
    fn = func_at(bv, addr)
    if fn is None:
        return {"address": hex(addr), "error": "no function"}
    if raw_hlil:
        body = "\n".join(str(i) for i in fn.hlil.instructions)
    else:
        body = "\n".join(str(line) for line in fn.hlil.root.lines) if fn.hlil else ""
        if not body:
            body = "\n".join(str(i) for i in fn.hlil.instructions)
    return {
        "address": hex(fn.start),
        "name": fn.name,
        "size": fn.total_bytes,
        "basic_blocks": len(list(fn.basic_blocks)),
        "callees": sorted({hex(c.start) for c in fn.callees}),
        "callers": sorted({hex(c.start) for c in fn.callers}),
        "hlil": body,
    }


def do_vars(bv: bn.BinaryView, addr: int) -> dict[str, Any]:
    """List a function's variables, its prototype, and its parameters.

    This is the fact surface for variable_name / variable_type /
    function_prototype claims. The `target` field of each row is the exact
    string a claim must use, so a claim never has to be hand-assembled.
    """
    fn = func_at(bv, addr)
    if fn is None:
        return {"address": hex(addr), "error": "no function"}
    params = {v.identifier for v in fn.parameter_vars}
    variables = []
    for var in fn.vars:
        variables.append(
            {
                "target": f"{hex(fn.start)}#{var.name}",
                "name": var.name,
                "type": str(var.type) if var.type is not None else "",
                "width": var.type.width if var.type is not None else 0,
                "source_type": getattr(var.source_type, "name", None) or str(var.source_type),
                "is_parameter": var.identifier in params,
                "identifier": hex(var.identifier),
            }
        )
    return {
        "address": hex(fn.start),
        "name": fn.name,
        "prototype": str(fn.type),
        "parameters": [
            {"name": v.name, "type": str(v.type) if v.type is not None else ""}
            for v in fn.parameter_vars
        ],
        "variable_count": len(variables),
        "variables": variables,
    }


def do_disasm(bv: bn.BinaryView, addr: int, count: int) -> dict[str, Any]:
    fn = func_at(bv, addr)
    out = []
    cur = addr
    for _ in range(count):
        toks = bv.get_disassembly(cur)
        if toks is None:
            break
        out.append(f"{cur:#x}  {toks}")
        ln = bv.get_instruction_length(cur)
        if not ln:
            break
        cur += ln
    return {
        "address": hex(addr),
        "function": hex(fn.start) if fn else None,
        "function_name": fn.name if fn else None,
        "disasm": out,
    }


def do_xrefs(bv: bn.BinaryView, addr: int) -> dict[str, Any]:
    code = []
    for ref in bv.get_code_refs(addr):
        code.append({
            "from_function": hex(ref.function.start) if ref.function else None,
            "from_name": ref.function.name if ref.function else None,
            "at": hex(ref.address),
            "disasm": bv.get_disassembly(ref.address),
        })
    data = [hex(r.address) for r in bv.get_data_refs(addr)]
    return {"address": hex(addr), "code_refs": code, "data_refs": data}


def do_const(bv: bn.BinaryView, value: int, limit: int = 200) -> dict[str, Any]:
    """Find instructions whose disassembly mentions a constant."""
    hits = []
    pats = [f"{value:#x}", f"{value:x}"]
    for fn in bv.functions:
        try:
            insns = fn.instructions
        except Exception:
            continue
        for toks, iaddr in insns:
            text = "".join(str(t) for t in toks)
            if any(p in text.lower() for p in pats):
                hits.append({
                    "function": hex(fn.start),
                    "function_name": fn.name,
                    "at": hex(iaddr),
                    "disasm": text,
                })
                if len(hits) >= limit:
                    return {"const": hex(value), "hits": hits, "truncated": True}
    return {"const": hex(value), "hits": hits, "truncated": False}


def do_strings_grep(bv: bn.BinaryView, pattern: str, limit: int) -> dict[str, Any]:
    rx = re.compile(pattern)
    out = []
    for s in bv.strings:
        v = str(s.value)
        if rx.search(v):
            refs = [hex(r.address) for r in bv.get_code_refs(s.start)][:8]
            out.append({"address": hex(s.start), "value": v, "code_refs": refs})
            if len(out) >= limit:
                break
    return {"pattern": pattern, "count": len(out), "strings": out}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("bndb")
    ap.add_argument("--decompile", nargs="*", default=[])
    ap.add_argument("--vars", nargs="*", default=[],
                    help="list variables, prototype and parameters for each function")
    ap.add_argument("--raw-hlil", action="store_true")
    ap.add_argument("--disasm", nargs="*", default=[])
    ap.add_argument("--disasm-count", type=int, default=30)
    ap.add_argument("--xrefs", nargs="*", default=[])
    ap.add_argument("--const", nargs="*", default=[])
    ap.add_argument("--strings-grep")
    ap.add_argument("--limit", type=int, default=300)
    ap.add_argument("--batch", help="JSON file with the same keys as the CLI flags")
    ap.add_argument("--out", help="write JSON results here instead of stdout")
    args = ap.parse_args()

    spec: dict[str, Any] = {
        "decompile": list(args.decompile),
        "vars": list(args.vars),
        "disasm": list(args.disasm),
        "xrefs": list(args.xrefs),
        "const": list(args.const),
        "strings_grep": args.strings_grep,
    }
    if args.batch:
        loaded = json.loads(Path(args.batch).read_text(encoding="utf-8"))
        for k, v in loaded.items():
            spec[k.replace("-", "_")] = v

    path = Path(args.bndb).expanduser().resolve()
    print(f"[query] loading {path}", file=sys.stderr, flush=True)
    bv = bn.load(str(path))
    if bv is None:
        raise RuntimeError(f"failed to load {path}")
    bv.update_analysis_and_wait()

    results: dict[str, Any] = {"bndb": str(path)}
    if spec.get("decompile"):
        results["decompile"] = [
            do_decompile(bv, resolve_addr(a), args.raw_hlil) for a in spec["decompile"]
        ]
    if spec.get("vars"):
        results["vars"] = [do_vars(bv, resolve_addr(a)) for a in spec["vars"]]
    if spec.get("disasm"):
        cnt = spec.get("disasm_count", args.disasm_count)
        results["disasm"] = [do_disasm(bv, resolve_addr(a), cnt) for a in spec["disasm"]]
    if spec.get("xrefs"):
        results["xrefs"] = [do_xrefs(bv, resolve_addr(a)) for a in spec["xrefs"]]
    if spec.get("const"):
        results["const"] = [do_const(bv, resolve_addr(c)) for c in spec["const"]]
    if spec.get("strings_grep"):
        results["strings_grep"] = do_strings_grep(bv, spec["strings_grep"], args.limit)

    text = json.dumps(results, indent=2, sort_keys=False)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
        print(args.out)
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
