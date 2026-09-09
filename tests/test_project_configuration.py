from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "configure_project.ps1"
WORKFLOW_DOC = ROOT / "docs" / "GITHUB_WORKFLOW.md"

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

    def test_documentation_matches_canonical_views(self):
        text = WORKFLOW_DOC.read_text(encoding="utf-8")
        self.assertIn("ровно пять", text.lower())
        for name in CANONICAL_VIEWS:
            self.assertIn(f"`{name}`", text)

    def test_unknown_views_are_fail_closed(self):
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("$unexpected", text)
        self.assertIn("неизвестные дополнительные представления", text)
        self.assertNotIn("$blank=", text)


if __name__ == "__main__":
    unittest.main()
