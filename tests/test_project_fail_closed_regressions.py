from pathlib import Path
import shutil
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
BEHAVIOR_TEST = ROOT / "tests" / "test_project_fail_closed_regressions.ps1"


class ProjectFailClosedRegressionTests(unittest.TestCase):
    def test_fail_closed_regressions_are_executed(self):
        pwsh = shutil.which("pwsh")
        self.assertIsNotNone(pwsh, "PowerShell 7 (pwsh) обязателен для regression-проверки Project policy")
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
            msg=f"PowerShell regression test упал.\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}",
        )
        self.assertIn("PASS: #101/#104 regression", result.stdout)


if __name__ == "__main__":
    unittest.main()
