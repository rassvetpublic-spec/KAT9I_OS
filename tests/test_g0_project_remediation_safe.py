import unittest
from unittest.mock import patch

from scripts import g0_project_remediation as core
from scripts import g0_project_remediation_safe as safe


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
            with self.assertRaisesRegex(core.RemediationError, "inventory is incomplete"):
                safe.safe_remediation(core.OWNER, core.REPOSITORY, core.PROJECT_NUMBER, apply=True)
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
             patch.object(safe.core, "build_plan", side_effect=core.RemediationError("self-QA")), \
             patch.object(safe.core, "apply_worker_field_update") as worker_mutation, \
             patch.object(safe.core, "apply_delete_views") as view_mutation, \
             patch.object(safe.core, "apply_item_edits") as item_mutation:
            with self.assertRaisesRegex(core.RemediationError, "self-QA"):
                safe.safe_remediation(core.OWNER, core.REPOSITORY, core.PROJECT_NUMBER, apply=True)
            worker_mutation.assert_not_called()
            view_mutation.assert_not_called()
            item_mutation.assert_not_called()

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
