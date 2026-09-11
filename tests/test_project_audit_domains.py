from __future__ import annotations

import ast
import unittest
from pathlib import Path

from scripts.project_audit_domains import REGISTRY_SCHEMA, enrich, finding_domain, load_registry

ROOT = Path(__file__).resolve().parents[1]
AUDITOR = ROOT / "scripts" / "g0_control_plane_audit.py"
WORKFLOWS = (
    ROOT / ".github" / "workflows" / "g0-control-plane-audit.yml",
    ROOT / ".github" / "workflows" / "project-views-migrate.yml",
    ROOT / ".github" / "workflows" / "project-cards-classification.yml",
)


def current_audit_codes() -> set[str]:
    tree = ast.parse(AUDITOR.read_text(encoding="utf-8"))
    codes: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not node.args:
            continue
        if not isinstance(node.func, ast.Name) or node.func.id != "Finding":
            continue
        first = node.args[0]
        if isinstance(first, ast.Constant) and isinstance(first.value, str):
            codes.add(first.value)
    return codes


class ProjectAuditDomainsTests(unittest.TestCase):
    def test_registry_is_machine_readable_ssot(self) -> None:
        registry = load_registry()
        self.assertEqual(registry["schema"], REGISTRY_SCHEMA)
        self.assertEqual(registry["fallback"]["policy"], "UNREGISTERED_ONLY")

    def test_known_codes_are_split_by_domain(self) -> None:
        self.assertEqual(finding_domain("VIEW_COUNT"), "views")
        self.assertEqual(finding_domain("OPEN_P01_STAGE"), "cards")
        self.assertEqual(finding_domain("CONTROLLED_QA"), "cards")
        self.assertEqual(finding_domain("FIELD_OPTIONS"), "schema")
        self.assertEqual(finding_domain("ITERATION_DURATION"), "schema")
        self.assertEqual(finding_domain("RULESET_STRICT"), "governance")
        self.assertEqual(finding_domain("MILESTONE"), "governance")

    def test_every_current_auditor_code_is_explicitly_registered(self) -> None:
        codes = current_audit_codes()
        self.assertGreater(len(codes), 10)
        for code in sorted(codes):
            with self.subTest(code=code):
                self.assertIn(finding_domain(code, require_registered=True), {"views", "cards", "schema", "governance"})

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
        self.assertEqual(result["schema"], summary["schema"])
        self.assertEqual(result["verdict"], summary["verdict"])
        self.assertEqual(result["finding_count"], summary["finding_count"])
        self.assertEqual(result["findings"], summary["findings"])
        self.assertEqual(result["domain_registry_schema"], REGISTRY_SCHEMA)
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

    def test_future_unregistered_code_uses_explicit_other_fallback(self) -> None:
        result = enrich({"schema": "KAT9I_G0_AUDIT/1", "verdict": "FAIL", "finding_count": 1, "findings": [{"code": "NEW_FUTURE_CHECK", "message": "future"}]})
        self.assertEqual(result["domain_counts"]["other"], 1)
        self.assertEqual(result["findings_by_domain"]["other"][0]["code"], "NEW_FUTURE_CHECK")
        with self.assertRaisesRegex(ValueError, "отсутствует в registry"):
            finding_domain("NEW_FUTURE_CHECK", require_registered=True)

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
