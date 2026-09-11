from __future__ import annotations

import unittest
from unittest.mock import patch

from scripts.project_repair_evidence import build_summary


def audit(verdict: str, counts: dict[str, int]) -> dict:
    findings = []
    code_for = {
        "views": "VIEW_COUNT",
        "cards": "OPEN_P01_STAGE",
        "schema": "FIELD_OPTIONS",
        "governance": "RULESET_STRICT",
        "other": "NEW_FUTURE_CHECK",
    }
    for domain, count in counts.items():
        for index in range(count):
            findings.append({"code": code_for[domain], "message": f"{domain}-{index}"})
    return {
        "schema": "KAT9I_G0_AUDIT/1",
        "verdict": verdict,
        "finding_count": len(findings),
        "findings": findings,
    }


class ProjectRepairEvidenceTests(unittest.TestCase):
    @patch("scripts.project_repair_evidence.audit_from_snapshot")
    def test_target_repair_can_pass_while_global_audit_stays_fail(self, before_mock) -> None:
        before_mock.return_value = audit("FAIL", {"views": 2, "cards": 3, "schema": 0, "governance": 0, "other": 0})
        result = build_summary(
            target_domain="views",
            apply_outcome="success",
            before_snapshot={},
            after_audit=audit("FAIL", {"views": 0, "cards": 3, "schema": 0, "governance": 0, "other": 0}),
        )
        self.assertEqual(result["repair_verdict"], "PASS")
        self.assertEqual(result["global_audit_verdict"], "FAIL")
        self.assertEqual(result["target_after"], 0)

    @patch("scripts.project_repair_evidence.audit_from_snapshot")
    def test_new_unrelated_drift_blocks_repair_pass(self, before_mock) -> None:
        before_mock.return_value = audit("FAIL", {"views": 2, "cards": 0, "schema": 0, "governance": 0, "other": 0})
        result = build_summary(
            target_domain="views",
            apply_outcome="success",
            before_snapshot={},
            after_audit=audit("FAIL", {"views": 0, "cards": 1, "schema": 0, "governance": 0, "other": 0}),
        )
        self.assertEqual(result["repair_verdict"], "FAIL")
        self.assertIn("cards", result["unrelated_regressions"])

    @patch("scripts.project_repair_evidence.audit_from_snapshot")
    def test_target_domain_must_be_cleared(self, before_mock) -> None:
        before_mock.return_value = audit("FAIL", {"views": 2, "cards": 0, "schema": 0, "governance": 0, "other": 0})
        result = build_summary(
            target_domain="views",
            apply_outcome="success",
            before_snapshot={},
            after_audit=audit("FAIL", {"views": 1, "cards": 0, "schema": 0, "governance": 0, "other": 0}),
        )
        self.assertEqual(result["repair_verdict"], "FAIL")

    @patch("scripts.project_repair_evidence.audit_from_snapshot")
    def test_apply_failure_blocks_repair_pass_even_when_target_is_clean(self, before_mock) -> None:
        before_mock.return_value = audit("FAIL", {"views": 1, "cards": 0, "schema": 0, "governance": 0, "other": 0})
        result = build_summary(
            target_domain="views",
            apply_outcome="failure",
            before_snapshot={},
            after_audit=audit("PASS", {"views": 0, "cards": 0, "schema": 0, "governance": 0, "other": 0}),
        )
        self.assertEqual(result["repair_verdict"], "FAIL")

    def test_invalid_target_domain_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unsupported target_domain"):
            build_summary(target_domain="other", apply_outcome="success", before_snapshot={}, after_audit=audit("PASS", {}))


if __name__ == "__main__":
    unittest.main()
