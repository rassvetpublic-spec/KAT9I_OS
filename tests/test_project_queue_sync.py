from pathlib import Path
import shutil
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
QUEUE_BEHAVIOR = ROOT / "tests" / "test_project_queue_sync.ps1"
CONFIG = ROOT / "scripts" / "configure_project.ps1"
SYNC = ROOT / "scripts" / "project_queue_sync.ps1"
WORKFLOW = ROOT / ".github" / "workflows" / "project-queue-sync.yml"


class ProjectQueueSyncTests(unittest.TestCase):
    def test_queue_policy_is_canonical(self):
        config = CONFIG.read_text(encoding="utf-8")
        sync = SYNC.read_text(encoding="utf-8")
        self.assertIn("(Opt 'AGY'", config)
        self.assertNotIn("(Opt 'Антигравити'", config)
        for alias in (
            "AGY",
            "Agy",
            "Antigravity",
            "Антигравити",
            "Antigravity (AGY)",
            "Антигравити (AGY)",
        ):
            self.assertIn(alias, sync)
        self.assertIn("'INBOX'", sync)
        self.assertIn("'QUEUED'", sync)
        self.assertIn("'Проверка качества пройдена'", sync)
        self.assertIn("'В очереди'", sync)
        self.assertIn("--id $ItemId", sync)
        self.assertIn("--project-id $ProjectId", sync)
        self.assertIn("--field-id $Binding.FieldId", sync)
        self.assertIn("--single-select-option-id $Binding.OptionId", sync)
        self.assertNotIn("gh pr merge", sync)
        self.assertNotIn("merge_pull_request", sync)

    def test_diagnostic_preflight_contract_is_pinned(self):
        sync = SYNC.read_text(encoding="utf-8")
        for code in (
            "SECRET_MISSING",
            "TOKEN_INVALID",
            "PROJECT_ACCESS_DENIED",
            "PROJECT_WRITE_DENIED",
            "PROJECT_SCHEMA_MISMATCH",
            "PROJECT_SYNC_FAILED",
        ):
            self.assertIn(code, sync)
        self.assertIn("viewerCanUpdate", sync)
        self.assertIn("KAT9I_PROJECT_PREFLIGHT=OK", sync)
        self.assertIn("gh api user", sync)
        self.assertNotIn("$env:GITHUB_TOKEN", sync)

    def test_workflow_is_trusted_and_never_merges(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("KAT9I_PROJECT_TOKEN", text)
        self.assertIn("project_queue_event.py", text)
        self.assertIn("project_queue_sync.ps1", text)
        self.assertNotIn("configure_project.ps1", text)
        self.assertIn("types: [closed, synchronize]", text)
        self.assertIn("ITEM_WORKER", text)
        self.assertIn("ITEM_QA", text)
        self.assertIn("github.actor", text)
        self.assertNotIn("-Worker 'ChatGPT' -QaWorker 'AGY'", text)
        self.assertNotIn("gh pr merge", text)
        self.assertNotIn("merge_pull_request", text)
        self.assertNotIn("pull_request_target", text)

    def _run_pwsh(self, path: Path, expected: str):
        pwsh = shutil.which("pwsh")
        self.assertIsNotNone(pwsh, "PowerShell 7 (pwsh) обязателен для Project tests")
        result = subprocess.run(
            [pwsh, "-NoProfile", "-File", str(path)],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            check=False,
        )
        self.assertEqual(0, result.returncode, msg=f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}")
        self.assertIn(expected, result.stdout)

    def test_queue_behavior_suite(self):
        self._run_pwsh(QUEUE_BEHAVIOR, "PASS: Project queue identity metadata, diagnostic preflight")


if __name__ == "__main__":
    unittest.main()
