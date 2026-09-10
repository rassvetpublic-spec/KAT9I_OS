import importlib.util
import sys
from pathlib import Path
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "g0_control_plane_audit.py"
WORKFLOW = ROOT / ".github" / "workflows" / "g0-control-plane-audit.yml"
SPEC = importlib.util.spec_from_file_location("g0audit", SCRIPT)
MOD = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MOD
assert SPEC.loader
SPEC.loader.exec_module(MOD)


def select(name, options):
    return {"__typename": "ProjectV2SingleSelectField", "name": name, "options": [{"name": x} for x in options]}


def item(url, title, values):
    return {
        "id": url,
        "content": {"url": url, "title": title, "state": "OPEN"},
        "fieldValues": {"nodes": [
            {"__typename": "ProjectV2ItemFieldSingleSelectValue", "name": value, "field": {"name": key}}
            for key, value in values.items()
        ], "pageInfo": {"hasNextPage": False}},
    }


def good_snapshot():
    fields = [select("Status", MOD.EXPECTED_SELECTS["Статус"])]
    fields += [select(name, options) for name, options in MOD.EXPECTED_SELECTS.items() if name != "Статус"]
    fields.append({"__typename": "ProjectV2IterationField", "name": "Итерация", "configuration": {"duration": 3, "startDay": 1}})
    status_name = "Status"
    views = [
        {"name": "00 — Все задачи", "layout": "TABLE_LAYOUT", "filter": "is:open"},
        {"name": "01 — Готово к работе", "layout": "TABLE_LAYOUT", "filter": f'is:open {status_name}:"Готово к работе" -Исполнение:"Заблокировано"'},
        {"name": "02 — В работе", "layout": "BOARD_LAYOUT", "filter": f'is:open {status_name}:"В работе"'},
        {"name": "03 — Проверка", "layout": "BOARD_LAYOUT", "filter": f'is:open {status_name}:"Проверка QA"'},
        {"name": "04 — Заблокировано", "layout": "TABLE_LAYOUT", "filter": f'is:open {status_name}:"Заблокировано"'},
    ]
    gate = "https://github.com/rassvetpublic-spec/KAT9I_OS/issues/62"
    p0 = "https://github.com/rassvetpublic-spec/KAT9I_OS/issues/1"
    items = [
        item(gate, "[GATE][P0] Gate", {"Приоритет": "P0", "Этап": "G0 — Порядок проекта и задач", "Исполнение": "Освобождено"}),
        item(p0, "[G0][P0] Audit", {"Приоритет": "P0", "Этап": "G0 — Порядок проекта и задач", "Исполнение": "Активно", "Исполнитель": "ChatGPT", "Проверяющий": "AGY", "Status": "В работе"}),
    ]
    ruleset = {
        "id": MOD.RULESET_ID,
        "name": "main-protection",
        "enforcement": "active",
        "conditions": {"ref_name": {"include": ["~DEFAULT_BRANCH"], "exclude": []}},
        "bypass_actors": [],
        "current_user_can_bypass": "never",
        "rules": [
            {"type": "deletion"},
            {"type": "non_fast_forward"},
            {"type": "pull_request", "parameters": {"required_review_thread_resolution": True}},
            {"type": "required_status_checks", "parameters": {"strict_required_status_checks_policy": True, "required_status_checks": [{"context": MOD.QUALITY_CONTEXT}]}},
        ],
    }
    milestones = [{"title": x} for x in sorted(MOD.EXPECTED_MILESTONES)]
    return {
        "project": {
            "title": MOD.EXPECTED_PROJECT_TITLE,
            "repository": "rassvetpublic-spec/KAT9I_OS",
            "repositories": {"nodes": [{"nameWithOwner": "rassvetpublic-spec/KAT9I_OS"}]},
            "fields": {"nodes": fields},
            "views": {"nodes": views},
            "items": items,
        },
        "ruleset": ruleset,
        "milestones": milestones,
        "open_work": [{"url": p0, "title": "[G0][P0] Audit", "state": "OPEN"}],
    }


