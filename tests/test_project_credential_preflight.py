from pathlib import Path
import shutil
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
PREFLIGHT_BEHAVIOR = ROOT / "tests" / "test_project_credential_preflight.ps1"
PREFLIGHT = ROOT / "scripts" / "project_credential_preflight.ps1"
SYNC = ROOT / "scripts" / "project_queue_sync.ps1"
WORKFLOW = ROOT / ".github" / "workflows" / "project-queue-sync.yml"


class ProjectCredentialPreflightTests(unittest.TestCase):
    def test_contract_is_separate_read_only_preflight(self):
        preflight = PREFLIGHT.read_text(encoding="utf-8")
        sync = SYNC.read_text(encoding="utf-8")
        for code in (
            "SECRET_MISSING",
            "TOKEN_INVALID",
            "PROJECT_ACCESS_DENIED",
            "PROJECT_WRITE_DENIED",
            "PROJECT_SCHEMA_MISMATCH",
            "PROJECT_SYNC_FAILED",
        ):
            self.assertIn(code, preflight)
        self.assertIn("viewerCanUpdate", preflight)
        self.assertIn("KAT9I_PROJECT_PREFLIGHT=OK", preflight)
        self.assertNotIn("project item-edit", preflight)
        self.assertNotIn("$env:GITHUB_TOKEN", preflight)
        self.assertNotIn("KAT9I_PROJECT_PREFLIGHT=", sync)

    def test_workflow_runs_preflight_before_sync(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("KAT9I_PROJECT_TOKEN", text)
        self.assertIn("project_credential_preflight.ps1", text)
        self.assertIn("project_queue_sync.ps1", text)
        self.assertLess(text.index("project_credential_preflight.ps1"), text.index("project_queue_sync.ps1"))
        self.assertNotIn("${{ github.token }}", text)
        self.assertNotIn("GITHUB_TOKEN:", text)
        self.assertNotIn("gh pr merge", text)

    def test_behavior_suite(self):
        pwsh = shutil.which("pwsh")
        self.assertIsNotNone(pwsh, "PowerShell 7 (pwsh) обязателен для Project tests")
        result = subprocess.run(
            [pwsh, "-NoProfile", "-File", str(PREFLIGHT_BEHAVIOR)],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            check=False,
        )
        self.assertEqual(0, result.returncode, msg=f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}")
        self.assertIn("PASS: Project credential preflight diagnostics", result.stdout)


if __name__ == "__main__":
    unittest.main()
