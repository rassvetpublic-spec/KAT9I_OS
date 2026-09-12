import json
import shutil
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "config" / "project_bootstrap_standard.json"
BOOTSTRAP = ROOT / "scripts" / "bootstrap_project.ps1"
PROJECT = ROOT / "scripts" / "configure_standard_project.ps1"
VIEWS = ROOT / "config" / "project_bootstrap_views.json"


class StandardProjectBootstrapTests(unittest.TestCase):
    def test_manifest_safety_contract(self):
        data = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(data["schema"], "KAT9I_PROJECT_BOOTSTRAP/1")
        self.assertEqual(data["repository"]["default_branch"], "main")
        self.assertFalse(data["repository"]["allow_auto_merge"])
        self.assertEqual(data["safety"]["owner_gate"], "mtd")
        self.assertFalse(data["safety"]["auto_merge"])
        self.assertEqual(data["safety"]["unknown_labels"], "СОХРАНИТЬ")
        self.assertTrue(data["capabilities"]["never_log_secret_values"])
        self.assertIn("KAT9I_PROJECT_TOKEN", data["capabilities"]["required_secret_names"])
        self.assertIn("KAT9I_PROJECT_URL", data["capabilities"]["required_variable_names"])
        for label in data["labels"]:
            self.assertRegex(label["name"], r"[А-Яа-яЁё]")
            self.assertRegex(label["description"], r"[А-Яа-яЁё]")

    def test_known_github_default_labels_have_safe_russian_migrations(self):
        data = json.loads(MANIFEST.read_text(encoding="utf-8"))
        migrations = {
            legacy: item["name"]
            for item in data["labels"]
            for legacy in item.get("legacy_names", [])
        }
        self.assertEqual(migrations["bug"], "ошибка")
        self.assertEqual(migrations["enhancement"], "улучшение")
        self.assertEqual(migrations["documentation"], "документация")
        self.assertEqual(migrations["duplicate"], "дубликат")
        self.assertEqual(migrations["good first issue"], "первая задача")
        self.assertEqual(migrations["help wanted"], "нужна помощь")
        self.assertEqual(migrations["invalid"], "недействительно")
        self.assertEqual(migrations["question"], "вопрос")
        self.assertEqual(migrations["wontfix"], "не планируется")
        text = BOOTSTRAP.read_text(encoding="utf-8")
        self.assertIn("legacy_names", text)
        self.assertIn("Автоматическое объединение не выполняется", text)
        self.assertIn("Get-AllLabels", text)

    def test_templates_are_unique_and_portable(self):
        data = json.loads(MANIFEST.read_text(encoding="utf-8"))
        targets = [item["target"] for item in data["templates"]]
        self.assertEqual(len(targets), len(set(targets)))
        for item in data["templates"]:
            source = ROOT / item["source"]
            self.assertTrue(source.is_file(), item["source"])
            text = source.read_text(encoding="utf-8")
            self.assertNotIn("C:\\GIT\\KAT9I_OS", text)

    def test_eight_russian_canonical_views_remain_the_standard(self):
        data = json.loads(VIEWS.read_text(encoding="utf-8"))
        names = [view["name"] for view in data["views"]]
        self.assertEqual(
            names,
            [
                "00 — Обзор",
                "01 — Очередь",
                "02 — Активная работа",
                "03 — Проверка качества",
                "04 — Подготовка выпуска",
                "05 — План развития",
                "06 — Заблокировано / Парковка",
                "07 — Показатели исполнителей",
            ],
        )
        for name in names:
            self.assertRegex(name, r"[А-Яа-яЁё]")
        quality_view = next(view for view in data["views"] if view["name"] == "03 — Проверка качества")
        self.assertIn("Проверка качества", quality_view["filter"])
        self.assertNotIn("Проверка QA", quality_view["filter"])

    def test_bootstrap_has_read_only_status_and_no_merge_authority(self):
        text = BOOTSTRAP.read_text(encoding="utf-8")
        self.assertIn("ValidateSet('Установка','Статус','Восстановление')", text)
        self.assertIn("$ReadOnly=($Mode -eq 'Статус')", text)
        self.assertIn("secret_values_included=$false", text)
        self.assertIn("owner_gate='mtd'", text)
        self.assertIn("ПРОЙДЕНО", text)
        self.assertIn("ЗАБЛОКИРОВАНО", text)
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
        self.assertIn("неизвестные представления Project", text)
        self.assertIn("не будет заменять идентификаторы вариантов поля", text)
        self.assertIn("duration=3", text)
        self.assertIn("Opt 'Проверка качества'", text)
        self.assertIn("Opt 'Антигравити'", text)
        self.assertNotIn("Opt 'Проверка QA'", text)
        self.assertNotIn("Opt 'AGY'", text)
        self.assertIn("deleteProjectV2View(input:$input){projectV2View{id}}", text)

    def test_human_facing_templates_are_russian(self):
        data = json.loads(MANIFEST.read_text(encoding="utf-8"))
        checked = 0
        for item in data["templates"]:
            source = ROOT / item["source"]
            text = source.read_text(encoding="utf-8")
            if source.name == "config.yml":
                continue
            if source.suffix.lower() in {".md", ".yml", ".yaml"} or source.name == "CODEOWNERS":
                self.assertRegex(text, r"[А-Яа-яЁё]", str(source))
                if source.name == "AGENTS.md":
                    self.assertNotIn("Проверка QA", text)
                    self.assertNotIn("machine identity", text.lower())
                checked += 1
        self.assertGreaterEqual(checked, 8)

    @unittest.skipUnless(shutil.which("pwsh"), "PowerShell 7 недоступен в окружении тестов")
    def test_powershell_bootstrap_scripts_parse(self):
        for path in (BOOTSTRAP, PROJECT):
            escaped = str(path).replace("'", "''")
            command = (
                "$tokens=$null; $errors=$null; "
                f"[System.Management.Automation.Language.Parser]::ParseFile('{escaped}', [ref]$tokens, [ref]$errors) | Out-Null; "
                "if($errors.Count -gt 0){ $errors | ForEach-Object { Write-Error $_.Message }; exit 1 }"
            )
            result = subprocess.run(
                ["pwsh", "-NoProfile", "-Command", command],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, f"{path}: {result.stderr}\n{result.stdout}")


if __name__ == "__main__":
    unittest.main()