class AuditTests(unittest.TestCase):
    def codes(self, snap):
        return {f.code for f in MOD.validate(snap)}

    def test_good_snapshot_passes(self):
        self.assertEqual([], MOD.validate(good_snapshot()))

    def test_view_drift_and_extra_view_fail(self):
        snap = good_snapshot()
        snap["project"]["views"]["nodes"][3]["filter"] = 'is:open Status:"Проверка качества"'
        snap["project"]["views"]["nodes"].append({"name": "лишний", "layout": "TABLE_LAYOUT", "filter": ""})
        codes = self.codes(snap)
        self.assertIn("VIEW_FILTER", codes)
        self.assertIn("VIEW_COUNT", codes)

    def test_iteration_drift_fails(self):
        snap = good_snapshot()
        for field in snap["project"]["fields"]["nodes"]:
            if field.get("name") == "Итерация":
                field["configuration"]["duration"] = 7
        self.assertIn("ITERATION_DURATION", self.codes(snap))

    def test_field_options_drift_fails(self):
        snap = good_snapshot()
        field = next(f for f in snap["project"]["fields"]["nodes"] if f.get("name") == "Приоритет")
        field["options"].append({"name": "P4"})
        self.assertIn("FIELD_OPTIONS", self.codes(snap))

    def test_open_p01_requires_project_classification_and_exact_priority(self):
        snap = good_snapshot()
        snap["project"]["items"] = [x for x in snap["project"]["items"] if x["content"]["url"].endswith("/62")]
        self.assertIn("OPEN_P01_MISSING", self.codes(snap))

        snap = good_snapshot()
        active = snap["project"]["items"][1]
        for node in active["fieldValues"]["nodes"]:
            if node["field"]["name"] == "Приоритет":
                node["name"] = "P1"
            if node["field"]["name"] == "Этап":
                node["name"] = ""
        codes = self.codes(snap)
        self.assertIn("OPEN_P01_PRIORITY", codes)
        self.assertIn("OPEN_P01_STAGE", codes)

    def test_active_item_requires_worker_and_qa(self):
        snap = good_snapshot()
        active = snap["project"]["items"][1]
        active["fieldValues"]["nodes"] = [n for n in active["fieldValues"]["nodes"] if n["field"]["name"] != "Проверяющий"]
        self.assertIn("ACTIVE_QA", self.codes(snap))

    def test_ruleset_bypass_non_strict_or_wrong_target_fails(self):
        snap = good_snapshot()
        snap["ruleset"]["bypass_actors"] = [{"actor_id": 1}]
        snap["ruleset"]["conditions"]["ref_name"]["include"] = ["refs/heads/main"]
        for rule in snap["ruleset"]["rules"]:
            if rule["type"] == "required_status_checks":
                rule["parameters"]["strict_required_status_checks_policy"] = False
                rule["parameters"]["required_status_checks"] = []
        codes = self.codes(snap)
        self.assertIn("RULESET_BYPASS", codes)
        self.assertIn("RULESET_TARGET", codes)
        self.assertIn("RULESET_STRICT", codes)
        self.assertIn("RULESET_QUALITY", codes)

    def test_milestone_gap_fails(self):
        snap = good_snapshot()
        snap["milestones"] = [m for m in snap["milestones"] if m["title"] != "v1.0"]
        self.assertIn("MILESTONE", self.codes(snap))

    def test_issue_62_must_be_in_project(self):
        snap = good_snapshot()
        snap["project"]["items"] = [x for x in snap["project"]["items"] if not x["content"]["url"].endswith("/62")]
        self.assertIn("GATE_62", self.codes(snap))

    def test_graphql_omits_null_cursor(self):
        with mock.patch.object(MOD, "run_json", return_value={}) as run:
            MOD.gh_graphql("query X", {"login": "rassvetpublic-spec", "number": 2, "after": None})
        command = run.call_args.args[0]
        self.assertNotIn("after=None", command)
        self.assertFalse(any(str(x).startswith("after=") for x in command))

    def test_workflow_is_owner_issue_comment_only_and_default_branch_trusted(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("issue_comment:", text)
        self.assertNotIn("pull_request:", text)
        self.assertIn("github.event.issue.number == 1", text)
        self.assertIn("github.event.comment.author_association == 'OWNER'", text)
        self.assertIn("github.event.repository.default_branch", text)
        self.assertIn("KAT9I_PROJECT_TOKEN", text)
        self.assertIn("secrets.GITHUB_TOKEN", text)


if __name__ == "__main__":
    unittest.main()
