# -*- coding: utf-8 -*-
"""Негативные и контрактные тесты Graveyard -> Context -> Approval -> normal workflow (#95)."""

import copy
import json
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from scripts.graveyard_context import (
    activation_action_hash,
    can_seed_planning,
    create_reactivation_candidate,
    reject_candidate,
    record_canon_check,
    resolve_archive_context,
    validate_candidate_policy,
    validate_context_ref_policy,
    verified_work_provenance,
)
from scripts.graveyard_excavate import (
    approve_excavate_request,
    approve_excavate_request_with_nonce_file,
    prepare_excavate_request,
)

REPO_ROOT = Path(__file__).resolve().parent.parent


class TestGraveyardContextBoundary(unittest.TestCase):
    def setUp(self):
        manifest = json.loads((REPO_ROOT / "graveyard" / "MANIFEST.json").read_text(encoding="utf-8"))
        self.archive_ids = [entry["archive_id"] for entry in manifest["archives"]]
        self.archive_id = self.archive_ids[0]
        self.fixed_time = "2026-09-09T15:00:00Z"
        self.checked_revision = "main@0123456789abcdef"
        self.ticket_expires = "2026-09-09T15:30:00Z"
        self.request = {
            "request_id": "gyreq-0123456789abcdef",
            "command": "EXCAVATE_IDEA",
            "task_id": "review-task-95",
            "requester_identity_id": "id-user12345678",
            "archive_id": self.archive_id,
            "selector": "section:3.1",
            "idea_summary": "Проверить историческую идею повторно",
            "proposed_work": {
                "kind": "ISSUE",
                "summary": "Оформить проверенную идею как обычную текущую работу",
                "target": "rassvetpublic-spec/KAT9I_OS",
            },
            "requested_at": self.fixed_time,
        }
        self.identity = {
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

    def _prepare(self):
        return prepare_excavate_request(
            self.request,
            canon_status="COMPATIBLE",
            checked_revision=self.checked_revision,
            ticket_expires_at=self.ticket_expires,
            evidence_ref="evidence://canon-check/1",
            notes="Идея совместима с текущим каноном.",
            root=REPO_ROOT,
        )

    def _approval(self, prepared, **overrides):
        approval = {
            "approval_id": "appr-graveyard123456",
            "approver_identity_id": self.identity["identity_id"],
            "approver_role": "LOCAL_USER",
            "task_id": self.request["task_id"],
            "action_hash": prepared["approval_action_hash"],
            "nonce": "nonce-graveyard-0001",
            "reason": "Явно разрешаю exact ticket.",
            "issued_at": "2026-09-09T15:01:00Z",
            "expires_at": "2026-09-09T15:20:00Z",
        }
        approval.update(overrides)
        return approval

    def test_every_archive_resolves_as_non_actionable_context(self):
        for archive_id in self.archive_ids:
            ref = resolve_archive_context(archive_id, root=REPO_ROOT, retrieved_at=self.fixed_time)
            self.assertEqual(ref["source_class"], "graveyard")
            self.assertFalse(ref["actionable"])
            self.assertFalse(ref["control"])
            self.assertFalse(ref["canonical"])
            self.assertEqual(ref["freshness"], "ARCHIVED")
            self.assertFalse(can_seed_planning(ref))

    def test_codex_p1_source_class_forgery_cannot_seed(self):
        ref = resolve_archive_context(self.archive_id, root=REPO_ROOT, retrieved_at=self.fixed_time)
        forged = copy.deepcopy(ref)
        forged.update(source_class="history", actionable=True, control=True, canonical=True)
        self.assertFalse(can_seed_planning(forged))
        with self.assertRaises(ValueError):
            validate_context_ref_policy(forged)

    def test_codex_p1_candidate_id_blocks_coordinated_provenance_substitution(self):
        if len(self.archive_ids) < 2:
            self.skipTest("Нужны два архива")
        candidate = create_reactivation_candidate(
            self.archive_id, "Проверка provenance", selector="section:1", root=REPO_ROOT, created_at=self.fixed_time
        )
        other = self.archive_ids[1]
        forged = copy.deepcopy(candidate)
        forged["archive_id"] = other
        forged["resurrected_from"] = other
        forged["source_ref"] = f"ctx-{other}"
        with self.assertRaises(ValueError):
            validate_candidate_policy(forged, root=REPO_ROOT)

    def test_unknown_archive_in_candidate_fails_closed(self):
        candidate = create_reactivation_candidate(
            self.archive_id, "Проверка manifest binding", root=REPO_ROOT, created_at=self.fixed_time
        )
        forged = copy.deepcopy(candidate)
        forged["archive_id"] = "GY-does-not-exist"
        forged["resurrected_from"] = "GY-does-not-exist"
        forged["source_ref"] = "ctx-GY-does-not-exist"
        with self.assertRaises(ValueError):
            validate_candidate_policy(forged, root=REPO_ROOT)

    def test_codex_p1_checked_revision_required_after_canon_check(self):
        candidate = create_reactivation_candidate(
            self.archive_id, "Проверка revision", root=REPO_ROOT, created_at=self.fixed_time
        )
        forged = copy.deepcopy(candidate)
        forged["state"] = "AWAITING_OWNER_CONFIRMATION"
        forged["canon_check"]["status"] = "COMPATIBLE"
        forged["canon_check"]["checked_revision"] = None
        with self.assertRaises(ValueError):
            validate_candidate_policy(forged, root=REPO_ROOT)
        schema = json.loads((REPO_ROOT / "schemas/v1/GraveyardCandidate.json").read_text(encoding="utf-8"))
        self.assertFalse(Draft202012Validator(schema).is_valid(forged))

    def test_codex_p2_rejected_completed_canon_check_requires_revision(self):
        candidate = create_reactivation_candidate(
            self.archive_id, "Проверка rejected revision", root=REPO_ROOT, created_at=self.fixed_time
        )
        forged = copy.deepcopy(candidate)
        forged["state"] = "REJECTED"
        forged["canon_check"]["status"] = "COMPATIBLE"
        forged["canon_check"]["checked_revision"] = None
        with self.assertRaises(ValueError):
            validate_candidate_policy(forged, root=REPO_ROOT)
        schema = json.loads((REPO_ROOT / "schemas/v1/GraveyardCandidate.json").read_text(encoding="utf-8"))
        self.assertFalse(Draft202012Validator(schema).is_valid(forged))

    def test_reject_after_real_canon_check_preserves_revision(self):
        candidate = create_reactivation_candidate(
            self.archive_id, "Отклоняемая идея", root=REPO_ROOT, created_at=self.fixed_time
        )
        checked = record_canon_check(candidate, status="COMPATIBLE", checked_revision=self.checked_revision, root=REPO_ROOT)
        rejected = reject_candidate(checked, root=REPO_ROOT)
        self.assertEqual(rejected["state"], "REJECTED")
        self.assertEqual(rejected["canon_check"]["checked_revision"], self.checked_revision)

    def test_conflict_superseded_unknown_are_blocked_without_ticket(self):
        for status in ("CONFLICT", "SUPERSEDED", "UNKNOWN"):
            result = prepare_excavate_request(
                self.request,
                canon_status=status,
                checked_revision=self.checked_revision,
                ticket_expires_at=self.ticket_expires,
                root=REPO_ROOT,
            )
            self.assertEqual(result["status"], "BLOCKED_BY_CANON")
            self.assertIsNone(result["activation_ticket"])
            self.assertFalse(result["side_effect_performed"])

    def test_prepare_exact_ticket_has_no_side_effect(self):
        prepared = self._prepare()
        self.assertEqual(prepared["status"], "AWAITING_OWNER_CONFIRMATION")
        self.assertFalse(prepared["side_effect_performed"])
        self.assertEqual(
            prepared["approval_action_hash"],
            activation_action_hash(prepared["activation_ticket"], root=REPO_ROOT),
        )

    def test_valid_approval_returns_only_provenance_handoff(self):
        prepared = self._prepare()
        approval = self._approval(prepared)
        used = set()
        result = approve_excavate_request(
            prepared, approval_record=approval, identity=self.identity,
            used_nonces=used, now="2026-09-09T15:02:00Z", root=REPO_ROOT,
        )
        self.assertEqual(result["status"], "APPROVED_FOR_NORMAL_WORKFLOW")
        self.assertFalse(result["side_effect_performed"])
        self.assertFalse(result["candidate"]["actionable"])
        self.assertEqual(result["provenance"]["approval_id"], approval["approval_id"])
        self.assertIn(approval["nonce"], used)

    def test_codex_p1_self_claimed_approved_candidate_cannot_build_provenance(self):
        prepared = self._prepare()
        forged = copy.deepcopy(prepared["candidate"])
        forged["state"] = "APPROVED_FOR_NORMAL_WORKFLOW"
        forged["activation_ref"] = prepared["activation_ticket"]["activation_id"]
        forged["owner_confirmation_ref"] = "appr-forged12345678"
        with self.assertRaises(ValueError):
            verified_work_provenance(forged, root=REPO_ROOT)

    def test_wrong_action_hash_task_identity_are_rejected(self):
        prepared = self._prepare()
        cases = [
            self._approval(prepared, action_hash="sha256:" + "0" * 64),
            self._approval(prepared, task_id="another-task"),
            self._approval(prepared, approver_identity_id="id-other12345678"),
        ]
        for approval in cases:
            with self.assertRaises(ValueError):
                approve_excavate_request(
                    prepared, approval_record=approval, identity=self.identity,
                    used_nonces=set(), now="2026-09-09T15:02:00Z", root=REPO_ROOT,
                )

    def test_worker_provisional_and_unelevated_admin_are_rejected(self):
        prepared = self._prepare()
        approval = self._approval(prepared)
        worker = copy.deepcopy(self.identity)
        worker["subject_type"] = "LOCAL_WORKER"
        worker["roles"] = ["WORKER"]
        provisional = copy.deepcopy(self.identity)
        provisional["trust_level"] = "PROVISIONAL"
        for identity in (worker, provisional):
            with self.assertRaises(ValueError):
                approve_excavate_request(
                    prepared, approval_record=approval, identity=identity,
                    used_nonces=set(), now="2026-09-09T15:02:00Z", root=REPO_ROOT,
                )
        admin = copy.deepcopy(self.identity)
        admin["roles"] = ["LOCAL_ADMIN"]
        admin["windows_binding"]["is_elevated"] = False
        with self.assertRaises(ValueError):
            approve_excavate_request(
                prepared, approval_record=self._approval(prepared, approver_role="LOCAL_ADMIN"),
                identity=admin, used_nonces=set(), now="2026-09-09T15:02:00Z", root=REPO_ROOT,
            )

    def test_expiry_and_in_memory_replay_are_rejected(self):
        prepared = self._prepare()
        approval = self._approval(prepared)
        with self.assertRaises(ValueError):
            approve_excavate_request(
                prepared, approval_record=approval, identity=self.identity,
                used_nonces=set(), now="2026-09-09T15:31:00Z", root=REPO_ROOT,
            )
        used = set()
        approve_excavate_request(
            prepared, approval_record=approval, identity=self.identity,
            used_nonces=used, now="2026-09-09T15:02:00Z", root=REPO_ROOT,
        )
        with self.assertRaises(ValueError):
            approve_excavate_request(
                prepared, approval_record=approval, identity=self.identity,
                used_nonces=used, now="2026-09-09T15:03:00Z", root=REPO_ROOT,
            )

    def test_codex_p1_nonce_file_persists_consumption_and_blocks_replay(self):
        prepared = self._prepare()
        approval = self._approval(prepared)
        with tempfile.TemporaryDirectory() as tmp:
            state_path = Path(tmp) / "nonces.json"
            state_path.write_text('{"used_nonces": []}\n', encoding="utf-8")
            result = approve_excavate_request_with_nonce_file(
                prepared, approval_record=approval, identity=self.identity,
                nonce_state_path=state_path, now="2026-09-09T15:02:00Z", root=REPO_ROOT,
            )
            self.assertEqual(result["status"], "APPROVED_FOR_NORMAL_WORKFLOW")
            state = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertIn(approval["nonce"], state["used_nonces"])
            self.assertFalse(state_path.with_name(state_path.name + ".lock").exists())
            with self.assertRaises(ValueError):
                approve_excavate_request_with_nonce_file(
                    prepared, approval_record=approval, identity=self.identity,
                    nonce_state_path=state_path, now="2026-09-09T15:03:00Z", root=REPO_ROOT,
                )

    def test_machine_schemas_and_module_owners(self):
        for name in ("ContextRef.json", "GraveyardCandidate.json", "GraveyardActivationTicket.json", "GraveyardExcavateRequest.json"):
            schema = json.loads((REPO_ROOT / "schemas/v1" / name).read_text(encoding="utf-8"))
            Draft202012Validator.check_schema(schema)
            self.assertFalse(schema["additionalProperties"])
        registry = json.loads((REPO_ROOT / "modules_registry.json").read_text(encoding="utf-8"))
        expected = {
            "ContextRef": "Context", "GraveyardCandidate": "Context",
            "Identity": "Security", "ApprovalRecord": "Security",
            "GraveyardActivationTicket": "Core", "GraveyardExcavateRequest": "Core",
        }
        for contract, owner in expected.items():
            providers = [m["module_id"] for m in registry["modules"] if contract in m.get("provides_contracts", [])]
            self.assertEqual(providers, [owner])


if __name__ == "__main__":
    unittest.main()
