# -*- coding: utf-8 -*-
"""Regression coverage for Codex review on exact Graveyard approval boundary."""

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.check_graveyard import CONTROL_TEXT_SUFFIXES, _iter_control_text_files
from scripts.graveyard_context import (
    REPO_ROOT,
    activation_action_hash,
    build_activation_ticket,
    can_seed_planning,
    confirm_for_normal_workflow,
    create_reactivation_candidate,
    record_canon_check,
    validate_candidate_policy,
    verified_work_provenance,
)


class TestLatestCodexRegressions(unittest.TestCase):
    def setUp(self):
        manifest = json.loads((REPO_ROOT / "graveyard" / "MANIFEST.json").read_text(encoding="utf-8"))
        self.manifest = manifest
        self.archive_id = manifest["archives"][0]["archive_id"]
        self.now = "2026-09-09T15:02:00Z"
        self.created = "2026-09-09T15:00:00Z"
        self.revision = "main@0123456789abcdef"

    def _checked_candidate(self):
        candidate = create_reactivation_candidate(
            self.archive_id,
            "Проверить latest Codex regressions",
            selector="section:sealed",
            root=REPO_ROOT,
            created_at=self.created,
        )
        return record_canon_check(
            candidate,
            status="COMPATIBLE",
            checked_revision=self.revision,
            root=REPO_ROOT,
        )

    def _identity(self):
        return {
            "identity_id": "id-user12345678",
            "subject_type": "HUMAN_USER",
            "display_name": "Local User",
            "roles": ["LOCAL_USER"],
            "trust_level": "AUTHENTICATED",
            "windows_binding": {
                "security_identifier": "S-1-5-21-1000",
                "account_name": "LOCAL\\\\User",
                "is_elevated": False,
                "account_hash": "sha256:" + "a" * 64,
            },
            "created_at": "2026-09-09T14:00:00Z",
        }

    def test_candidate_id_binds_manifest_path_and_hash_revision(self):
        candidate = create_reactivation_candidate(
            self.archive_id,
            "Manifest binding must survive Archive ID remap",
            root=REPO_ROOT,
            created_at=self.created,
        )
        swapped = copy.deepcopy(self.manifest)
        self.assertGreaterEqual(len(swapped["archives"]), 2)
        first, second = swapped["archives"][0], swapped["archives"][1]
        first["archive_id"], second["archive_id"] = second["archive_id"], first["archive_id"]
        with patch("scripts.graveyard_context.load_manifest", return_value=swapped):
            with self.assertRaises(ValueError):
                validate_candidate_policy(candidate, root=REPO_ROOT)

    def test_dot_relative_graveyard_uri_cannot_seed_planning(self):
        forged = {
            "ref_id": "ctx-history12345678",
            "uri": "./graveyard/GY-test.md",
            "source_class": "history",
            "resolver": "history_store",
            "actionable": True,
            "control": True,
            "provenance": {"source_uri": "./graveyard/GY-test.md"},
        }
        self.assertFalse(can_seed_planning(forged))

    def test_verified_outcome_exposes_only_copies_not_mutable_sealed_state(self):
        candidate = self._checked_candidate()
        ticket = build_activation_ticket(
            candidate,
            task_id="review-task-95",
            proposed_work={"kind": "ISSUE", "summary": "Normal workflow handoff", "target": "rassvetpublic-spec/KAT9I_OS"},
            issued_at=self.created,
            expires_at="2026-09-09T15:30:00Z",
            root=REPO_ROOT,
        )
        identity = self._identity()
        approval = {
            "approval_id": "appr-graveyard123456",
            "approver_identity_id": identity["identity_id"],
            "approver_role": "LOCAL_USER",
            "task_id": "review-task-95",
            "action_hash": activation_action_hash(ticket, root=REPO_ROOT),
            "nonce": "nonce-sealed-outcome-0001",
            "reason": "Exact ticket approved.",
            "issued_at": "2026-09-09T15:01:00Z",
            "expires_at": "2026-09-09T15:20:00Z",
        }
        outcome = confirm_for_normal_workflow(
            candidate,
            activation_ticket=ticket,
            approval_record=approval,
            identity=identity,
            used_nonces=set(),
            now=self.now,
            root=REPO_ROOT,
        )
        exposed_approval = outcome.approval_record
        exposed_candidate = outcome.candidate
        exposed_approval["approval_id"] = "appr-forged12345678"
        exposed_candidate["owner_confirmation_ref"] = "appr-forged12345678"
        provenance = verified_work_provenance(outcome, root=REPO_ROOT)
        self.assertEqual(provenance["approval_id"], "appr-graveyard123456")
        self.assertEqual(outcome.candidate["owner_confirmation_ref"], "appr-graveyard123456")

    def test_windows_cmd_and_bat_are_scanned_as_control_text(self):
        self.assertIn(".cmd", CONTROL_TEXT_SUFFIXES)
        self.assertIn(".bat", CONTROL_TEXT_SUFFIXES)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            scripts = root / "scripts"
            scripts.mkdir()
            cmd = scripts / "auto_plan.cmd"
            cmd.write_text("type graveyard\\GY-test.md\n", encoding="utf-8")
            bat = scripts / "auto_plan.bat"
            bat.write_text("type graveyard\\GY-test.md\n", encoding="utf-8")
            yielded = {p.name for p in _iter_control_text_files(root)}
            self.assertEqual(yielded, {"auto_plan.cmd", "auto_plan.bat"})


if __name__ == "__main__":
    unittest.main()
