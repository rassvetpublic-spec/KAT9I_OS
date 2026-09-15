from pathlib import Path
import shutil
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
QUEUE_BEHAVIOR = ROOT / "tests" / "test_project_queue_sync.ps1"
CONFIG = ROOT / "scripts" / "configure_project.ps1"
SYNC = ROOT / "scripts" / "project_queue_sync.ps1"
PREFLIGHT = ROOT / "scripts" / "project_credential_preflight.ps1"
PREFLIGHT_DIAGNOSTIC = ROOT / "scripts" / "project_preflight_diagnostic.ps1"
EVENT = ROOT / "scripts" / "project_queue_event.py"
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
        self.assertIn("'QA_READY'", sync)
        self.assertIn("'QUEUED'", sync)
        self.assertIn("'Автопроверки пройдены'", sync)
        self.assertIn("'Проверка качества пройдена'", sync)
        self.assertIn("'В очереди'", sync)
        self.assertIn("--id $ItemId", sync)
        self.assertIn("--project-id $ProjectId", sync)
        self.assertIn("--field-id $Binding.FieldId", sync)
        self.assertIn("--single-select-option-id $Binding.OptionId", sync)
        self.assertNotIn("gh pr merge", sync)
        self.assertNotIn("merge_pull_request", sync)

    def test_project_read_retry_is_bounded_and_writes_are_not_retried(self):
        sync = SYNC.read_text(encoding="utf-8")
        self.assertIn("for($attempt=1;$attempt -le 2;$attempt++)", sync)
        self.assertIn("Start-Sleep -Seconds 1", sync)
        self.assertIn("после 2 попыток чтения", sync)
        edit_start = sync.index("function Invoke-ProjectEdit")
        edit_end = sync.index("function Sync-ProjectQueueState")
        edit_body = sync[edit_start:edit_end]
        self.assertNotIn("for($attempt", edit_body)
        self.assertNotIn("Start-Sleep", edit_body)

    def test_preflight_coordinates_are_reused_by_workflow(self):
        sync = SYNC.read_text(encoding="utf-8")
        preflight = PREFLIGHT.read_text(encoding="utf-8")
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("[string]$PreflightPath=''", sync)
        self.assertIn("Resolve-ProjectCoordinates", sync)
        self.assertIn("Source='PREFLIGHT'", sync)
        self.assertIn("[string]$OutputPath=''", preflight)
        self.assertIn("$preflightLibraryMode=[bool]$LibraryMode", preflight)
        self.assertIn("$LibraryMode=$preflightLibraryMode", preflight)
        self.assertIn("ProjectId=$projectId", preflight)
        self.assertIn("ItemId=$itemId", preflight)
        self.assertIn("-OutputPath \"$PWD/project-preflight.json\"", workflow)
        self.assertIn("-PreflightPath \"$PWD/project-preflight.json\"", workflow)
        self.assertIn("project_preflight_diagnostic.ps1", workflow)
        self.assertIn("PREFLIGHT_ARTIFACT_MISSING", PREFLIGHT_DIAGNOSTIC.read_text(encoding="utf-8"))

    def test_workflow_is_single_trusted_project_writer_for_qa_phases(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        event = EVENT.read_text(encoding="utf-8")
        self.assertIn("KAT9I_PROJECT_TOKEN", text)
        self.assertIn("project_queue_event.py", text)
        self.assertIn("project_queue_sync.ps1", text)
        self.assertNotIn("configure_project.ps1", text)
        self.assertIn("types: [closed, synchronize]", text)
        self.assertIn("QA_READY", text)
        self.assertIn("expected_head", text)
        self.assertIn("ITEM_WORKER", text)
        self.assertIn("ITEM_QA", text)
        self.assertIn("github.actor", text)
        self.assertIn("KAT9I-EVIDENCE-SNAPSHOT/1", event)
        self.assertIn("COMMAND_MARKER", event)
        self.assertIn("parse_epoch_section", event)
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
        self._run_pwsh(QUEUE_BEHAVIOR, "PASS: Project queue identity metadata")


if __name__ == "__main__":
    unittest.main()
