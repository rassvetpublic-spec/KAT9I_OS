from __future__ import annotations

import unittest
from pathlib import Path

from scripts.project_audit_domains import enrich, finding_domain

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = (
    ROOT / ".github" / "workflows" / "g0-control-plane-audit.yml",
    ROOT / ".github" / "workflows" / "project-views-migrate.yml",
    ROOT / ".github" / "workflows" / "project-cards-classification.yml",
)


class ProjectAuditDomainsTests(unittest.TestCase):
    def test_known_codes_are_split_by_domain(self) -> None:
        self.assertEqual(finding_domain("VIEW_COUNT"), "views")
        self.assertEqual(finding_domain("OPEN_P01_STAGE"), "cards")
        self.assertEqual(finding_domain("CONTROLLED_QA"), "cards")
        self.assertEqual(finding_domain("FIELD_OPTIONS"), "schema")
        self.assertEqual(finding_domain("ITERATION_DURATION"), "schema")
        self.assertEqual(finding_domain("RULESET_STRICT"), "governance")
        self.assertEqual(finding_domain("MILESTONE"), "governance")

    def test_enrich_preserves_original_findings_and_adds_counts(self) -> None:
        summary = {
            "schema": "KAT9I_G0_AUDIT/1",
            "verdict": "FAIL",
            "finding_count": 4,
            "findings": [
                {"code": "VIEW_COUNT", "message": "views"},
                {"code": "OPEN_P01_STAGE", "message": "card"},
                {"code": "FIELD_OPTIONS", "message": "schema"},
                {"code": "RULESET_STRICT", "message": "rules"},
            ],
        }
        result = enrich(summary)
        self.assertEqual(result["findings"], summary["findings"])
        self.assertEqual(result["domain_counts"], {"views": 1, "cards": 1, "schema": 1, "governance": 1, "other": 0})

    def test_pr153_failure_shape_becomes_four_view_and_twelve_card_findings(self) -> None:
        findings = [
            {"code": "VIEW_COUNT", "message": "10 views"},
            {"code": "VIEW_MISSING", "message": "05"},
            {"code": "VIEW_MISSING", "message": "06"},
            {"code": "VIEW_MISSING", "message": "07"},
        ]
        for number in (145, 146, 147, 148, 150, 154):
            findings.append({"code": "OPEN_P01_PRIORITY", "message": f"#{number}"})
            findings.append({"code": "OPEN_P01_STAGE", "message": f"#{number}"})
        result = enrich({"schema": "KAT9I_G0_AUDIT/1", "verdict": "FAIL", "finding_count": 16, "findings": findings})
        self.assertEqual(result["domain_counts"]["views"], 4)
        self.assertEqual(result["domain_counts"]["cards"], 12)

    def test_unknown_code_is_visible_in_other_instead_of_disappearing(self) -> None:
        result = enrich({"schema": "KAT9I_G0_AUDIT/1", "verdict": "FAIL", "finding_count": 1, "findings": [{"code": "NEW_FUTURE_CHECK", "message": "future"}]})
        self.assertEqual(result["domain_counts"]["other"], 1)
        self.assertEqual(result["findings_by_domain"]["other"][0]["code"], "NEW_FUTURE_CHECK")

    def test_mismatched_finding_count_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "finding_count"):
            enrich({"schema": "KAT9I_G0_AUDIT/1", "verdict": "FAIL", "finding_count": 2, "findings": [{"code": "VIEW_COUNT", "message": "x"}]})

    def test_all_project_audit_workflows_enrich_evidence(self) -> None:
        for workflow in WORKFLOWS:
            text = workflow.read_text(encoding="utf-8")
            with self.subTest(workflow=workflow.name):
                self.assertIn("project_audit_domains.py", text)
                self.assertIn("domain", text.lower())


if __name__ == "__main__":
    unittest.main()
