import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "antigravity_one_contract.py"
SPEC = importlib.util.spec_from_file_location("antigravity_one_contract", MODULE_PATH)
mod = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(mod)


class AntigravityOneContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = mod.load_manifest()
        cls.x64 = next(x for x in cls.manifest["signatures"] if x["architecture"] == "x64")
        cls.arm64 = next(x for x in cls.manifest["signatures"] if x["architecture"] == "arm64")
        cls.runtime_root = ROOT / "bootstrap" / "antigravity-one"

    def test_manifest_is_version_hash_bound(self):
        self.assertGreaterEqual(len(self.manifest["compatibility"]), 1)
        for row in self.manifest["compatibility"]:
            self.assertRegex(row["product_version"], r"^\d+\.\d+(?:\.\d+)?$")
            self.assertIn(row["architecture"], {"x64", "arm64"})
            self.assertRegex(row["source_sha256"], r"^[0-9a-f]{64}$")
            self.assertTrue(row["signature_id"])

    def test_x64_original_to_patched(self):
        original = bytes.fromhex("AA BB 80 78 08 00 74 12 48 8B 55 24 20 48 89 4A 60 CC DD")
        self.assertEqual(mod.classify(original, self.x64)[0], "ORIGINAL")
        patched = mod.apply_patch(original, self.x64)
        self.assertEqual(mod.classify(patched, self.x64)[0], "PATCHED")
        self.assertEqual(patched[2:8], bytes.fromhex("C6 40 08 01 90 90"))

    def test_ambiguous_signature_is_blocked(self):
        gate = bytes.fromhex("80 78 08 00 74 12 48 8B 55 24 20 48 89 4A 60")
        data = b"\x00" + gate + b"\x00" + gate + b"\x00"
        with self.assertRaises(mod.ContractError):
            mod.classify(data, self.x64)

    def test_arm64_original_to_patched(self):
        original = bytes.fromhex(
            "AA AA 03 20 40 39 03 11 22 36 10 20 30 40 03 10 06 A9 BB BB"
        )
        self.assertEqual(mod.classify(original, self.arm64)[0], "ORIGINAL")
        patched = mod.apply_patch(original, self.arm64)
        self.assertEqual(mod.classify(patched, self.arm64)[0], "PATCHED")

    def test_manifest_rejects_unknown_signature_reference(self):
        broken = json.loads(json.dumps(self.manifest))
        broken["compatibility"] = [{
            "product_version": "9.9.9",
            "architecture": "x64",
            "source_sha256": "0" * 64,
            "patched_sha256": "",
            "signature_id": "missing-signature",
        }]
        with self.assertRaises(mod.ContractError):
            mod.validate_manifest(broken)

    def test_single_entry_point_and_explicit_fallback(self):
        cmd = (self.runtime_root / "ANTIGRAVITY.cmd").read_text(encoding="utf-8")
        controller = (self.runtime_root / "_System" / "Antigravity-Control.ps1").read_text(encoding="utf-8")
        self.assertIn("Antigravity-Control.ps1", cmd)
        self.assertIn("ValidateSet('status','install','repair','fallback')", controller)
        self.assertIn("EXPLICIT FALLBACK", controller)
        install_block = controller.split("'install'", 1)[1].split("'repair'", 1)[0]
        self.assertNotIn("Invoke-ExplicitFallback", install_block)

    def test_dryrun_is_read_only_alias_to_status(self):
        cmd = (self.runtime_root / "ANTIGRAVITY.cmd").read_text(encoding="utf-8")
        lower = cmd.lower()
        self.assertIn('if /i "%~1"=="dryrun"', lower)
        dryrun_block = lower.split('if /i "%~1"=="dryrun"', 1)[1].split('"%ps%" -nologo -noprofile -executionpolicy bypass -file "%ctrl%" %*', 1)[0]
        self.assertIn('"%ctrl%" status', dryrun_block)
        self.assertNotIn(' install', dryrun_block)
        self.assertNotIn(' repair', dryrun_block)
        self.assertNotIn(' fallback', dryrun_block)

    def test_backup_before_first_write_and_transactional_rollback(self):
        patch = (self.runtime_root / "_System" / "Patch-Antigravity.ps1").read_text(encoding="utf-8")
        backup_pos = patch.index("Transaction rule: verify backups for every ORIGINAL target before the first write")
        write_pos = patch.index("[IO.File]::WriteAllBytes($p.Target,$data)")
        rollback_pos = patch.index("Restore-Verified $p.Target $p.Backup $p.Hash")
        self.assertLess(backup_pos, write_pos)
        self.assertGreater(rollback_pos, write_pos)
        self.assertIn("ROLLED_BACK_VERIFIED", patch)
        self.assertIn("ROLLBACK_FAILED", patch)

    def test_patched_state_requires_authority(self):
        patch = (self.runtime_root / "_System" / "Patch-Antigravity.ps1").read_text(encoding="utf-8")
        self.assertIn("Find-StateRecord", patch)
        self.assertIn("$p.Authorized -and $p.State -eq 'PATCHED'", patch)
        self.assertIn("authority='native-manifest'", patch)
        self.assertIn("patch-state.json", patch)

    def test_restore_uses_recorded_original_backup(self):
        patch = (self.runtime_root / "_System" / "Patch-Antigravity.ps1").read_text(encoding="utf-8")
        self.assertIn("$p.StateRecord.backup", patch)
        self.assertIn("$p.StateRecord.source_sha256", patch)
        self.assertIn("Restore-Verified", patch)

    def test_fallback_has_binary_backup_verify_register_and_rollback(self):
        controller = (self.runtime_root / "_System" / "Antigravity-Control.ps1").read_text(encoding="utf-8")
        self.assertIn("New-FallbackBinarySnapshot", controller)
        self.assertIn("Fallback backup verification failed", controller)
        self.assertIn("Register-VerifiedFallback", controller)
        self.assertIn("explicit-external-fallback", controller)
        self.assertIn("Restore-FallbackSnapshot", controller)
        self.assertIn("FALLBACK_VERIFIED", controller)

    def test_receipts_use_normalized_paths(self):
        patch = (self.runtime_root / "_System" / "Patch-Antigravity.ps1").read_text(encoding="utf-8")
        self.assertIn("Normalize-Path", patch)
        self.assertIn("%LOCALAPPDATA%", patch)
        self.assertIn("%APPDATA%", patch)
        self.assertIn("%USERPROFILE%", patch)

    def test_no_dotnet_fromhexstring_dependency(self):
        patch = (self.runtime_root / "_System" / "Patch-Antigravity.ps1").read_text(encoding="utf-8")
        self.assertNotIn("FromHexString", patch)
        self.assertIn("Convert-HexBytes", patch)


if __name__ == "__main__":
    unittest.main()
