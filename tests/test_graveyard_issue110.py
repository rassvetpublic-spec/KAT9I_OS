# -*- coding: utf-8 -*-
"""Regression coverage for Graveyard replay-store path deduplication Issue #110."""

import inspect
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.graveyard_context import REPO_ROOT
from scripts.graveyard_excavate import _trusted_nonce_state_path
from scripts.graveyard_trusted_handoff import (
    TRUSTED_NONCE_STATE_RELATIVE_PATH,
    approve_trusted,
    trusted_nonce_state_path,
)


class TestGraveyardIssue110(unittest.TestCase):
    def test_default_helper_delegates_to_trusted_adapter(self):
        expected = REPO_ROOT / TRUSTED_NONCE_STATE_RELATIVE_PATH
        with patch(
            "scripts.graveyard_trusted_handoff.trusted_nonce_state_path",
            return_value=expected,
        ) as trusted_path:
            self.assertEqual(_trusted_nonce_state_path(), expected)
        trusted_path.assert_called_once_with()

    def test_custom_test_root_reuses_same_relative_definition(self):
        test_root = Path("test-root")
        self.assertEqual(
            _trusted_nonce_state_path(test_root),
            test_root / TRUSTED_NONCE_STATE_RELATIVE_PATH,
        )

    def test_replay_store_filename_literal_owned_by_trusted_adapter(self):
        root = Path(__file__).resolve().parents[1]
        trusted_source = (root / "scripts" / "graveyard_trusted_handoff.py").read_text(encoding="utf-8")
        excavate_source = (root / "scripts" / "graveyard_excavate.py").read_text(encoding="utf-8")
        self.assertIn("graveyard-used-nonces.json", trusted_source)
        self.assertNotIn("graveyard-used-nonces.json", excavate_source)

    def test_production_facing_signature_remains_closed(self):
        self.assertEqual(
            tuple(inspect.signature(approve_trusted).parameters),
            ("prepared", "approval_record", "identity"),
        )
        self.assertEqual(trusted_nonce_state_path(), REPO_ROOT / TRUSTED_NONCE_STATE_RELATIVE_PATH)


if __name__ == "__main__":
    unittest.main()
