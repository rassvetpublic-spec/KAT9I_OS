from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
PREFLIGHT = ROOT / "scripts" / "project_credential_preflight.ps1"
SYNC = ROOT / "scripts" / "project_queue_sync.ps1"
WORKFLOW = ROOT / ".github" / "workflows" / "project-queue-sync.yml"


class ProjectCredentialPreflightContractTests(unittest.TestCase):
    def test_diagnostic_codes_live_in_preflight_not_core_sync(self):
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
        self.assertNotIn("KAT9I_PROJECT_PREFLIGHT=", sync)

    def test_workflow_has_no_legacy_generic_credential_probe(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("project_credential_preflight.ps1", text)
        self.assertNotIn("gh auth status", text)
        self.assertNotIn("gh project view 2 --owner rassvetpublic-spec --format json >/dev/null", text)


if __name__ == "__main__":
    unittest.main()
