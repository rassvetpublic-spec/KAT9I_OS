import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "bootstrap" / "antigravity-one" / "Test-Antigravity-One-Host.ps1"


class AntigravityOneHostSmokeContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = SCRIPT.read_text(encoding="utf-8")

    def test_read_only_is_default(self):
        self.assertIn("[string]$Mode = 'ReadOnly'", self.text)
        self.assertIn("if ($Mode -ne 'ReadOnly' -and -not $AllowMutation)", self.text)
        self.assertIn("Mutation mode requires explicit -AllowMutation.", self.text)

    def test_read_only_runs_status_and_dryrun(self):
        self.assertIn("Invoke-Entry 'status'", self.text)
        self.assertIn("Invoke-Entry 'dryrun'", self.text)
        self.assertIn("READ_ONLY_MUTATION_DETECTED", self.text)

    def test_mutating_commands_require_explicit_mode(self):
        self.assertIn("[ValidateSet('ReadOnly','Install','Repair')]", self.text)
        self.assertIn("if ($Mode -eq 'Install')", self.text)
        self.assertIn("elseif ($Mode -eq 'Repair')", self.text)
        self.assertNotIn("Invoke-Entry 'fallback'", self.text)

    def test_evidence_is_sanitized_and_machine_readable(self):
        self.assertIn("Normalize-Path", self.text)
        self.assertIn("%LOCALAPPDATA%", self.text)
        self.assertIn("%APPDATA%", self.text)
        self.assertIn("%USERPROFILE%", self.text)
        self.assertIn("protected_state_before", self.text)
        self.assertIn("protected_state_after", self.text)
        self.assertIn("ConvertTo-Json", self.text)
        self.assertNotIn("Get-Content -LiteralPath (Join-Path $Root 'Standalone\\Profile')", self.text)


if __name__ == "__main__":
    unittest.main()
