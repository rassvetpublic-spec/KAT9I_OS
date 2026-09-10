# -*- coding: utf-8 -*-
"""Regression coverage for Graveyard hardening Issue #99."""

import hashlib
import inspect
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.check_graveyard import (
    MARKER,
    _find_python_ast_graveyard_ref,
    _git_blob_sha1,
    validate_graveyard,
)
from scripts.graveyard_excavate import _approve_via_trusted_cli_boundary


class TestGraveyardIssue99(unittest.TestCase):
    def _repo(self):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        for name in ("graveyard", "docs", "schemas", "config", "scripts", "tests"):
            (root / name).mkdir()
        (root / "README.md").write_text("# Test\n", encoding="utf-8")
        (root / "graveyard" / "README.md").write_text("# Graveyard\n", encoding="utf-8")
        archive = root / "graveyard" / "GY-20260910-test.md"
        data = (MARKER + "\n\nИсторические DATA.\n").encode("utf-8")
        archive.write_bytes(data)
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
            "archives": [{
                "archive_id": "GY-20260910-test",
                "path": "graveyard/GY-20260910-test.md",
                "archive_date": "2026-09-10",
                "byte_size": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
                "git_blob_sha1": _git_blob_sha1(data),
                "actionable": False,
                "control": False,
                "canonical": False,
            }],
        }
        (root / "graveyard" / "MANIFEST.json").write_text(
            json.dumps(manifest, ensure_ascii=False), encoding="utf-8"
        )
        return temp, root, archive

    def test_repo_wide_symlink_alias_to_graveyard_is_rejected(self):
        temp, root, _ = self._repo()
        with temp:
            alias = root / "archive_alias"
            try:
                os.symlink(root / "graveyard", alias, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest("symlink недоступен в test environment")
            with self.assertRaisesRegex(ValueError, "Repo-wide alias"):
                validate_graveyard(root)

    def test_repo_wide_symlink_alias_to_archive_is_rejected(self):
        temp, root, archive = self._repo()
        with temp:
            alias = root / "archive.md"
            try:
                os.symlink(archive, alias)
            except (OSError, NotImplementedError):
                self.skipTest("symlink недоступен в test environment")
            with self.assertRaisesRegex(ValueError, "Repo-wide alias"):
                validate_graveyard(root)

    def test_ast_detects_compile_time_concatenation(self):
        source = (
            'from pathlib import Path\n'
            'BASE = "grave" + "yard"\n'
            'NAME = "GY-" + "20260910-test" + ".md"\n'
            'TARGET = Path(BASE) / NAME\n'
        )
        found = _find_python_ast_graveyard_ref(source)
        self.assertIsNotNone(found)
        self.assertIn("GY-20260910-test.md", found)

    def test_ast_detects_joinpath_with_constants(self):
        source = (
            'from pathlib import Path\n'
            'BASE = Path("grave" + "yard")\n'
            'TARGET = BASE.joinpath("GY-" + "20260910-test.md")\n'
        )
        self.assertIsNotNone(_find_python_ast_graveyard_ref(source))

    def test_ast_does_not_execute_dynamic_code(self):
        source = (
            'def dynamic(name):\n'
            '    return name\n'
            'TARGET = dynamic("graveyard/GY-20260910-test.md")\n'
        )
        # Direct literal remains visible to static analysis; unknown calls are never executed.
        self.assertIsNotNone(_find_python_ast_graveyard_ref(source))

    def test_trusted_cli_boundary_has_no_injected_clock_or_store_parameters(self):
        params = tuple(inspect.signature(_approve_via_trusted_cli_boundary).parameters)
        self.assertEqual(params, ("prepared", "approval_record", "identity"))
        with patch("scripts.graveyard_excavate._trusted_now_iso", return_value="2026-09-10T10:00:00Z"), patch(
            "scripts.graveyard_excavate._trusted_nonce_state_path",
            return_value=Path("/trusted/graveyard-used-nonces.json"),
        ), patch("scripts.graveyard_excavate.approve_excavate_request_with_nonce_file", return_value={"status": "OK"}) as call:
            result = _approve_via_trusted_cli_boundary({}, {}, {})
        self.assertEqual(result, {"status": "OK"})
        kwargs = call.call_args.kwargs
        self.assertEqual(kwargs["now"], "2026-09-10T10:00:00Z")
        self.assertEqual(kwargs["nonce_state_path"], Path("/trusted/graveyard-used-nonces.json"))

    def test_readme_documents_defence_in_depth_boundary(self):
        root = Path(__file__).resolve().parents[1]
        text = (root / "graveyard" / "README.md").read_text(encoding="utf-8")
        self.assertIn("defence-in-depth", text)
        self.assertIn("Context/Planner", text)
        self.assertIn("trusted cli", text.casefold())
        self.assertNotIn("durable replay-store nonce после перезапуска", text)


if __name__ == "__main__":
    unittest.main()
