import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "config" / "project_bootstrap_standard.json"
BOOTSTRAP = ROOT / "scripts" / "bootstrap_project.ps1"
PROJECT = ROOT / "scripts" / "configure_standard_project.ps1"
VIEWS = ROOT / "config" / "project_views.json"


class StandardProjectBootstrapTests(unittest.TestCase):
    def test_manifest_safety_contract(self):
        data = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(data["schema"], "KAT9I_PROJECT_BOOTSTRAP/1")
        self.assertEqual(data["repository"]["default_branch"], "main")
        self.assertFalse(data["repository"]["allow_auto_merge"])
        self.assertEqual(data["safety"]["owner_gate"], "mtd")
        self.assertFalse(data["safety"]["auto_merge"])
        self.assertEqual(data["safety"]["unknown_labels"], "PRESERVE")
        self.assertTrue(data["capabilities"]["never_log_secret_values"])
        self.assertIn("KAT9I_PROJECT_TOKEN", data["capabilities"]["optional_secret_names"])

    def test_templates_are_unique_and_portable(self):
        data = json.loads(MANIFEST.read_text(encoding="utf-8"))
        targets = [item["target"] for item in data["templates"]]
        self.assertEqual(len(targets), len(set(targets)))
        for item in data["templates"]:
            source = ROOT / item["source"]
            self.assertTrue(source.is_file(), item["source"])
            text = source.read_text(encoding="utf-8")
            self.assertNotIn("C:\\GIT\\KAT9I_OS", text)

    def test_eight_canonical_views_remain_the_standard(self):
        data = json.loads(VIEWS.read_text(encoding="utf-8"))
        names = [view["name"] for view in data["views"]]
        self.assertEqual(
            names,
            [
                "00 — Dashboard",
                "01 — Queue",
                "02 — Active Work",
                "03 — QA Gate",
                "04 — Release Flow",
                "05 — Roadmap",
                "06 — Blocked / Parking",
                "07 — Agent KPI",
            ],
        )

    def test_bootstrap_has_read_only_status_and_no_merge_authority(self):
        text = BOOTSTRAP.read_text(encoding="utf-8")
        self.assertIn("ValidateSet('Install','Status','Repair')", text)
        self.assertIn("$ReadOnly=($Mode -eq 'Status')", text)
        self.assertIn("secret_values_included=$false", text)
        self.assertIn("owner_gate='mtd'", text)
        lowered = text.lower()
        self.assertNotIn("gh pr merge", lowered)
        self.assertNotIn("enable-auto-merge", lowered)
        self.assertNotIn("merge_pull_request", lowered)

    def test_project_configurator_keeps_core_fields_and_fail_closed_guards(self):
        text = PROJECT.read_text(encoding="utf-8")
        for name in (
            "Статус",
            "Этап",
            "Приоритет",
            "Тип",
            "Область",
            "Размер",
            "Итерация",
            "Исполнитель",
            "Проверяющий",
            "Исполнение",
            "Цель",
            "Риск",
            "Доказательство",
        ):
            self.assertIn(name, text)
        self.assertIn("unknown Project views", text)
        self.assertIn("will not replace option IDs", text)
        self.assertIn("duration=3", text)


if __name__ == "__main__":
    unittest.main()
