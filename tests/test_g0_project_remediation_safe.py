import unittest
from dataclasses import dataclass
from types import SimpleNamespace
from unittest.mock import patch

from scripts import g0_project_remediation as core
from scripts import g0_project_remediation_safe as safe


@dataclass
class FakeFinding:
    code: str
    message: str


class SafeRemediationOrderingTests(unittest.TestCase):
    def test_missing_inventory_stops_before_any_mutation(self):
        snapshot = {"project": {"id": "PVT_1"}}
        mutation_names = (
            "apply_worker_field_update",
            "apply_delete_views",
            "apply_item_edits",
            "add_missing_items",
        )
        with patch.object(safe.core, "collect_live", return_value=snapshot), \
             patch.object(safe.core, "worker_option_plan", return_value=None), \
             patch.object(safe.core, "view_delete_plan", return_value=[]), \
             patch.object(safe.core, "find_select_field", return_value={}), \
             patch.object(safe.core, "missing_open_items", return_value=["https://github.com/rassvetpublic-spec/KAT9I_OS/issues/999"]), \
             patch.object(safe.core, mutation_names[0]) as worker_mutation, \
             patch.object(safe.core, mutation_names[1]) as view_mutation, \
             patch.object(safe.core, mutation_names[2]) as item_mutation, \
             patch.object(safe.core, mutation_names[3]) as add_mutation:
            with self.assertRaisesRegex(safe.core.RemediationError, "inventory is incomplete"):
                safe.safe_remediation(safe.core.OWNER, safe.core.REPOSITORY, safe.core.PROJECT_NUMBER, apply=True)
            worker_mutation.assert_not_called()
            view_mutation.assert_not_called()
            item_mutation.assert_not_called()
            add_mutation.assert_not_called()

    def test_semantic_preflight_failure_stops_before_any_mutation(self):
        snapshot = {"project": {"id": "PVT_1"}}
        with patch.object(safe.core, "collect_live", return_value=snapshot), \
             patch.object(safe.core, "worker_option_plan", return_value=None), \
             patch.object(safe.core, "view_delete_plan", return_value=[]), \
             patch.object(safe.core, "find_select_field", return_value={}), \
             patch.object(safe.core, "missing_open_items", return_value=[]), \
             patch.object(safe.core, "collect_closed_outcomes", return_value={}), \
             patch.object(safe.core, "build_plan", side_effect=safe.core.RemediationError("self-QA")), \
             patch.object(safe.core, "apply_worker_field_update") as worker_mutation, \
             patch.object(safe.core, "apply_delete_views") as view_mutation, \
             patch.object(safe.core, "apply_item_edits") as item_mutation:
            with self.assertRaisesRegex(safe.core.RemediationError, "self-QA"):
                safe.safe_remediation(safe.core.OWNER, safe.core.REPOSITORY, safe.core.PROJECT_NUMBER, apply=True)
            worker_mutation.assert_not_called()
            view_mutation.assert_not_called()
            item_mutation.assert_not_called()

    def test_legacy_antigravity_and_agy_are_self_qa_before_mutation(self):
        snapshot = {
            "project": {
                "items": [
                    {
                        "id": "PVTI_1",
                        "content": {
                            "state": "OPEN",
                            "title": "[G0][P0] active",
                            "url": "https://github.com/rassvetpublic-spec/KAT9I_OS/issues/1",
                        },
                    }
                ]
            }
        }
        values = {"Исполнитель": "Antigravity", "Проверяющий": "AGY"}
        with patch.object(safe.core, "item_fields", return_value=values), \
             patch.object(safe.core, "is_controlled", return_value=True):
            with self.assertRaisesRegex(safe.core.RemediationError, "canonical self-QA"):
                safe.assert_no_canonical_self_qa(snapshot)

    def test_failed_post_audit_preserves_before_plan_and_after_evidence(self):
        before = {"project": {"id": "PVT_1"}}
        after = {"project": {"id": "PVT_1"}}
        plan = SimpleNamespace(
            worker_field_update=None,
            delete_views=[],
            item_edits=[],
            missing_open_items=[],
            jsonable=lambda: {"worker_field_update": None, "delete_views": [], "item_edits": [], "missing_open_items": []},
        )
        remaining = FakeFinding("CONTROLLED_QA", "still broken")
        with patch.object(safe.core, "collect_live", side_effect=[before, after]), \
             patch.object(safe.core, "worker_option_plan", return_value=None), \
             patch.object(safe.core, "view_delete_plan", return_value=[]), \
             patch.object(safe.core, "find_select_field", return_value={}), \
             patch.object(safe, "assert_no_canonical_self_qa"), \
             patch.object(safe.core, "missing_open_items", return_value=[]), \
             patch.object(safe.core, "collect_closed_outcomes", return_value={}), \
             patch.object(safe.core, "build_plan", return_value=plan), \
             patch.object(safe.core, "audit_validate", side_effect=[[], [remaining]]), \
             patch.object(safe.core, "apply_worker_field_update"), \
             patch.object(safe.core, "apply_delete_views"), \
             patch.object(safe.core, "apply_item_edits"):
            report = safe.safe_remediation(safe.core.OWNER, safe.core.REPOSITORY, safe.core.PROJECT_NUMBER, apply=True)
        self.assertEqual("FAIL", report["verdict"])
        self.assertEqual([], report["before_audit"])
        self.assertEqual("CONTROLLED_QA", report["after_audit"][0]["code"])
        self.assertIn("Post-remediation", report["reason"])
        self.assertIn("plan", report)

    def test_workflow_uses_safe_runner(self):
        from pathlib import Path
        workflow = (
            Path(__file__).resolve().parents[1]
            / ".github"
            / "workflows"
            / "g0-project-remediation.yml"
        ).read_text(encoding="utf-8")
        self.assertIn("g0_project_remediation_safe.py --apply", workflow)
        self.assertNotIn("g0_project_remediation.py --apply", workflow)


if __name__ == "__main__":
    unittest.main()
