from __future__ import annotations

import unittest

from scripts.project_views_reconcile import (
    build_create_input,
    build_update_input,
    canonical_views,
    layout_capabilities,
    legacy_names,
    preflight,
    staged_name,
)


POLICY = {
    "layout_capabilities": {
        "TABLE_LAYOUT": {"visible_fields": True, "filter": True},
        "BOARD_LAYOUT": {"visible_fields": True, "filter": True},
        "ROADMAP_LAYOUT": {"visible_fields": False, "filter": True},
    },
    "views": [
        {"name": "00 — Dashboard", "layout": "TABLE_LAYOUT", "filter": ""},
        {"name": "01 — Queue", "layout": "BOARD_LAYOUT", "filter": "is:open"},
        {"name": "02 — Active Work", "layout": "BOARD_LAYOUT", "filter": 'is:open {status}:"В работе"'},
        {"name": "03 — QA Gate", "layout": "TABLE_LAYOUT", "filter": 'is:open {status}:"Проверка QA"'},
        {"name": "04 — Release Flow", "layout": "BOARD_LAYOUT", "filter": "is:pr"},
        {"name": "05 — Roadmap", "layout": "ROADMAP_LAYOUT", "filter": "is:open"},
        {"name": "06 — Blocked / Parking", "layout": "TABLE_LAYOUT", "filter": 'is:open {status}:"Заблокировано"'},
        {"name": "07 — Agent KPI", "layout": "TABLE_LAYOUT", "filter": "has:Исполнитель"},
    ],
    "legacy_views": ["00 — Все задачи", "01 — Готово к работе", "02 — В работе", "03 — Проверка", "04 — Заблокировано"],
}


def live_view(name: str, layout: str, filter_value: str, view_id: str) -> dict[str, str]:
    return {"id": view_id, "name": name, "layout": layout, "filter": filter_value}


