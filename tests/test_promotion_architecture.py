import json
import re
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, ValidationError

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "schemas" / "v1"


def load_schema(name):
    return json.loads((SCHEMAS / name).read_text(encoding="utf-8"))


class PromotionArchitectureTests(unittest.TestCase):
    def test_promotion_schemas_are_fail_closed(self):
        names = ["PromotionRequest.json", "ChangeEvidence.json", "ImpactAssessment.json", "PromotionTicket.json"]
        for name in names:
            data = load_schema(name)
            Draft202012Validator.check_schema(data)
            self.assertFalse(data["additionalProperties"], name)
            self.assertEqual(data["$schema"], "https://json-schema.org/draft/2020-12/schema")
            self.assertTrue(data["required"], name)

    def test_promotion_events_are_journaled(self):
        data = load_schema("JournalEvent.json")
        events = set(data["properties"]["event_type"]["enum"])
        required = {"PROMOTION_ENQUEUED", "PROMOTION_TICKET_SEALED", "PROMOTION_COMMITTED", "CANDIDATE_STALE", "QA_REUSED"}
        self.assertTrue(required.issubset(events))

    def test_candidate_stale_is_durable_promotion_state(self):
        data = load_schema("PromotionRequest.json")
        states = set(data["properties"]["state"]["enum"])
        self.assertIn("CANDIDATE_STALE", states)

    def test_adr_heading_ids_are_unique(self):
        text = (ROOT / "docs" / "architecture" / "32_ARCHITECTURAL_DECISIONS_AND_OPEN_QUESTIONS.md").read_text(encoding="utf-8")
        ids = re.findall(r"^## .*?ADR-(\d{3})\b", text, flags=re.MULTILINE)
        self.assertEqual(len(ids), len(set(ids)), f"duplicate ADR heading IDs: {ids}")

    def test_promotion_invariants_exist(self):
        text = (ROOT / "docs" / "architecture" / "36_CHANGE_PROMOTION_PROTOCOL.md").read_text(encoding="utf-8")
        for token in ["sealed PromotionTicket", "один target", "AI не может единолично", "Missing capability", "Turbo", "RFC 8785"]:
            self.assertIn(token, text)

    def test_impact_assessment_blocks_unsafe_reuse(self):
        schema = load_schema("ImpactAssessment.json")
        validator = Draft202012Validator(schema)
        base = {
            "impact_assessment_id": "impact-12345678",
            "task_id": "task-090",
            "previous_change_digest": "sha256:" + "1" * 64,
            "current_change_digest": "sha256:" + "1" * 64,
            "target_revision": "abc123",
            "method_level": "L1",
            "impact_level": "NONE",
            "applicability": "APPLICABLE",
            "decision": "QA_REUSE",
            "affected_scopes": [],
            "reasons": ["same change"],
            "decided_at": "2026-09-09T12:00:00Z"
        }
        validator.validate(base)
        unsafe = dict(base, applicability="INDETERMINATE", impact_level="INDETERMINATE")
        with self.assertRaises(ValidationError):
            validator.validate(unsafe)
        missing_reason = dict(base, decision="FULL_QA", applicability="NOT_APPLICABLE", impact_level="MATERIAL")
        with self.assertRaises(ValidationError):
            validator.validate(missing_reason)
        valid_full = dict(missing_reason, full_qa_reason="MATERIAL_CHANGESET_CHANGE")
        validator.validate(valid_full)

    def test_non_safe_ticket_requires_change_evidence(self):
        schema = load_schema("PromotionTicket.json")
        validator = Draft202012Validator(schema)
        base = {
            "promotion_ticket_id": "ptkt-12345678",
            "promotion_id": "promo-12345678",
            "task_id": "task-090",
            "sealed": True,
            "change_ref": "pr:93",
            "change_digest": "sha256:" + "2" * 64,
            "target_ref": "main",
            "target_revision": "abc123",
            "candidate_revision": "def456",
            "risk_class": "SAFE",
            "change_evidence_ref": None,
            "integration_evidence_ref": "evidence:integration-1",
            "security_decision_ref": "security:decision-1",
            "action_hash": "sha256:" + "3" * 64,
            "policy_ref": "policy:promotion",
            "policy_version": "1.0.0",
            "promotion_method": "SQUASH",
            "authorization_mode": "AUTO_POLICY",
            "lease_generation": 1,
            "issued_at": "2026-09-09T12:00:00Z",
            "expires_at": "2026-09-09T13:00:00Z"
        }
        validator.validate(base)
        strict = dict(base, risk_class="STRICT")
        with self.assertRaises(ValidationError):
            validator.validate(strict)
        strict["change_evidence_ref"] = "change-evidence:1"
        strict["authorization_mode"] = "HUMAN_APPROVAL"
        validator.validate(strict)

    def test_security_decision_binds_promotion_action(self):
        schema = load_schema("SecurityDecision.json")
        validator = Draft202012Validator(schema)
        decision = {
            "decision_id": "sec-12345678",
            "task_id": "task-090",
            "worker_id": "execution",
            "action": {"operation": "PROMOTE_CHANGE", "target": "main"},
            "verdict": "ALLOW",
            "decided_at": "2026-09-09T12:00:00Z"
        }
        with self.assertRaises(ValidationError):
            validator.validate(decision)
        decision["action_hash"] = "sha256:" + "4" * 64
        validator.validate(decision)

    def test_reuse_does_not_create_new_change_evidence_mode(self):
        schema = load_schema("ChangeEvidence.json")
        self.assertNotIn("REUSED", schema["properties"]["qa_mode"]["enum"])


    def test_non_safe_ticket_rejects_auto_policy(self):
        schema = load_schema("PromotionTicket.json")
        validator = Draft202012Validator(schema)
        ticket = {
            "promotion_ticket_id": "ptkt-12345678",
            "promotion_id": "promo-12345678",
            "task_id": "task-090",
            "sealed": True,
            "change_ref": "pr:93",
            "change_digest": "sha256:" + "2" * 64,
            "target_ref": "main",
            "target_revision": "abc123",
            "candidate_revision": "def456",
            "risk_class": "STRICT",
            "change_evidence_ref": "change-evidence:1",
            "integration_evidence_ref": "evidence:integration-1",
            "security_decision_ref": "security:decision-1",
            "action_hash": "sha256:" + "3" * 64,
            "policy_ref": "policy:promotion",
            "policy_version": "1.0.0",
            "promotion_method": "SQUASH",
            "authorization_mode": "AUTO_POLICY",
            "lease_generation": 1,
            "issued_at": "2026-09-09T12:00:00Z",
            "expires_at": "2026-09-09T13:00:00Z"
        }
        with self.assertRaises(ValidationError):
            validator.validate(ticket)
        ticket["authorization_mode"] = "HUMAN_APPROVAL"
        validator.validate(ticket)

    def test_material_impact_cannot_reuse_qa(self):
        schema = load_schema("ImpactAssessment.json")
        validator = Draft202012Validator(schema)
        impact = {
            "impact_assessment_id": "impact-12345678",
            "task_id": "task-090",
            "previous_change_digest": "sha256:" + "1" * 64,
            "current_change_digest": "sha256:" + "2" * 64,
            "target_revision": "abc123",
            "method_level": "L2",
            "impact_level": "MATERIAL",
            "applicability": "APPLICABLE",
            "decision": "QA_REUSE",
            "affected_scopes": ["security"],
            "reasons": ["material security delta"],
            "decided_at": "2026-09-09T12:00:00Z"
        }
        with self.assertRaises(ValidationError):
            validator.validate(impact)
        impact["decision"] = "FULL_QA"
        impact["full_qa_reason"] = "MATERIAL_CHANGESET_CHANGE"
        validator.validate(impact)

    def test_done_request_requires_recovery_proof(self):
        schema = load_schema("PromotionRequest.json")
        validator = Draft202012Validator(schema)
        done = {
            "promotion_id": "promo-12345678",
            "task_id": "task-090",
            "change_ref": "pr:93",
            "change_digest": "sha256:" + "2" * 64,
            "target_ref": "main",
            "risk_class": "STRICT",
            "state": "DONE",
            "policy_ref": "policy:promotion",
            "policy_version": "1.0.0",
            "enqueued_at": "2026-09-09T12:00:00Z"
        }
        with self.assertRaises(ValidationError):
            validator.validate(done)
        done.update({
            "target_revision": "abc123",
            "candidate_revision": "def456",
            "integration_evidence_ref": "evidence:integration-1",
            "promotion_ticket_ref": "ticket:1",
            "authorization_evidence_ref": "approval:1",
            "lease_generation": 1
        })
        validator.validate(done)


if __name__ == "__main__":
    unittest.main()
