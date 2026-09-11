from __future__ import annotations

import unittest

from scripts.project_card_classification_reconcile import ClassificationError, build_plan, derive_priority, derive_stage

POLICY = {
    "version": 1,
    "priority_pattern": r"\[(P[01])\]",
    "stage_by_gate": {
        "G0": "G0 — Порядок проекта и задач",
        "G1": "G1 — ТЗ и базовая архитектура",
        "G2": "G2 — Машинные контракты",
        "G3": "G3 — Основа исполняемой системы",
        "G4": "G4 — Сквозная версия v0.1",
        "G5": "G5 — После v0.1",
    },
    "stage_by_tag": {
        "ROADMAP": "G5 — После v0.1",
        "PROCESS": "G0 — Порядок проекта и задач",
        "OBSERVABILITY": "G0 — Порядок проекта и задач",
        "PROJECT": "G0 — Порядок проекта и задач",
        "DOCS": "G0 — Порядок проекта и задач",
        "HARDENING": "G0 — Порядок проекта и задач",
    },
}


def select_field(name: str, field_id: str, options: list[str]) -> dict:
    return {"__typename": "ProjectV2SingleSelectField", "id": field_id, "name": name, "options": [{"id": f"{field_id}-{i}", "name": v} for i, v in enumerate(options)]}


def item(url: str, item_id: str, priority: str | None = None, stage: str | None = None) -> dict:
    nodes = []
    if priority:
        nodes.append({"__typename": "ProjectV2ItemFieldSingleSelectValue", "name": priority, "field": {"name": "Приоритет"}})
    if stage:
        nodes.append({"__typename": "ProjectV2ItemFieldSingleSelectValue", "name": stage, "field": {"name": "Этап"}})
    return {"id": item_id, "content": {"url": url, "state": "OPEN", "title": ""}, "fieldValues": {"nodes": nodes}}


def snapshot(work: list[dict], items: list[dict]) -> dict:
    return {
        "project": {
            "fields": {"nodes": [select_field("Приоритет", "FP", ["P0", "P1", "P2", "P3"]), select_field("Этап", "FS", list(POLICY["stage_by_gate"].values()))]},
            "items": items,
        },
        "open_work": work,
    }


class ProjectCardClassificationTests(unittest.TestCase):
    def test_priority_and_stage_from_gate_win(self) -> None:
        title = "[G3][P0][DOCS] test"
        self.assertEqual(derive_priority(title, POLICY), "P0")
        self.assertEqual(derive_stage(title, POLICY), "G3 — Основа исполняемой системы")

    def test_stage_fallback_tags_are_ssot_driven(self) -> None:
        self.assertEqual(derive_stage("[ROADMAP][P0] future", POLICY), "G5 — После v0.1")
        for tag in ("PROCESS", "OBSERVABILITY", "PROJECT", "DOCS", "HARDENING"):
            self.assertEqual(derive_stage(f"[P1][{tag}] test", POLICY), "G0 — Порядок проекта и задач")

    def test_live_drift_from_run_34580863381_produces_exactly_12_bounded_edits(self) -> None:
        titles = {
            145: "[G0][P1][HARDENING] Pre-validate QA result envelope до публикации PR review",
            146: "[ROADMAP][P0] Следующий цикл развития KAT9I_OS после T0",
            147: "[P1][PROCESS] Chat-to-GitHub Context Bridge: materialize decisions into SSoT",
            148: "[P1][OBSERVABILITY] Continuous Project Drift Detector",
            150: "[P1][PROJECT] GitHub Projects UX: Views, Board and Card Design",
            154: "[P0][DOCS] Сохранить остаточный операционный контекст чата",
        }
        work, items = [], []
        for number, title in titles.items():
            kind = "pull" if number == 154 else "issues"
            url = f"https://github.com/rassvetpublic-spec/KAT9I_OS/{kind}/{number}"
            work.append({"url": url, "title": title, "state": "OPEN"})
            items.append(item(url, f"ITEM-{number}"))
        plan = build_plan(snapshot(work, items), POLICY)
        self.assertEqual(len(plan), 12)
        self.assertEqual({edit.field for edit in plan}, {"Приоритет", "Этап"})
        self.assertEqual({edit.url for edit in plan}, {entry["url"] for entry in work})

    def test_already_classified_card_is_idempotent(self) -> None:
        url = "https://github.com/rassvetpublic-spec/KAT9I_OS/issues/145"
        work = [{"url": url, "title": "[G0][P1][HARDENING] test", "state": "OPEN"}]
        items = [item(url, "ITEM", "P1", "G0 — Порядок проекта и задач")]
        self.assertEqual(build_plan(snapshot(work, items), POLICY), [])

    def test_unknown_stage_fails_before_mutation_plan(self) -> None:
        url = "https://github.com/rassvetpublic-spec/KAT9I_OS/issues/999"
        work = [{"url": url, "title": "[P1][UNKNOWN] test", "state": "OPEN"}]
        with self.assertRaisesRegex(ClassificationError, "не определён Этап"):
            build_plan(snapshot(work, [item(url, "ITEM")]), POLICY)

    def test_missing_project_card_fails_closed(self) -> None:
        url = "https://github.com/rassvetpublic-spec/KAT9I_OS/issues/999"
        work = [{"url": url, "title": "[G0][P1] test", "state": "OPEN"}]
        with self.assertRaisesRegex(ClassificationError, "отсутствует в Project"):
            build_plan(snapshot(work, []), POLICY)


if __name__ == "__main__":
    unittest.main()