class ProjectViewsReconcileTests(unittest.TestCase):
    def setUp(self) -> None:
        self.capabilities = layout_capabilities(POLICY)
        self.expected = canonical_views(POLICY, "Status")
        self.fields = ["TITLE", "STATUS", "PRIORITY"]

    def test_roadmap_never_receives_visible_fields(self) -> None:
        roadmap = next(view for view in self.expected if view["layout"] == "ROADMAP_LAYOUT")
        create_input = build_create_input("PROJECT", roadmap, self.fields, self.capabilities)
        update_input = build_update_input("ROADMAP", roadmap, self.fields, self.capabilities)
        self.assertNotIn("configuration", create_input)
        self.assertNotIn("configuration", update_input)
        self.assertEqual(update_input["filter"], "is:open")

    def test_table_and_board_keep_visible_fields(self) -> None:
        for layout in ("TABLE_LAYOUT", "BOARD_LAYOUT"):
            view = next(view for view in self.expected if view["layout"] == layout)
            self.assertEqual(build_create_input("PROJECT", view, self.fields, self.capabilities)["configuration"]["visibleFieldIds"], self.fields)

    def test_capability_matrix_drives_behavior_without_layout_special_case(self) -> None:
        capabilities = {"CUSTOM_LAYOUT": {"visible_fields": False, "filter": False}}
        view = {"name": "Custom", "layout": "CUSTOM_LAYOUT", "filter": "is:open"}
        self.assertNotIn("configuration", build_create_input("PROJECT", view, self.fields, capabilities))
        self.assertEqual(build_update_input("VIEW", view, self.fields, capabilities), {"viewId": "VIEW"})

    def test_policy_rejects_layout_without_capability_contract(self) -> None:
        policy = {"layout_capabilities": {"TABLE_LAYOUT": {"visible_fields": True, "filter": True}}, "views": [{"name": "Roadmap", "layout": "ROADMAP_LAYOUT", "filter": ""}]}
        with self.assertRaisesRegex(RuntimeError, "capability contract"):
            layout_capabilities(policy)

    def test_policy_rejects_non_boolean_capability(self) -> None:
        policy = {"layout_capabilities": {"TABLE_LAYOUT": {"visible_fields": "yes", "filter": True}}, "views": [{"name": "Dashboard", "layout": "TABLE_LAYOUT", "filter": ""}]}
        with self.assertRaisesRegex(RuntimeError, "boolean"):
            layout_capabilities(policy)

    def test_new_views_use_staging_name_then_single_finalize_update(self) -> None:
        roadmap = next(view for view in self.expected if view["name"] == "05 — Roadmap")
        create_input = build_create_input("PROJECT", roadmap, self.fields, self.capabilities, name=staged_name(roadmap["name"]))
        update_input = build_update_input("VIEW", roadmap, self.fields, self.capabilities, finalize_name=roadmap["name"])
        self.assertEqual(create_input["name"], staged_name("05 — Roadmap"))
        self.assertEqual(update_input["name"], "05 — Roadmap")
        self.assertEqual(update_input["filter"], "is:open")

    def test_partial_live_state_from_failed_pr153_run_is_recoverable(self) -> None:
        actual = [
            live_view("00 — Все задачи", "TABLE_LAYOUT", "is:open", "OLD0"),
            live_view("01 — Готово к работе", "TABLE_LAYOUT", 'is:open Status:"Готово к работе" -Исполнение:"Заблокировано"', "OLD1"),
            live_view("02 — В работе", "BOARD_LAYOUT", 'is:open Status:"В работе"', "OLD2"),
            live_view("03 — Проверка", "BOARD_LAYOUT", 'is:open Status:"Проверка QA"', "OLD3"),
            live_view("04 — Заблокировано", "TABLE_LAYOUT", 'is:open Status:"Заблокировано"', "OLD4"),
        ]
        actual.extend(live_view(view["name"], view["layout"], view["filter"], f"NEW{i}") for i, view in enumerate(self.expected[:5]))
        pending = preflight(actual, self.expected, legacy_names(POLICY))
        self.assertEqual([view["name"] for view in pending], ["05 — Roadmap", "06 — Blocked / Parking", "07 — Agent KPI"])

    def test_interrupted_create_before_update_is_recoverable(self) -> None:
        actual = [live_view(view["name"], view["layout"], view["filter"], f"V{i}") for i, view in enumerate(self.expected[:5])]
        roadmap = self.expected[5]
        actual.append(live_view(staged_name(roadmap["name"]), roadmap["layout"], "", "STAGED5"))
        pending = preflight(actual, self.expected, legacy_names(POLICY))
        by_name = {entry["name"]: entry for entry in pending}
        self.assertEqual(by_name["05 — Roadmap"]["_staged_id"], "STAGED5")

    def test_interrupted_after_filter_before_finalize_is_recoverable(self) -> None:
        actual = [live_view(view["name"], view["layout"], view["filter"], f"V{i}") for i, view in enumerate(self.expected[:5])]
        blocked = self.expected[6]
        actual.append(live_view(staged_name(blocked["name"]), blocked["layout"], blocked["filter"], "STAGED6"))
        recovered = next(entry for entry in preflight(actual, self.expected, legacy_names(POLICY)) if entry["name"] == blocked["name"])
        self.assertEqual(recovered["_staged_id"], "STAGED6")

    def test_staging_drift_outside_recoverable_states_fails_closed(self) -> None:
        actual = [live_view(view["name"], view["layout"], view["filter"], f"V{i}") for i, view in enumerate(self.expected[:5])]
        roadmap = self.expected[5]
        actual.append(live_view(staged_name(roadmap["name"]), roadmap["layout"], "is:closed", "STAGED5"))
        with self.assertRaisesRegex(RuntimeError, "recoverable контракт"):
            preflight(actual, self.expected, legacy_names(POLICY))

    def test_canonical_and_staging_copy_together_fail_closed(self) -> None:
        actual = [live_view(view["name"], view["layout"], view["filter"], f"V{i}") for i, view in enumerate(self.expected)]
        roadmap = self.expected[5]
        actual.append(live_view(staged_name(roadmap["name"]), roadmap["layout"], "", "STAGED5"))
        with self.assertRaisesRegex(RuntimeError, "canonical и staging"):
            preflight(actual, self.expected, legacy_names(POLICY))

    def test_unknown_view_stops_before_mutation_plan(self) -> None:
        actual = [live_view(view["name"], view["layout"], view["filter"], f"V{i}") for i, view in enumerate(self.expected)]
        actual.append(live_view("Пользовательская вкладка", "TABLE_LAYOUT", "", "X"))
        with self.assertRaisesRegex(RuntimeError, "неизвестные"):
            preflight(actual, self.expected, legacy_names(POLICY))

    def test_existing_canonical_drift_stops_before_mutation_plan(self) -> None:
        actual = [live_view(view["name"], view["layout"], view["filter"], f"V{i}") for i, view in enumerate(self.expected)]
        actual[5]["filter"] = "is:closed"
        with self.assertRaisesRegex(RuntimeError, "нарушает контракт"):
            preflight(actual, self.expected, legacy_names(POLICY))


if __name__ == "__main__":
    unittest.main()
