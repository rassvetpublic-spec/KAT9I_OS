import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from check_graveyard import MARKER, _git_blob_sha1, validate_append_only, validate_graveyard


class GraveyardChecksTests(unittest.TestCase):
    def _repo(self):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        (root / "graveyard").mkdir()
        (root / "docs").mkdir()
        (root / "schemas").mkdir()
        (root / "config").mkdir()
        (root / "README.md").write_text("# Test\n", encoding="utf-8")
        (root / "graveyard" / "README.md").write_text("# Graveyard\n", encoding="utf-8")

        archive_path = root / "graveyard" / "GY-20260909-test.md"
        data = (MARKER + "\n\nИсторические DATA.\n").encode("utf-8")
        archive_path.write_bytes(data)

        manifest = {
            "schema_version": "1.0",
            "source_class": "graveyard",
            "actionable": False,
            "control": False,
            "canonical": False,
            "auto_promotion": False,
            "ssot": False,
            "owner_reactivation_required": True,
            "archive_policy": {
                "immutable_history": True,
                "prefer_new_version_over_in_place_edit": True,
                "current_canon_wins_on_conflict": True,
            },
            "archives": [
                {
                    "archive_id": "GY-20260909-test",
                    "path": "graveyard/GY-20260909-test.md",
                    "archive_date": "2026-09-09",
                    "byte_size": len(data),
                    "sha256": hashlib.sha256(data).hexdigest(),
                    "git_blob_sha1": _git_blob_sha1(data),
                    "actionable": False,
                    "control": False,
                    "canonical": False,
                }
            ],
        }
        manifest_path = root / "graveyard" / "MANIFEST.json"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
        return temp, root, manifest, archive_path, manifest_path

    def test_valid_graveyard_passes(self):
        temp, root, _, _, _ = self._repo()
        with temp:
            validate_graveyard(root)

    def test_actionable_true_fails_closed(self):
        temp, root, manifest, _, manifest_path = self._repo()
        with temp:
            manifest["actionable"] = True
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
            with self.assertRaises(ValueError):
                validate_graveyard(root)

    def test_archive_content_change_fails_integrity(self):
        temp, root, _, archive_path, _ = self._repo()
        with temp:
            archive_path.write_text(MARKER + "\n\nИзменено.\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                validate_graveyard(root)

    def test_unregistered_archive_fails_closed(self):
        temp, root, _, _, _ = self._repo()
        with temp:
            (root / "graveyard" / "GY-20260909-unregistered.md").write_text(MARKER + "\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                validate_graveyard(root)

    def test_specific_graveyard_dependency_from_docs_fails(self):
        temp, root, _, _, _ = self._repo()
        with temp:
            (root / "docs" / "bad.md").write_text("Источник: graveyard/GY-20260909-test.md\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                validate_graveyard(root)

    @patch("check_graveyard.subprocess.run")
    def test_append_only_rejects_modified_existing_archive(self, run):
        temp, root, _, _, _ = self._repo()
        with temp:
            run.return_value.stdout = "M\tgraveyard/GY-20260909-test.md\n"
            with self.assertRaises(ValueError):
                validate_append_only(root, "base-sha")

    @patch("check_graveyard.subprocess.run")
    def test_append_only_allows_new_archive(self, run):
        temp, root, _, _, _ = self._repo()
        with temp:
            run.return_value.stdout = "A\tgraveyard/GY-20260910-new.md\n"
            validate_append_only(root, "base-sha")


if __name__ == "__main__":
    unittest.main()
