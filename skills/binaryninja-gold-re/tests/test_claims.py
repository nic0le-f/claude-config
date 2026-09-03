#!/usr/bin/env python3
"""Regression tests for the claim shape-validation layer.

Covers the four claim kinds added for argument, variable and structure
recovery (function_prototype, variable_name, variable_type, data_type) and the
cross-claim conflict rules that guard against silent wrong writes to gold.bndb.
The apply layer (bn_apply_claims.py) needs Binary Ninja and a real .bndb, so it
is out of scope here; these tests pin the pure-Python gate that runs before it.

Stdlib unittest only — no third-party runner is configured for this repo.

    python3 skills/binaryninja-gold-re/tests/test_claims.py
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import bngold_case as bc  # noqa: E402


def errors_for(claim: dict) -> list[str]:
    """validate_claim errors for a single claim."""
    return bc.validate_claim(claim, 1)


def joined(errors: list[str]) -> str:
    return " || ".join(errors)


# A minimal well-formed claim of each new kind, used as the base each negative
# test mutates one field of. Keeping the base valid is itself a test: if any of
# these starts erroring, the assertions below stop being meaningful.
GOOD = {
    "function_prototype": {
        "claim_id": "proto_401000",
        "kind": "function_prototype",
        "target": "0x401000",
        "proposed_value": "int64_t f(struct c2_config* cfg, uint64_t len)",
        "evidence": ["9 of 9 call sites pass cfg in rdi", "len in rsi is the memcpy size"],
        "status": "proposed",
    },
    "variable_type": {
        "claim_id": "vtype_401500_cfg",
        "kind": "variable_type",
        "target": "0x401500#var_18",
        "proposed_value": "struct c2_config*",
        "evidence": ["field access +0x18 width 8", "passed to config parser"],
        "status": "proposed",
    },
    "variable_name": {
        "claim_id": "vname_401500_cfg",
        "kind": "variable_name",
        "target": "0x401500#var_18",
        "proposed_value": "cfg",
        "evidence": ["holds pointer written by config allocator", "read at every parse step"],
        "status": "proposed",
    },
    "data_type": {
        "claim_id": "dtype_402000",
        "kind": "data_type",
        "target": "0x402000",
        "proposed_value": "struct c2_config",
        "evidence": ["24-byte read by config parser", "offsets 0/8/16 accessed"],
        "status": "proposed",
    },
}


class GoodClaims(unittest.TestCase):
    def test_each_new_kind_is_accepted(self):
        for kind, claim in GOOD.items():
            with self.subTest(kind=kind):
                self.assertEqual(errors_for(claim), [], msg=joined(errors_for(claim)))


class PrototypeRules(unittest.TestCase):
    def test_signature_without_parameter_list_is_rejected(self):
        claim = {**GOOD["function_prototype"], "proposed_value": "int64_t f"}
        self.assertIn("full C signature", joined(errors_for(claim)))

    def test_empty_signature_is_rejected(self):
        claim = {**GOOD["function_prototype"], "proposed_value": ""}
        self.assertTrue(errors_for(claim))


class VariableTargetRules(unittest.TestCase):
    def test_variable_target_needs_var_suffix(self):
        claim = {**GOOD["variable_name"], "target": "0x401500"}
        self.assertIn("0xVA#current_var_name", joined(errors_for(claim)))

    def test_variable_target_address_must_be_va_hex(self):
        claim = {**GOOD["variable_name"], "target": "401500#var_18"}
        self.assertIn("VA hex", joined(errors_for(claim)))

    def test_variable_target_missing_name_after_hash(self):
        claim = {**GOOD["variable_name"], "target": "0x401500#"}
        self.assertIn("missing the variable name", joined(errors_for(claim)))

    def test_variable_type_needs_nonempty_text(self):
        claim = {**GOOD["variable_type"], "proposed_value": ""}
        self.assertIn("non-empty C type text", joined(errors_for(claim)))


class NameConventionRules(unittest.TestCase):
    def test_mw_prefix_rejected_on_variable(self):
        claim = {**GOOD["variable_name"], "proposed_value": "mw_cfg"}
        self.assertIn("plain recovered name", joined(errors_for(claim)))

    def test_name_must_be_snake_case(self):
        claim = {**GOOD["variable_name"], "proposed_value": "myBuffer"}
        self.assertIn("snake_case", joined(errors_for(claim)))

    def test_likely_suffix_is_rejected(self):
        claim = {**GOOD["variable_name"], "proposed_value": "cfg_likely"}
        self.assertIn("_likely", joined(errors_for(claim)))

    def test_invalid_identifier_is_rejected(self):
        claim = {**GOOD["variable_name"], "proposed_value": "cfg-ptr"}
        self.assertTrue(errors_for(claim))

    def test_function_name_authored_needs_mw_prefix(self):
        claim = {
            "claim_id": "fn_1",
            "kind": "function_name",
            "target": "0x401000",
            "proposed_value": "config_parse",
            "evidence": ["xref to 'c2list='", "calls inet_addr"],
            "status": "proposed",
        }
        self.assertIn("prefixed 'mw_'", joined(errors_for(claim)))

    def test_function_name_recovered_rejects_mw_prefix(self):
        claim = {
            "claim_id": "fn_2",
            "kind": "function_name",
            "target": "0x401000",
            "proposed_value": "mw_main",
            "name_source": "recovered",
            "evidence": ["pclntab symbol main.main"],
            "status": "proposed",
        }
        self.assertIn("must not carry the 'mw_'", joined(errors_for(claim)))

    def test_function_name_recovered_needs_symbol_source_evidence(self):
        claim = {
            "claim_id": "fn_3",
            "kind": "function_name",
            "target": "0x401000",
            "proposed_value": "main_run",
            "name_source": "recovered",
            "evidence": ["looks like the entry point"],
            "status": "proposed",
        }
        self.assertIn("symbol source", joined(errors_for(claim)))


class EvidenceRules(unittest.TestCase):
    def test_lead_only_evidence_is_rejected(self):
        claim = {**GOOD["data_type"], "evidence": ["capa says config", "virustotal detection"]}
        self.assertIn("lead-only source", joined(errors_for(claim)))

    def test_empty_evidence_is_rejected(self):
        claim = {**GOOD["data_type"], "evidence": []}
        self.assertIn("non-empty list", joined(errors_for(claim)))


class CrossClaimRules(unittest.TestCase):
    def test_prototype_and_variable_on_same_function_collide(self):
        claims = [
            GOOD["function_prototype"],  # target 0x401000
            {**GOOD["variable_name"], "target": "0x401000#var_18"},
        ]
        errs = bc.cross_claim_errors(claims, [])
        self.assertIn("function_prototype claim", joined(errs))

    def test_prototype_and_variable_on_different_functions_are_fine(self):
        errs = bc.cross_claim_errors(
            [GOOD["function_prototype"], GOOD["variable_name"]], []  # 0x401000 vs 0x401500
        )
        self.assertEqual(errs, [], msg=joined(errs))

    def test_duplicate_variable_name_on_same_target_collides(self):
        claims = [
            GOOD["variable_name"],
            {**GOOD["variable_name"], "claim_id": "vname_dup", "proposed_value": "config"},
        ]
        self.assertIn("duplicate variable_name", joined(bc.cross_claim_errors(claims, [])))

    def test_two_type_definitions_of_same_name_collide(self):
        claims = [
            {
                "claim_id": "t1",
                "kind": "type_definition",
                "target": "0x0",
                "proposed_value": "struct c2_config { uint64_t a; };",
                "evidence": ["offset 0 width 8"],
                "status": "proposed",
            },
            {
                "claim_id": "t2",
                "kind": "type_definition",
                "target": "0x0",
                "proposed_value": "struct c2_config { uint32_t b; };",
                "evidence": ["offset 0 width 4"],
                "status": "proposed",
            },
        ]
        self.assertIn("defined by multiple claims", joined(bc.cross_claim_errors(claims, [])))


class SupersedeRules(unittest.TestCase):
    def _proto(self, cid: str, **over) -> dict:
        return {**GOOD["function_prototype"], "claim_id": cid, **over}

    def test_valid_supersede_of_reviewed_claim(self):
        claims = [
            self._proto("proto_v1"),
            self._proto("proto_v2", supersedes="proto_v1"),
        ]
        verdicts = [{"claim_id": "proto_v1", "status": "needs_human"}]
        self.assertEqual(bc.supersede_errors(claims, verdicts), [])

    def test_self_supersede_is_rejected(self):
        claims = [self._proto("proto_v1", supersedes="proto_v1")]
        self.assertIn("supersedes itself", joined(bc.supersede_errors(claims, [])))

    def test_supersede_of_missing_claim_is_rejected(self):
        claims = [self._proto("proto_v2", supersedes="ghost")]
        self.assertIn("not a claim in this file", joined(bc.supersede_errors(claims, [])))

    def test_supersede_kind_mismatch_is_rejected(self):
        claims = [
            {**GOOD["variable_name"], "claim_id": "v1"},
            self._proto("proto_v2", supersedes="v1"),
        ]
        verdicts = [{"claim_id": "v1", "status": "accepted"}]
        self.assertIn("same kind", joined(bc.supersede_errors(claims, verdicts)))

    def test_supersede_of_unreviewed_claim_is_rejected(self):
        claims = [self._proto("proto_v1"), self._proto("proto_v2", supersedes="proto_v1")]
        self.assertIn("no verdict yet", joined(bc.supersede_errors(claims, [])))

    def test_double_supersede_is_ambiguous(self):
        claims = [
            self._proto("proto_v1"),
            self._proto("proto_a", supersedes="proto_v1"),
            self._proto("proto_b", supersedes="proto_v1"),
        ]
        verdicts = [{"claim_id": "proto_v1", "status": "rejected"}]
        self.assertIn("more than one claim", joined(bc.supersede_errors(claims, verdicts)))


class EndToEndCli(unittest.TestCase):
    """Run the validate-claims subcommand exactly as the pipeline does."""

    def _run(self, claims: list[dict]) -> tuple[int, dict]:
        with tempfile.TemporaryDirectory() as tmp:
            case = Path(tmp)
            (case / "claims").mkdir()
            (case / "claims" / "claims.jsonl").write_text(
                "\n".join(json.dumps(c) for c in claims) + "\n", encoding="utf-8"
            )
            proc = subprocess.run(
                [sys.executable, str(SCRIPTS / "bngold_case.py"), "validate-claims", str(case)],
                capture_output=True,
                text=True,
            )
            summary = json.loads((case / "claims" / "validation_summary.json").read_text())
            return proc.returncode, summary

    def test_clean_set_exits_zero(self):
        code, summary = self._run([GOOD["function_prototype"], GOOD["variable_name"], GOOD["data_type"]])
        self.assertEqual(code, 0, msg=joined(summary["errors"]))
        self.assertTrue(summary["ok"])

    def test_malformed_set_exits_one(self):
        bad = {**GOOD["variable_name"], "proposed_value": "myBuffer"}
        code, summary = self._run([bad])
        self.assertEqual(code, 1)
        self.assertFalse(summary["ok"])
        self.assertTrue(summary["errors"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
