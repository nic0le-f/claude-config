#!/usr/bin/env python3
"""Generate a concise final report for a Binary Ninja gold RE case."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


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


def read_text(path: Path, default: str = "") -> str:
    if not path.exists():
        return default
    return path.read_text(encoding="utf-8", errors="replace")


def verdict_counts(verdicts: list[dict[str, Any]], total_claims: int) -> dict[str, int]:
    counts = {"accepted": 0, "rejected": 0, "needs_human": 0}
    for row in verdicts:
        status = row.get("status")
        if status in counts:
            counts[status] += 1
    counts["unreviewed"] = max(0, total_claims - sum(counts.values()))
    return counts


def accepted_by_kind(claims: list[dict[str, Any]], verdicts: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    accepted_ids = {row.get("claim_id") for row in verdicts if row.get("status") == "accepted"}
    grouped: dict[str, list[dict[str, Any]]] = {}
    for claim in claims:
        if claim.get("claim_id") in accepted_ids:
            grouped.setdefault(claim.get("kind", "unknown"), []).append(claim)
    return grouped


def plural(count: int, word: str) -> str:
    return word if count == 1 else word + "s"


def executive_summary(
    case: dict[str, Any],
    facts: dict[str, Any],
    counts: dict[str, int],
    grouped: dict[str, list[dict[str, Any]]],
    go_context: dict[str, Any],
) -> list[str]:
    """Two-to-five factual lines. Never asserts more than the verdicts support."""
    bv = facts.get("binary_view", {})
    named = len(grouped.get("function_name", []))
    types = len(grouped.get("type_definition", []))
    total_fns = len(facts.get("functions", []))

    lines = []
    what = f"`{case.get('sample_name', 'sample')}`"
    fmt = " ".join(x for x in (bv.get("view_type", ""), bv.get("arch", ""), bv.get("platform", "")) if x)
    if fmt:
        article = "an" if fmt[:1].upper() in "AEIOU" else "a"
        what += f" is {article} {fmt} binary"
    if go_context.get("is_go"):
        what += " built with Go"
    lines.append(f"- {what}.")

    if case.get("lineage"):
        step = case["lineage"][-1]
        lines.append(
            f"- Analysis target is `{case.get('analysis_target')}` "
            f"(unpacked via {step.get('method')}), not the delivered sample."
        )

    total_claims = counts["accepted"] + counts["rejected"] + counts["needs_human"] + counts["unreviewed"]
    lines.append(
        f"- {counts['accepted']} of {total_claims} claims survived validation: "
        f"{named} function {plural(named, 'name')} and {types} type {plural(types, 'definition')} "
        f"applied to `gold.bndb`."
    )
    if total_fns:
        lines.append(f"- {named} of {total_fns} functions carry validated names; the remainder are uncurated.")

    # Type recovery is only meaningful if a recovered type is actually applied to
    # something, so report the application counts alongside the definitions.
    protos = len(grouped.get("function_prototype", []))
    var_types = len(grouped.get("variable_type", []))
    var_names = len(grouped.get("variable_name", []))
    data_types = len(grouped.get("data_type", []))
    if protos or var_types or var_names or data_types:
        parts = []
        if protos:
            parts.append(f"{protos} function {plural(protos, 'prototype')}")
        if var_types:
            parts.append(f"{var_types} variable {plural(var_types, 'retype')}")
        if var_names:
            parts.append(f"{var_names} variable {plural(var_names, 'rename')}")
        if data_types:
            parts.append(f"{data_types} data {plural(data_types, 'retype')}")
        lines.append(f"- Type recovery applied: {', '.join(parts)}.")
    elif types:
        lines.append(
            f"- {types} type {plural(types, 'definition')} {'is' if types == 1 else 'are'} defined but "
            "applied to no variable, parameter or data symbol; they do not yet appear in decompiled output."
        )
    open_items = []
    if counts["needs_human"]:
        n = counts["needs_human"]
        open_items.append(f"{n} {plural(n, 'claim')} {'needs' if n == 1 else 'need'} human adjudication")
    if counts["unreviewed"]:
        n = counts["unreviewed"]
        open_items.append(f"{n} {plural(n, 'claim')} {'is' if n == 1 else 'are'} unreviewed")
    if open_items:
        lines.append(f"- {' and '.join(open_items)} — the BNDB is not complete.")
    return lines


def detection_anchors(grouped: dict[str, list[dict[str, Any]]]) -> list[str]:
    """Anchors a YARA rule may be built from. Accepted claims only, by construction."""
    lines = []
    for kind in ("data_name", "function_name"):
        rows = grouped.get(kind, [])
        if not rows:
            continue
        lines.append(f"- From accepted `{kind}` claims:")
        for claim in rows[:20]:
            lines.append(f"  - `{claim.get('target')}` → `{claim.get('proposed_value')}`")
    if not lines:
        lines.append("- No accepted claims yet — do not author a rule.")
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate reports/final.md for a gold RE case")
    parser.add_argument("case_dir")
    args = parser.parse_args()

    case_dir = Path(args.case_dir).expanduser().resolve()
    case = read_json(case_dir / "case.json", {})
    facts = read_json(case_dir / "evidence" / "bn_facts.json", {})
    go_context = read_json(case_dir / "evidence" / "go_context.json", {})
    type_layouts = read_json(case_dir / "evidence" / "go_type_layouts.json", {})
    applied_claims = read_json(case_dir / "reports" / "applied_claims.json", {})
    claims = read_jsonl(case_dir / "claims" / "claims.jsonl")
    verdicts = read_jsonl(case_dir / "claims" / "verdicts.jsonl")
    counts = verdict_counts(verdicts, len(claims))
    grouped = accepted_by_kind(claims, verdicts)

    sample_name = case.get("sample_name", "sample")
    bv = facts.get("binary_view", {})
    sample = facts.get("sample", {})
    source_tree = read_text(case_dir / "recovered_tree" / "source_tree.md")

    # Executive Summary then Table of Contents, before any other section.
    report_lines = [
        f"# {sample_name} Gold BNDB Report",
        "",
        "## Executive Summary",
        "",
    ]
    report_lines.extend(executive_summary(case, facts, counts, grouped, go_context))
    report_lines.extend(
        [
            "",
            "## Table of Contents",
            "",
            "1. [Executive Summary](#executive-summary)",
            "2. [Artifacts](#artifacts)",
            "3. [Sample Lineage](#sample-lineage)",
            "4. [Observed Facts](#observed-facts)",
            "5. [Claim Status](#claim-status)",
            "6. [Accepted Highlights](#accepted-highlights)",
            "7. [Source Tree](#source-tree)",
            "8. [Detection Anchors](#detection-anchors)",
            "9. [Unresolved Areas](#unresolved-areas)",
            "10. [Checks Run](#checks-run)",
            "",
            "## Artifacts",
            "",
            f"- Gold BNDB: `{case_dir / 'gold' / 'gold.bndb'}`",
            f"- BN facts: `{case_dir / 'evidence' / 'bn_facts.json'}`",
            f"- Claims: `{case_dir / 'claims' / 'claims.jsonl'}`",
            f"- Verdicts: `{case_dir / 'claims' / 'verdicts.jsonl'}`",
            "",
            "## Sample Lineage",
            "",
        ]
    )
    lineage = case.get("lineage") or []
    if not lineage:
        report_lines.append(
            f"- No unpacking performed. The gold BNDB describes `sample/original.bin` "
            f"(`{case.get('sha256', '')}`)."
        )
    else:
        report_lines.append(
            f"- Delivered sample: `sample/original.bin` (`{case.get('sha256', '')}`)"
        )
        for step in lineage:
            report_lines.append(
                f"- Step {step.get('step')}: `{step.get('parent_path')}` → `{step.get('path')}` "
                f"via {step.get('method')} ({step.get('tool')}) — `{step.get('sha256')}`"
                + (f" — {step['notes']}" if step.get("notes") else "")
            )
        report_lines.append(
            f"- **The gold BNDB describes `{case.get('analysis_target')}`, not the delivered sample.**"
        )

    report_lines.extend(
        [
            "",
            "## Observed Facts",
            "",
            f"- Sample: `{sample_name}`",
            f"- SHA-256: `{case.get('sha256') or sample.get('sha256', '')}`",
            f"- Size: `{sample.get('size', '')}` bytes",
            f"- Binary Ninja view: `{bv.get('view_type', '')}` `{bv.get('arch', '')}` `{bv.get('platform', '')}`",
            f"- Entry point: `{bv.get('entry_point', '')}`",
            f"- Functions exported: `{len(facts.get('functions', []))}`",
            f"- Strings exported: `{len(facts.get('strings', []))}`",
            f"- Sections exported: `{len(facts.get('sections', []))}`",
        ]
    )
    if go_context:
        report_lines.extend(
            [
                f"- Go binary: `{go_context.get('is_go')}`",
                f"- Application roots: `{', '.join(go_context.get('app_roots', []))}`",
                f"- DWARF source paths: `{len(go_context.get('source_paths', []))}`",
                f"- Application symbols: `{go_context.get('symbol_counts', {}).get('app', 0)}`",
            ]
        )
    if type_layouts:
        report_lines.append(f"- DWARF app struct layouts: `{len(type_layouts.get('structs', []))}`")
    if applied_claims:
        for phase in ("type_definition", "function_prototype", "variable_type", "variable_name"):
            rows = applied_claims.get(phase, [])
            if rows:
                report_lines.append(f"- Applied `{phase}` claims: `{len(rows)}`")
        if applied_claims.get("other"):
            report_lines.append(f"- Applied other claims: `{len(applied_claims['other'])}`")
    report_lines.extend(
        [
            "",
            "## Claim Status",
            "",
            f"- Accepted: {counts['accepted']}",
            f"- Rejected: {counts['rejected']}",
            f"- Needs human: {counts['needs_human']}",
            f"- Unreviewed: {counts['unreviewed']}",
            "",
            "## Accepted Highlights",
            "",
        ]
    )
    if not grouped:
        report_lines.append("- No accepted claims yet.")
    else:
        for kind in sorted(grouped):
            report_lines.append(f"- `{kind}`: {len(grouped[kind])}")
            for claim in grouped[kind][:8]:
                report_lines.append(f"  - `{claim.get('target')}` -> `{claim.get('proposed_value')}`")
    report_lines.extend(["", "## Source Tree", ""])
    if source_tree:
        report_lines.append(source_tree)
    else:
        report_lines.append("No recovered source tree has been generated yet.")
    report_lines.extend(["", "## Detection Anchors", "", "Author YARA rules from these only — never from rejected, needs-human, or unreviewed claims. Rule structure and metadata follow the `/malware-analyst` standards; write rules to `reports/rules.yar`.", ""])
    report_lines.extend(detection_anchors(grouped))
    report_lines.extend(
        [
            "",
            "## Unresolved Areas",
            "",
            "- Review rejected, needs-human, and unreviewed claims before calling the BNDB gold-standard complete.",
            "- Runtime/library functions and compiler-generated code should remain uncurated unless they affect application behavior.",
            "- Type/struct layouts require dedicated offset/access evidence and validator acceptance.",
            "",
            "## Checks Run",
            "",
            "- Binary Ninja fact export if `evidence/bn_facts.json` exists.",
            "- Claim/verdict validation if `claims/validation_summary.json` exists.",
            "- ELF/Go context extraction if `evidence/go_context.json` exists.",
            "- Go type-layout extraction if `evidence/go_type_layouts.json` exists.",
            "- Accepted-claim application if `reports/applied_claims.json` exists.",
        ]
    )
    out = case_dir / "reports" / "final.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
