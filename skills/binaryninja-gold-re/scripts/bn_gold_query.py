#!/usr/bin/env bnpython3
"""Read-only queries against a case's gold.bndb.

The post-gold agents (re-triage, re-dive, re-compare) use this instead of the
Binary Ninja MCP server: the pipeline is strictly headless, and nothing
downstream of bn_apply_claims.py is allowed to mutate the database.

Run with bnpython3, e.g.
    /home/ubi/Applications/BinaryNinja/binaryninja/bnpython3 bn_gold_query.py summary CASE_DIR
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import binaryninja as bn


def gold_path(case_dir: Path) -> Path:
    gold = case_dir / "gold" / "gold.bndb"
    if not gold.exists():
        raise FileNotFoundError(
            f"no gold BNDB at {gold} — run bn_apply_claims.py before querying"
        )
    return gold


def load_gold(case_dir: Path) -> bn.BinaryView:
    bv = bn.load(str(gold_path(case_dir)))
    if bv is None:
        raise RuntimeError(f"failed to load {gold_path(case_dir)}")
    bv.update_analysis_and_wait()
    return bv


def resolve_addr(text: str) -> int:
    return int(text, 16) if text.lower().startswith("0x") else int(text, 0)


def emit(value: Any) -> None:
    print(json.dumps(value, indent=2, sort_keys=True))


def is_named(name: str) -> bool:
    """Has a real symbol name — not a Binary Ninja auto-generated sub_/j_/data_ label."""
    return not re.match(r"^(sub|j|data|jump_table|__)[_0-9a-fA-F]", name)


def cmd_summary(args: argparse.Namespace) -> int:
    case_dir = Path(args.case_dir).expanduser().resolve()
    bv = load_gold(case_dir)
    case = json.loads((case_dir / "case.json").read_text(encoding="utf-8"))

    named = [f for f in bv.functions if is_named(f.name)]
    emit(
        {
            "sample_name": case.get("sample_name"),
            "sha256": case.get("sha256"),
            "analysis_target": case.get("analysis_target"),
            "unpacked": bool(case.get("lineage")),
            "view_type": bv.view_type,
            "arch": str(bv.arch) if bv.arch else "",
            "platform": str(bv.platform) if bv.platform else "",
            "entry_point": hex(bv.entry_point) if bv.entry_point else "",
            "function_count": len(list(bv.functions)),
            "named_function_count": len(named),
            "string_count": len(bv.strings),
            "section_count": len(bv.sections),
            "named_functions": [
                {"address": hex(f.start), "name": f.name} for f in named[: args.limit]
            ],
        }
    )
    return 0


def cmd_functions(args: argparse.Namespace) -> int:
    bv = load_gold(Path(args.case_dir).expanduser().resolve())
    pattern = re.compile(args.grep, re.IGNORECASE) if args.grep else None
    rows = []
    for func in bv.functions:
        if args.named_only and not is_named(func.name):
            continue
        if pattern and not pattern.search(func.name):
            continue
        rows.append(
            {
                "address": hex(func.start),
                "name": func.name,
                "basic_blocks": len(list(func.basic_blocks)),
                "callees": sorted({hex(c.start) for c in func.callees}),
                "callers": sorted({hex(c.start) for c in func.callers}),
            }
        )
    emit({"count": len(rows), "functions": rows[: args.limit]})
    return 0


def cmd_decompile(args: argparse.Namespace) -> int:
    bv = load_gold(Path(args.case_dir).expanduser().resolve())
    addr = resolve_addr(args.address)
    funcs = bv.get_functions_containing(addr)
    if not funcs:
        print(f"no function at {hex(addr)}", file=sys.stderr)
        return 1
    func = funcs[0]
    print(f"// {func.name} @ {hex(func.start)}")
    comment = func.comment
    if comment:
        print(f"// {comment}")
    for line in func.hlil.root.lines if args.raw_hlil else func.hlil.instructions:
        print(str(line))
    return 0


def cmd_disasm(args: argparse.Namespace) -> int:
    bv = load_gold(Path(args.case_dir).expanduser().resolve())
    addr = resolve_addr(args.address)
    funcs = bv.get_functions_containing(addr)
    if not funcs:
        print(f"no function at {hex(addr)}", file=sys.stderr)
        return 1
    func = funcs[0]
    print(f"; {func.name} @ {hex(func.start)}")
    for block in func.basic_blocks:
        print(f"; --- block {hex(block.start)} ---")
        for text, length in block:
            line = "".join(str(token) for token in text)
            print(f"{hex(block.start)}  {line}")
    return 0


def cmd_xrefs(args: argparse.Namespace) -> int:
    bv = load_gold(Path(args.case_dir).expanduser().resolve())
    addr = resolve_addr(args.address)
    rows = []
    for ref in bv.get_code_refs(addr):
        rows.append(
            {
                "from_function": ref.function.name if ref.function else "",
                "from_function_address": hex(ref.function.start) if ref.function else "",
                "at": hex(ref.address),
            }
        )
    emit({"target": hex(addr), "count": len(rows), "refs": rows[: args.limit]})
    return 0


def cmd_strings(args: argparse.Namespace) -> int:
    bv = load_gold(Path(args.case_dir).expanduser().resolve())
    pattern = re.compile(args.grep, re.IGNORECASE) if args.grep else None
    rows = []
    for s in bv.strings:
        value = str(s.value)
        if pattern and not pattern.search(value):
            continue
        rows.append({"address": hex(s.start), "length": s.length, "value": value})
    emit({"count": len(rows), "strings": rows[: args.limit]})
    return 0


def cmd_imports(args: argparse.Namespace) -> int:
    bv = load_gold(Path(args.case_dir).expanduser().resolve())
    rows = [
        {"name": sym.name, "address": hex(sym.address)}
        for sym in bv.get_symbols_of_type(bn.SymbolType.ImportedFunctionSymbol)
    ]
    emit({"count": len(rows), "imports": rows[: args.limit]})
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only queries against a case's gold.bndb")
    sub = parser.add_subparsers(dest="cmd", required=True)

    def add(name: str, func, help_text: str):
        p = sub.add_parser(name, help=help_text)
        p.add_argument("case_dir")
        p.add_argument("--limit", type=int, default=200)
        p.set_defaults(func=func)
        return p

    add("summary", cmd_summary, "view info plus named function inventory")

    p_fn = add("functions", cmd_functions, "list functions")
    p_fn.add_argument("--named-only", action="store_true", help="skip default sub_/j_ names")
    p_fn.add_argument("--grep", help="regex over function names")

    p_dec = add("decompile", cmd_decompile, "HLIL for the function containing an address")
    p_dec.add_argument("address")
    p_dec.add_argument("--raw-hlil", action="store_true")

    p_dis = add("disasm", cmd_disasm, "disassembly for the function containing an address")
    p_dis.add_argument("address")

    p_xref = add("xrefs", cmd_xrefs, "code references to an address")
    p_xref.add_argument("address")

    p_str = add("strings", cmd_strings, "strings, optionally filtered")
    p_str.add_argument("--grep", help="regex over string values")

    add("imports", cmd_imports, "imported functions")

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
