from pathlib import Path
import re
import shutil
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "configure_project.ps1"
WORKFLOW_DOC = ROOT / "docs" / "GITHUB_WORKFLOW.md"
BEHAVIOR_TEST = ROOT / "tests" / "test_project_views.ps1"

CANONICAL_VIEWS = [
    "00 — Все задачи",
    "01 — Готово к работе",
    "02 — В работе",
    "03 — Проверка",
    "04 — Заблокировано",
]


class ProjectConfigurationTests(unittest.TestCase):
    def test_configurator_has_exactly_five_canonical_views(self):
        text = SCRIPT.read_text(encoding="utf-8")
        match = re.search(
            r"\$views=@\(\s*(.*?)\n\s*\)\s*\n\s*\$p=\(Snapshot\)\.user\.projectV2",
            text,
            re.DOTALL,
        )
        self.assertIsNotNone(match, "Не найден канонический блок $views в configure_project.ps1")
        active_block = match.group(1)
        names = re.findall(r"@\{n='([^']+)'", active_block)
        self.assertEqual(CANONICAL_VIEWS, names)
        self.assertEqual(5, len(names))
        self.assertIn('Статус:\"Проверка QA\"', active_block)

    def test_documentation_matches_canonical_views_and_status(self):
        text = WORKFLOW_DOC.read_text(encoding="utf-8")
        self.assertIn("ровно пять", text.lower())
        self.assertIn("`Проверка QA`", text)
        for name in CANONICAL_VIEWS:
            self.assertIn(f"`{name}`", text)

    def test_fail_closed_behavior_is_executed(self):
        pwsh = shutil.which("pwsh")
        self.assertIsNotNone(pwsh, "PowerShell 7 (pwsh) обязателен для поведенческой проверки Project policy")
        result = subprocess.run(
            [pwsh, "-NoProfile", "-File", str(BEHAVIOR_TEST)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(
            0,
            result.returncode,
            msg=f"PowerShell behavior test упал.\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}",
        )
        self.assertIn("PASS: Project policy fail-closed", result.stdout)


if __name__ == "__main__":
    unittest.main()
