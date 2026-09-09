# -*- coding: utf-8 -*-
"""Негативные и контрактные тесты Graveyard -> Context -> Approval -> normal workflow (#95)."""

import copy
import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from scripts.graveyard_context import (
    activation_action_hash,
    build_work_provenance,
    can_seed_planning,
    create_reactivation_candidate,
    record_canon_check,
    resolve_archive_context,
    validate_candidate_policy,
    validate_context_ref_policy,
)
from scripts.graveyard_excavate import approve_excavate_request, prepare_excavate_request

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
            "reason": "Явно разрешаю переход этого exact ticket в обычный workflow.",
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
            self.assertEqual(ref["access"], "read")
            self.assertEqual(ref["provenance"]["transformation"], "none")
            self.assertFalse(can_seed_planning(ref))

    def test_codex_p1_graveyard_cannot_seed_after_source_class_forgery(self):
        ref = resolve_archive_context(self.archive_id, root=REPO_ROOT, retrieved_at=self.fixed_time)
        forged = copy.deepcopy(ref)
        forged["source_class"] = "history"
        forged["actionable"] = True
        forged["control"] = True
        forged["canonical"] = True
        self.assertFalse(can_seed_planning(forged))
        with self.assertRaises(ValueError):
            validate_context_ref_policy(forged)

    def test_candidate_remains_data_before_and_after_canon_check(self):
        candidate = create_reactivation_candidate(
            self.archive_id,
            "Проверить историческую идею повторно",
            selector="section:3.1",
            root=REPO_ROOT,
            created_at=self.fixed_time,
        )
        self.assertEqual(candidate["state"], "CANDIDATE")
        self.assertFalse(candidate["actionable"])
        self.assertFalse(candidate["control"])
        self.assertIsNone(candidate["activation_ref"])
        self.assertIsNone(candidate["owner_confirmation_ref"])

        checked = record_canon_check(
            candidate,
            status="COMPATIBLE",
            checked_revision=self.checked_revision,
            root=REPO_ROOT,
        )
        self.assertEqual(checked["state"], "AWAITING_OWNER_CONFIRMATION")
        self.assertFalse(checked["actionable"])
        self.assertFalse(checked["control"])
        with self.assertRaises(ValueError):
            build_work_provenance(checked)

    def test_codex_p1_checked_revision_is_required_after_canon_check(self):
        candidate = create_reactivation_candidate(
            self.archive_id,
            "Проверка обязательной revision",
            root=REPO_ROOT,
            created_at=self.fixed_time,
        )
        forged = copy.deepcopy(candidate)
        forged["state"] = "AWAITING_OWNER_CONFIRMATION"
        forged["canon_check"]["status"] = "COMPATIBLE"
        forged["canon_check"]["checked_revision"] = None
        with self.assertRaises(ValueError):
            validate_candidate_policy(forged)

        schema = json.loads((REPO_ROOT / "schemas" / "v1" / "GraveyardCandidate.json").read_text(encoding="utf-8"))
        self.assertFalse(Draft202012Validator(schema).is_valid(forged))

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
            self.assertIsNone(result["approval_action_hash"])
            self.assertFalse(result["side_effect_performed"])

    def test_unknown_archive_fails_closed(self):
        with self.assertRaises(ValueError):
            resolve_archive_context("GY-DOES-NOT-EXIST", root=REPO_ROOT, retrieved_at=self.fixed_time)

    def test_candidate_policy_rejects_data_promotion_and_provenance_substitution(self):
        candidate = create_reactivation_candidate(
            self.archive_id,
            "Проверка DATA/CONTROL boundary",
            root=REPO_ROOT,
            created_at=self.fixed_time,
        )
        promoted = copy.deepcopy(candidate)
        promoted["actionable"] = True
        with self.assertRaises(ValueError):
            validate_candidate_policy(promoted)

        substituted = copy.deepcopy(candidate)
        substituted["source_ref"] = "ctx-GY-other-archive"
        with self.assertRaises(ValueError):
            validate_candidate_policy(substituted)

    def test_candidate_policy_rejects_unknown_state_and_early_confirmation(self):
        candidate = create_reactivation_candidate(
            self.archive_id,
            "Проверка состояния",
            root=REPO_ROOT,
            created_at=self.fixed_time,
        )
        unknown = copy.deepcopy(candidate)
        unknown["state"] = "AUTO_PROMOTED"
        with self.assertRaises(ValueError):
            validate_candidate_policy(unknown)

        early = copy.deepcopy(candidate)
        early["activation_ref"] = "gya-0123456789abcdef"
        early["owner_confirmation_ref"] = "appr-graveyard123456"
        with self.assertRaises(ValueError):
            validate_candidate_policy(early)

    def test_prepare_command_returns_exact_ticket_hash_without_side_effect(self):
        prepared = self._prepare()
        self.assertEqual(prepared["status"], "AWAITING_OWNER_CONFIRMATION")
        self.assertFalse(prepared["side_effect_performed"])
        self.assertEqual(prepared["approval_action_hash"], activation_action_hash(prepared["activation_ticket"], root=REPO_ROOT))
        self.assertTrue(prepared["approval_action_hash"].startswith("sha256:"))
        self.assertEqual(prepared["activation_ticket"]["candidate_id"], prepared["candidate"]["candidate_id"])
        self.assertEqual(prepared["activation_ticket"]["canon_checked_revision"], self.checked_revision)

    def test_valid_human_approval_allows_only_provenance_handoff(self):
        prepared = self._prepare()
        approval = self._approval(prepared)
        used_nonces = set()
        result = approve_excavate_request(
            prepared,
            approval_record=approval,
            identity=self.identity,
            used_nonces=used_nonces,
            now="2026-09-09T15:02:00Z",
            root=REPO_ROOT,
        )
        self.assertEqual(result["status"], "APPROVED_FOR_NORMAL_WORKFLOW")
        self.assertFalse(result["side_effect_performed"])
        self.assertFalse(result["candidate"]["actionable"])
        self.assertFalse(result["candidate"]["control"])
        self.assertEqual(result["candidate"]["activation_ref"], prepared["activation_ticket"]["activation_id"])
        self.assertEqual(result["candidate"]["owner_confirmation_ref"], approval["approval_id"])
        self.assertEqual(result["provenance"]["approval_id"], approval["approval_id"])
        self.assertEqual(result["provenance"]["activation_ticket_id"], prepared["activation_ticket"]["activation_id"])
        self.assertIn(approval["nonce"], used_nonces)

    def test_wrong_action_hash_is_rejected(self):
        prepared = self._prepare()
        approval = self._approval(prepared, action_hash="sha256:" + "0" * 64)
        with self.assertRaises(ValueError):
            approve_excavate_request(
                prepared,
                approval_record=approval,
                identity=self.identity,
                used_nonces=set(),
                now="2026-09-09T15:02:00Z",
                root=REPO_ROOT,
            )

    def test_wrong_task_or_identity_is_rejected(self):
        prepared = self._prepare()
        wrong_task = self._approval(prepared, task_id="another-review-task")
        with self.assertRaises(ValueError):
            approve_excavate_request(
                prepared,
                approval_record=wrong_task,
                identity=self.identity,
                used_nonces=set(),
                now="2026-09-09T15:02:00Z",
                root=REPO_ROOT,
            )

        wrong_identity = self._approval(prepared, approver_identity_id="id-other12345678")
        with self.assertRaises(ValueError):
            approve_excavate_request(
                prepared,
                approval_record=wrong_identity,
                identity=self.identity,
                used_nonces=set(),
                now="2026-09-09T15:02:00Z",
                root=REPO_ROOT,
            )

    def test_worker_or_provisional_identity_cannot_approve(self):
        prepared = self._prepare()
        approval = self._approval(prepared)

        worker = copy.deepcopy(self.identity)
        worker["subject_type"] = "LOCAL_WORKER"
        worker["roles"] = ["WORKER"]
        with self.assertRaises(ValueError):
            approve_excavate_request(
                prepared,
                approval_record=approval,
                identity=worker,
                used_nonces=set(),
                now="2026-09-09T15:02:00Z",
                root=REPO_ROOT,
            )

        provisional = copy.deepcopy(self.identity)
        provisional["trust_level"] = "PROVISIONAL"
        with self.assertRaises(ValueError):
            approve_excavate_request(
                prepared,
                approval_record=approval,
                identity=provisional,
                used_nonces=set(),
                now="2026-09-09T15:02:00Z",
                root=REPO_ROOT,
            )

    def test_local_admin_requires_elevation(self):
        prepared = self._prepare()
        admin_identity = copy.deepcopy(self.identity)
        admin_identity["roles"] = ["LOCAL_ADMIN"]
        admin_identity["windows_binding"]["is_elevated"] = False
        approval = self._approval(prepared, approver_role="LOCAL_ADMIN")
        with self.assertRaises(ValueError):
            approve_excavate_request(
                prepared,
                approval_record=approval,
                identity=admin_identity,
                used_nonces=set(),
                now="2026-09-09T15:02:00Z",
                root=REPO_ROOT,
            )

    def test_expired_ticket_or_approval_is_rejected(self):
        prepared = self._prepare()
        approval = self._approval(prepared)
        with self.assertRaises(ValueError):
            approve_excavate_request(
                prepared,
                approval_record=approval,
                identity=self.identity,
                used_nonces=set(),
                now="2026-09-09T15:31:00Z",
                root=REPO_ROOT,
            )

        expired_approval = self._approval(prepared, expires_at="2026-09-09T15:01:30Z")
        with self.assertRaises(ValueError):
            approve_excavate_request(
                prepared,
                approval_record=expired_approval,
                identity=self.identity,
                used_nonces=set(),
                now="2026-09-09T15:02:00Z",
                root=REPO_ROOT,
            )

    def test_replay_same_nonce_is_rejected(self):
        prepared = self._prepare()
        approval = self._approval(prepared)
        used_nonces = set()
        approve_excavate_request(
            prepared,
            approval_record=approval,
            identity=self.identity,
            used_nonces=used_nonces,
            now="2026-09-09T15:02:00Z",
            root=REPO_ROOT,
        )
        with self.assertRaises(ValueError):
            approve_excavate_request(
                prepared,
                approval_record=approval,
                identity=self.identity,
                used_nonces=used_nonces,
                now="2026-09-09T15:03:00Z",
                root=REPO_ROOT,
            )

    def test_machine_schemas_encode_full_graveyard_boundary(self):
        names = (
            "ContextRef.json",
            "GraveyardCandidate.json",
            "GraveyardActivationTicket.json",
            "GraveyardExcavateRequest.json",
        )
        schemas = {}
        for name in names:
            schema = json.loads((REPO_ROOT / "schemas" / "v1" / name).read_text(encoding="utf-8"))
            Draft202012Validator.check_schema(schema)
            self.assertFalse(schema["additionalProperties"])
            schemas[name] = schema

        self.assertEqual(schemas["GraveyardCandidate.json"]["properties"]["actionable"]["const"], False)
        self.assertEqual(schemas["GraveyardActivationTicket.json"]["properties"]["control"]["const"], False)
        self.assertEqual(schemas["GraveyardExcavateRequest.json"]["properties"]["command"]["const"], "EXCAVATE_IDEA")

        prepared = self._prepare()
        self.assertTrue(Draft202012Validator(schemas["GraveyardActivationTicket.json"]).is_valid(prepared["activation_ticket"]))
        self.assertTrue(Draft202012Validator(schemas["GraveyardExcavateRequest.json"]).is_valid(self.request))

    def test_contracts_have_single_canonical_module_owner(self):
        registry = json.loads((REPO_ROOT / "modules_registry.json").read_text(encoding="utf-8"))
        expected = {
            "ContextRef": "Context",
            "GraveyardCandidate": "Context",
            "Identity": "Security",
            "ApprovalRecord": "Security",
            "GraveyardActivationTicket": "Core",
            "GraveyardExcavateRequest": "Core",
        }
        for contract, owner in expected.items():
            providers = [m["module_id"] for m in registry["modules"] if contract in m.get("provides_contracts", [])]
            self.assertEqual(providers, [owner], f"{contract} должен иметь ровно одного владельца {owner}")

        context = next(m for m in registry["modules"] if m["module_id"] == "Context")
        security = next(m for m in registry["modules"] if m["module_id"] == "Security")
        core = next(m for m in registry["modules"] if m["module_id"] == "Core")
        self.assertIn("NON_ACTIONABLE_CONTEXT_FILTERING", context["capabilities"])
        self.assertIn("HUMAN_APPROVAL_VALIDATION", security["capabilities"])
        self.assertIn("GRAVEYARD_REACTIVATION_ORCHESTRATION", core["capabilities"])


if __name__ == "__main__":
    unittest.main()
