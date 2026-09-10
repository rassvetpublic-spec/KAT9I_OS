import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from g0_project_remediation import (  # noqa: E402
    CANONICAL_WORKERS,
    RemediationError,
    build_plan,
    derive_stage,
    missing_open_items,
    view_delete_plan,
    worker_option_plan,
)


def option(name, idx):
    return {"id": f"OPT_{idx}", "name": name}


def select_field(name, values, idx):
    return {
        "__typename": "ProjectV2SingleSelectField",
        "id": f"FIELD_{idx}",
        "name": name,
        "options": [option(value, f"{idx}_{n}") for n, value in enumerate(values)],
    }


def field_value(field, value):
    return {
        "__typename": "ProjectV2ItemFieldSingleSelectValue",
        "name": value,
        "field": {"name": field},
    }


def project_item(number, title, state="OPEN", kind="Issue", values=None):
    noun = "pull" if kind == "PullRequest" else "issues"
    url = f"https://github.com/rassvetpublic-spec/KAT9I_OS/{noun}/{number}"
    return {
        "id": f"ITEM_{number}_{kind}",
        "content": {
            "__typename": kind,
            "url": url,
            "number": number,
            "title": title,
            "state": state,
        },
        "fieldValues": {"nodes": [field_value(k, v) for k, v in (values or {}).items()]},
    }


def open_work(number, title, kind="Issue"):
    noun = "pull" if kind == "PullRequest" else "issues"
    return {
        "kind": "pr" if kind == "PullRequest" else "issue",
        "number": number,
        "title": title,
        "url": f"https://github.com/rassvetpublic-spec/KAT9I_OS/{noun}/{number}",
    }


def base_fields(worker_options=None):
    return [
        select_field("Статус", ["Входящие", "Нужно разобрать", "Готово к работе", "В работе", "Проверка QA", "Заблокировано", "Готово"], 1),
        select_field("Этап", [
            "G0 — Порядок проекта и задач",
            "G1 — ТЗ и базовая архитектура",
            "G2 — Машинные контракты",
            "G3 — Основа исполняемой системы",
            "G4 — Сквозная версия v0.1",
            "G5 — После v0.1",
        ], 2),
        select_field("Приоритет", ["P0", "P1", "P2", "P3"], 3),
        select_field("Исполнитель", worker_options or ["ChatGPT", "Antigravity", "Codex", "Человек", "Другой", "Kat9i_OS"], 4),
        select_field("Проверяющий", CANONICAL_WORKERS, 5),
        select_field("Исполнение", ["Свободно", "В очереди", "Активно", "На проверке", "Заблокировано", "Освобождено"], 6),
    ]


def snapshot(items=None, work=None, worker_options=None, extra_view="05 — Заблокировано"):
    views = [{"id": f"VIEW_{i}", "name": name} for i, name in enumerate([
        "00 — Все задачи",
        "01 — Готово к работе",
        "02 — В работе",
        "03 — Проверка",
        "04 — Заблокировано",
    ])]
    if extra_view:
        views.append({"id": "VIEW_EXTRA", "name": extra_view})
    return {
        "project": {
            "id": "PROJECT_2",
            "fields": {"nodes": base_fields(worker_options)},
            "views": {"nodes": views},
            "items": items or [],
        },
        "open_work": work or [],
    }


