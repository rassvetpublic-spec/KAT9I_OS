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
        self.assertNotIn("Invoke-ExplicitFallback\n        exit", controller.split("'install'", 1)[1].split("'repair'", 1)[0])

    def test_backup_before_first_write_and_rollback_contract(self):
        patch = (self.runtime_root / "_System" / "Patch-Antigravity.ps1").read_text(encoding="utf-8")
        backup_pos = patch.index("Transaction rule: verify backups for every target before the first write")
        write_pos = patch.index("[IO.File]::WriteAllBytes($p.Target,$data)")
        rollback_pos = patch.index("Restore-Verified $p.Target $p.Backup $p.Hash")
        self.assertLess(backup_pos, write_pos)
        self.assertGreater(rollback_pos, write_pos)
        self.assertIn("PATCH_INCOMPATIBLE / BLOCKED", patch)
        self.assertIn("signature is ambiguous", patch)

    def test_receipts_use_normalized_paths(self):
        patch = (self.runtime_root / "_System" / "Patch-Antigravity.ps1").read_text(encoding="utf-8")
        self.assertIn("Normalize-Path", patch)
        self.assertIn("%LOCALAPPDATA%", patch)
        self.assertIn("%APPDATA%", patch)
        self.assertIn("%USERPROFILE%", patch)


if __name__ == "__main__":
    unittest.main()
