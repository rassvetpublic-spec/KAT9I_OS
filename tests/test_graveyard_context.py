# -*- coding: utf-8 -*-
"""Негативные и контрактные тесты Graveyard -> Context -> normal workflow (#95)."""

import copy
import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from scripts.graveyard_context import (
    build_work_provenance,
    can_seed_planning,
    confirm_for_normal_workflow,
    create_reactivation_candidate,
    record_canon_check,
    resolve_archive_context,
    validate_candidate_policy,
    validate_context_ref_policy,
)

REPO_ROOT = Path(__file__).resolve().parent.parent


class TestGraveyardContextBoundary(unittest.TestCase):
    def setUp(self):
        manifest = json.loads((REPO_ROOT / "graveyard" / "MANIFEST.json").read_text(encoding="utf-8"))
        self.archive_ids = [entry["archive_id"] for entry in manifest["archives"]]
        self.archive_id = self.archive_ids[0]
        self.fixed_time = "2026-09-09T14:30:00Z"

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

    def test_graveyard_cannot_seed_planning_even_if_flags_are_forged(self):
        ref = resolve_archive_context(self.archive_id, root=REPO_ROOT, retrieved_at=self.fixed_time)
        forged = copy.deepcopy(ref)
        forged["actionable"] = True
        forged["control"] = True
        forged["canonical"] = True
        self.assertFalse(can_seed_planning(forged))
        with self.assertRaises(ValueError):
            validate_context_ref_policy(forged)

    def test_candidate_requires_canon_check_then_owner_confirmation(self):
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
        self.assertEqual(candidate["resurrected_from"], self.archive_id)

        with self.assertRaises(ValueError):
            confirm_for_normal_workflow(candidate, confirmation_ref="owner://confirmation/1")
        with self.assertRaises(ValueError):
            build_work_provenance(candidate)

        checked = record_canon_check(
            candidate,
            status="COMPATIBLE",
            checked_revision="main@0123456789abcdef",
            evidence_ref="evidence://canon-check/1",
            notes="Идея не реализована и не конфликтует с актуальным каноном.",
        )
        self.assertEqual(checked["state"], "AWAITING_OWNER_CONFIRMATION")
        self.assertFalse(checked["actionable"])

        with self.assertRaises(ValueError):
            confirm_for_normal_workflow(checked, confirmation_ref="")

        approved = confirm_for_normal_workflow(checked, confirmation_ref="owner://command/explicit-1")
        self.assertEqual(approved["state"], "APPROVED_FOR_NORMAL_WORKFLOW")
        self.assertFalse(approved["actionable"])
        self.assertFalse(approved["control"])

        provenance = build_work_provenance(approved)
        self.assertEqual(provenance["resurrected_from"], self.archive_id)
        self.assertEqual(provenance["graveyard_candidate_id"], approved["candidate_id"])
        self.assertEqual(provenance["owner_confirmation_ref"], "owner://command/explicit-1")

    def test_conflict_or_superseded_candidate_is_blocked(self):
        for status in ("CONFLICT", "SUPERSEDED", "UNKNOWN"):
            candidate = create_reactivation_candidate(
                self.archive_id,
                f"Идея со статусом {status}",
                root=REPO_ROOT,
                created_at=self.fixed_time,
            )
            blocked = record_canon_check(
                candidate,
                status=status,
                checked_revision="main@0123456789abcdef",
                notes="Fail-closed проверка.",
            )
            self.assertEqual(blocked["state"], "BLOCKED_BY_CANON")
            with self.assertRaises(ValueError):
                confirm_for_normal_workflow(blocked, confirmation_ref="owner://command/2")

    def test_unknown_archive_fails_closed(self):
        with self.assertRaises(ValueError):
            resolve_archive_context("GY-DOES-NOT-EXIST", root=REPO_ROOT, retrieved_at=self.fixed_time)

    def test_candidate_policy_rejects_attempt_to_promote_data(self):
        candidate = create_reactivation_candidate(
            self.archive_id,
            "Проверка DATA/CONTROL boundary",
            root=REPO_ROOT,
            created_at=self.fixed_time,
        )
        forged = copy.deepcopy(candidate)
        forged["actionable"] = True
        with self.assertRaises(ValueError):
            validate_candidate_policy(forged)

    def test_candidate_policy_rejects_provenance_substitution(self):
        candidate = create_reactivation_candidate(
            self.archive_id,
            "Проверка подмены provenance",
            root=REPO_ROOT,
            created_at=self.fixed_time,
        )
        forged = copy.deepcopy(candidate)
        forged["source_ref"] = "ctx-GY-other-archive"
        with self.assertRaises(ValueError):
            validate_candidate_policy(forged)

    def test_candidate_policy_rejects_unknown_state(self):
        candidate = create_reactivation_candidate(
            self.archive_id,
            "Проверка неизвестного состояния",
            root=REPO_ROOT,
            created_at=self.fixed_time,
        )
        forged = copy.deepcopy(candidate)
        forged["state"] = "AUTO_PROMOTED"
        with self.assertRaises(ValueError):
            validate_candidate_policy(forged)

    def test_candidate_policy_rejects_early_owner_confirmation(self):
        candidate = create_reactivation_candidate(
            self.archive_id,
            "Проверка раннего подтверждения",
            root=REPO_ROOT,
            created_at=self.fixed_time,
        )
        forged = copy.deepcopy(candidate)
        forged["owner_confirmation_ref"] = "owner://forged-before-canon-check"
        with self.assertRaises(ValueError):
            validate_candidate_policy(forged)

    def test_machine_schemas_encode_graveyard_boundary(self):
        context_schema = json.loads((REPO_ROOT / "schemas" / "v1" / "ContextRef.json").read_text(encoding="utf-8"))
        candidate_schema = json.loads((REPO_ROOT / "schemas" / "v1" / "GraveyardCandidate.json").read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(context_schema)
        Draft202012Validator.check_schema(candidate_schema)
        self.assertFalse(context_schema["additionalProperties"])
        self.assertFalse(candidate_schema["additionalProperties"])
        self.assertEqual(candidate_schema["properties"]["actionable"]["const"], False)
        self.assertEqual(candidate_schema["properties"]["control"]["const"], False)
        self.assertEqual(candidate_schema["properties"]["requires_owner_confirmation"]["const"], True)

        candidate = create_reactivation_candidate(
            self.archive_id,
            "Проверка схемы кандидата",
            root=REPO_ROOT,
            created_at=self.fixed_time,
        )
        validator = Draft202012Validator(candidate_schema)
        self.assertTrue(validator.is_valid(candidate))

        early_confirmation = copy.deepcopy(candidate)
        early_confirmation["owner_confirmation_ref"] = "owner://forged-before-canon-check"
        self.assertFalse(validator.is_valid(early_confirmation))


if __name__ == "__main__":
    unittest.main()
