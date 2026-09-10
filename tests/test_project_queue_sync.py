from pathlib import Path
import shutil
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
BEHAVIOR = ROOT / "tests" / "test_project_queue_sync.ps1"
CONFIG = ROOT / "scripts" / "configure_project.ps1"
SYNC = ROOT / "scripts" / "project_queue_sync.ps1"


class ProjectQueueSyncTests(unittest.TestCase):
    def test_queue_policy_is_canonical(self):
        config = CONFIG.read_text(encoding="utf-8")
        sync = SYNC.read_text(encoding="utf-8")
        self.assertIn("Антигравити", config)
        self.assertIn("Antigravity", config)
        self.assertIn("'QUEUED'", sync)
        self.assertIn("'Проверка качества пройдена'", sync)
        self.assertIn("'В очереди'", sync)
        self.assertNotIn("merge_pull_request", sync)
        self.assertNotIn("gh pr merge", sync)

    def test_behavior_suite(self):
        pwsh = shutil.which("pwsh")
        self.assertIsNotNone(pwsh, "PowerShell 7 (pwsh) обязателен для Project queue tests")
        result = subprocess.run(
            [pwsh, "-NoProfile", "-File", str(BEHAVIOR)],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            check=False,
        )
        self.assertEqual(0, result.returncode, msg=f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}")
        self.assertIn("PASS: Project queue lifecycle", result.stdout)


if __name__ == "__main__":
    unittest.main()
