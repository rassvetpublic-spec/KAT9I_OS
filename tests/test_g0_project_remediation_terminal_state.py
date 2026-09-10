import unittest
from types import SimpleNamespace
from unittest.mock import patch

from scripts import g0_project_remediation as core
from scripts import g0_project_remediation_safe as safe


def controlled_item(state, kind="PullRequest", number=97):
    noun = "pull" if kind == "PullRequest" else "issues"
    return {
        "id": f"ITEM_{number}",
        "content": {
            "__typename": kind,
            "url": f"https://github.com/rassvetpublic-spec/KAT9I_OS/{noun}/{number}",
            "number": number,
            "title": "[P3] historical controlled item",
            "state": state,
        },
        "fieldValues": {
            "nodes": [
                {
                    "__typename": "ProjectV2ItemFieldSingleSelectValue",
                    "name": "На проверке",
                    "field": {"name": "Исполнение"},
                }
            ]
        },
    }


def snapshot(item):
    return {"project": {"id": "PVT_2", "items": [item]}}


class TerminalStatePlannerTests(unittest.TestCase):
    def test_merged_pr_is_normalized_only_in_planner_copy(self):
        item = controlled_item("MERGED")
        raw = snapshot(item)
        planned, normalized = safe.planner_snapshot(raw)
        self.assertEqual("MERGED", raw["project"]["items"][0]["content"]["state"])
        self.assertEqual("CLOSED", planned["project"]["items"][0]["content"]["state"])
        self.assertEqual([item["content"]["url"]], normalized)

    def test_closed_and_open_pr_states_are_preserved(self):
        for state in ("OPEN", "CLOSED"):
            with self.subTest(state=state):
                raw = snapshot(controlled_item(state))
                planned, normalized = safe.planner_snapshot(raw)
                self.assertEqual(state, planned["project"]["items"][0]["content"]["state"])
                self.assertEqual([], normalized)

    def test_unknown_controlled_pr_state_is_fail_closed(self):
        with self.assertRaisesRegex(core.RemediationError, "unsupported state"):
            safe.planner_snapshot(snapshot(controlled_item("UNKNOWN")))

    def test_unknown_controlled_issue_state_is_fail_closed(self):
        with self.assertRaisesRegex(core.RemediationError, "unsupported state"):
            safe.planner_snapshot(snapshot(controlled_item("MERGED", kind="Issue")))

    def test_uncontrolled_unknown_content_is_not_reclassified(self):
        raw = snapshot(controlled_item("UNKNOWN"))
        raw["project"]["items"][0]["fieldValues"] = {"nodes": []}
        planned, normalized = safe.planner_snapshot(raw)
        self.assertEqual("UNKNOWN", planned["project"]["items"][0]["content"]["state"])
        self.assertEqual([], normalized)

    def test_normalized_merged_pr_still_requires_rest_merged_at_for_done(self):
        item = controlled_item("MERGED")
        planned, _ = safe.planner_snapshot(snapshot(item))
        with patch.object(core, "gh_json", return_value={"merged_at": "2026-09-10T07:49:58Z"}) as rest:
            outcomes = core.collect_closed_outcomes(planned)
        self.assertEqual("DONE", outcomes[item["content"]["url"]])
        rest.assert_called_once()
        self.assertIn("pulls/97", rest.call_args.args[0][-1])

    def test_closed_unmerged_pr_is_blocked_by_rest_outcome(self):
        item = controlled_item("CLOSED", number=196)
        planned, _ = safe.planner_snapshot(snapshot(item))
        with patch.object(core, "gh_json", return_value={"merged_at": None}) as rest:
            outcomes = core.collect_closed_outcomes(planned)
        self.assertEqual("BLOCKED", outcomes[item["content"]["url"]])
        rest.assert_called_once()
        self.assertIn("pulls/196", rest.call_args.args[0][-1])

    def test_safe_pipeline_passes_normalized_terminal_snapshot_to_core_planner(self):
        item = controlled_item("MERGED")
        raw = snapshot(item)
        url = item["content"]["url"]
        plan = SimpleNamespace(
            worker_field_update=None,
            delete_views=[],
            item_edits=[],
            missing_open_items=[],
            jsonable=lambda: {
                "worker_field_update": None,
                "delete_views": [],
                "item_edits": [],
                "missing_open_items": [],
            },
        )

        def outcomes_side_effect(planned):
            self.assertEqual("CLOSED", planned["project"]["items"][0]["content"]["state"])
            return {url: "DONE"}

        def plan_side_effect(planned, outcomes):
            self.assertEqual("CLOSED", planned["project"]["items"][0]["content"]["state"])
            self.assertEqual({url: "DONE"}, outcomes)
            return plan

        with patch.object(safe.core, "collect_live", return_value=raw), \
             patch.object(safe.core, "worker_option_plan", return_value=None), \
             patch.object(safe.core, "view_delete_plan", return_value=[]), \
             patch.object(safe.core, "find_select_field", return_value={}), \
             patch.object(safe, "assert_no_canonical_self_qa"), \
             patch.object(safe.core, "missing_open_items", return_value=[]), \
             patch.object(safe.core, "collect_closed_outcomes", side_effect=outcomes_side_effect), \
             patch.object(safe.core, "build_plan", side_effect=plan_side_effect), \
             patch.object(safe.core, "audit_validate", return_value=[]):
            report = safe.safe_remediation(
                safe.core.OWNER,
                safe.core.REPOSITORY,
                safe.core.PROJECT_NUMBER,
                apply=False,
            )

        self.assertEqual([url], report["terminal_state_normalizations"])
        self.assertEqual("MERGED", raw["project"]["items"][0]["content"]["state"])


if __name__ == "__main__":
    unittest.main()
