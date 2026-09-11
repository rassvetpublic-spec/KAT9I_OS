from pathlib import Path
import json
import shutil
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "configure_project.ps1"
WORKFLOW_DOC = ROOT / "docs" / "GITHUB_WORKFLOW.md"
BEHAVIOR_TEST = ROOT / "tests" / "test_project_views.ps1"

CANONICAL_VIEWS = ['00 — Dashboard', '01 — Queue', '02 — Active Work', '03 — QA Gate', '04 — Release Flow', '05 — Roadmap', '06 — Blocked / Parking', '07 — Agent KPI']


class ProjectConfigurationTests(unittest.TestCase):
    def test_configurator_and_audit_use_shared_eight_view_policy(self):
        policy = json.loads((ROOT / "config/project_views.json").read_text(encoding="utf-8"))
        self.assertEqual(CANONICAL_VIEWS, [v["name"] for v in policy["views"]])
        self.assertEqual(8, len(policy["views"]))
        self.assertEqual(["TABLE_LAYOUT", "BOARD_LAYOUT", "BOARD_LAYOUT", "TABLE_LAYOUT", "BOARD_LAYOUT", "ROADMAP_LAYOUT", "TABLE_LAYOUT", "TABLE_LAYOUT"], [v["layout"] for v in policy["views"]])
        self.assertIn("CanonicalViews $statusName", SCRIPT.read_text(encoding="utf-8"))
        self.assertIn("config/project_views.json", (ROOT / "scripts/g0_control_plane_audit.py").read_text(encoding="utf-8"))

    def test_documentation_matches_canonical_views_and_status(self):
        text = WORKFLOW_DOC.read_text(encoding="utf-8")
        self.assertIn("ровно восемь", text.lower())
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
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            check=False,
        )
        self.assertEqual(
            0,
            result.returncode,
            msg=f"PowerShell behavior test упал.\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}",
        )
        self.assertIn("PASS: Project policy запускает фактическое production-тело entrypoint", result.stdout)


if __name__ == "__main__":
    unittest.main()