class G0ProjectRemediationTests(unittest.TestCase):
    def test_worker_option_migration_preserves_legacy_agy_id(self):
        snap = snapshot()
        update = worker_option_plan(snap)
        self.assertIsNotNone(update)
        names = [item["name"] for item in update["options"]]
        self.assertEqual(CANONICAL_WORKERS, names)
        old = next(o for o in base_fields()[3]["options"] if o["name"] == "Antigravity")
        agy = next(o for o in update["options"] if o["name"] == "AGY")
        self.assertEqual(old["id"], agy["id"])
        self.assertNotIn("Kat9i_OS", names)

    def test_used_kat9i_worker_option_blocks_removal(self):
        item = project_item(1, "[G0][P0] test", values={"Исполнитель": "Kat9i_OS"})
        with self.assertRaisesRegex(RemediationError, "Refusing to remove used legacy worker options"):
            worker_option_plan(snapshot(items=[item]))

    def test_unknown_worker_option_is_fail_closed(self):
        with self.assertRaisesRegex(RemediationError, "unknown options"):
            worker_option_plan(snapshot(worker_options=["ChatGPT", "Antigravity", "Codex", "Человек", "Другой", "Mystery"] ))

    def test_canonical_worker_field_is_idempotent(self):
        self.assertIsNone(worker_option_plan(snapshot(worker_options=CANONICAL_WORKERS)))

    def test_known_legacy_view_is_only_deletion_candidate(self):
        plan = view_delete_plan(snapshot())
        self.assertEqual([{"id": "VIEW_EXTRA", "name": "05 — Заблокировано"}], plan)

    def test_unknown_extra_view_is_fail_closed(self):
        with self.assertRaisesRegex(RemediationError, "unknown Project views"):
            view_delete_plan(snapshot(extra_view="99 — Мой важный экран"))

    def test_t_phases_map_to_g1(self):
        self.assertEqual("G1 — ТЗ и базовая архитектура", derive_stage("[T0][P0] registry"))
        self.assertEqual("G1 — ТЗ и базовая архитектура", derive_stage("[T1][P0] ABC"))
        self.assertEqual("G0 — Порядок проекта и задач", derive_stage("[G0][P1] queue"))

    def test_open_p0_is_classified_without_guessing(self):
        item = project_item(129, "[T0][P0] registry", values={"Статус": "Входящие", "Исполнение": "Свободно"})
        work = open_work(129, "[T0][P0] registry")
        plan = build_plan(snapshot(items=[item], work=[work]), {})
        values = {(edit.field, edit.option) for edit in plan.item_edits}
        self.assertIn(("Приоритет", "P0"), values)
        self.assertIn(("Этап", "G1 — ТЗ и базовая архитектура"), values)

    def test_open_p1_without_stage_signal_fails_instead_of_guessing(self):
        item = project_item(200, "[P1] ambiguous", values={"Статус": "Входящие", "Исполнение": "Свободно"})
        work = open_work(200, "[P1] ambiguous")
        with self.assertRaisesRegex(RemediationError, "no derivable/non-empty Этап"):
            build_plan(snapshot(items=[item], work=[work]), {})

    def test_closed_controlled_item_uses_trusted_outcome(self):
        item = project_item(
            99,
            "[P2] old",
            state="CLOSED",
            values={"Статус": "Проверка QA", "Исполнение": "На проверке"},
        )
        plan = build_plan(snapshot(items=[item]), {item["content"]["url"]: "DONE"})
        values = {(edit.field, edit.option) for edit in plan.item_edits}
        self.assertIn(("Исполнение", "Освобождено"), values)
        self.assertIn(("Статус", "Готово"), values)

    def test_open_data_only_controlled_item_is_parked(self):
        item = project_item(
            109,
            "[DATA] forensic",
            values={"Статус": "В работе", "Исполнение": "Активно"},
            kind="PullRequest",
        )
        work = open_work(109, "[DATA] forensic", kind="PullRequest")
        plan = build_plan(snapshot(items=[item], work=[work]), {})
        values = {(edit.field, edit.option) for edit in plan.item_edits}
        self.assertIn(("Исполнение", "Заблокировано"), values)
        self.assertIn(("Статус", "Заблокировано"), values)

    def test_open_controlled_non_data_without_identity_fails(self):
        item = project_item(201, "[G0][P2] active", values={"Статус": "В работе", "Исполнение": "Активно"})
        work = open_work(201, "[G0][P2] active")
        with self.assertRaisesRegex(RemediationError, "refusing to guess"):
            build_plan(snapshot(items=[item], work=[work]), {})

    def test_missing_open_work_is_reported_before_edits(self):
        work = open_work(135, "[G0][P0] epoch")
        snap = snapshot(items=[], work=[work])
        self.assertEqual([work["url"]], missing_open_items(snap))
        plan = build_plan(snap, {})
        self.assertEqual([work["url"]], plan.missing_open_items)
        self.assertEqual([], plan.item_edits)

    def test_project_queue_concurrency_is_per_item_not_global(self):
        text = (ROOT / ".github" / "workflows" / "project-queue-sync.yml").read_text(encoding="utf-8")
        self.assertNotIn("group: kat9i-project-queue\n", text)
        self.assertIn("github.event.issue.number", text)
        self.assertIn("github.event.pull_request.number", text)
        self.assertIn("inputs.url", text)
        self.assertIn("cancel-in-progress: false", text)

    def test_remediation_workflow_is_owner_only_and_default_branch_trusted(self):
        text = (ROOT / ".github" / "workflows" / "g0-project-remediation.yml").read_text(encoding="utf-8")
        self.assertIn("github.event.issue.number == 134", text)
        self.assertIn("author_association == 'OWNER'", text)
        self.assertIn("github.event.repository.default_branch", text)
        self.assertIn("CONTROL_COMMENT", text)
        self.assertIn("first_line", text)
        self.assertIn("test \"$first_line\" = 'KAT9I-CONTROL/1 | G0-REMEDIATE'", text)
        self.assertIn("KAT9I_PROJECT_TOKEN", text)
        self.assertIn("g0_project_remediation_safe.py --apply", text)
        self.assertNotIn("g0_project_remediation.py --apply", text)


if __name__ == "__main__":
    unittest.main()
