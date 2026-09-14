import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] if "tests" in Path(__file__).parts else Path(__file__).resolve().parent
SCRIPTS = ROOT / "scripts" if (ROOT / "scripts").exists() else ROOT
sys.path.insert(0, str(SCRIPTS))

from final_action_gate import canonical_action_payload, compute_action_hash, evaluate
from final_action_gate_github import build_snapshot

NOW = datetime(2026, 9, 14, 10, 0, tzinfo=timezone.utc)
HEAD = "a" * 40
TARGET = "b" * 40


def github_pr(*, target_revision=TARGET, target_is_ancestor=True):
    return {
        "number": 195,
        "head": {"sha": HEAD},
        "base": {"ref": "main", "sha": target_revision},
        "kat9i_target_is_ancestor": target_is_ancestor,
    }


def quality_check(*, check_id=100, target_revision=TARGET, completed_at="2026-09-14T09:00:00Z"):
    return {
        "id": check_id,
        "name": "Базовые проверки качества и целостности",
        "head_sha": HEAD,
        "conclusion": "success",
        "completed_at": completed_at,
        "pull_requests": [{
            "number": 195,
            "head": {"sha": HEAD},
            "base": {"ref": "main", "sha": target_revision},
        }],
    }


def valid_snapshot():
    payload = canonical_action_payload(
        operation="PROMOTE_CHANGE",
        subject_ref="pr:195",
        subject_revision=HEAD,
        target_ref="main",
        target_revision=TARGET,
        policy_ref="policy:final-action-gate",
        policy_version="0.1.0",
        evidence_digest="sha256:" + "9" * 64,
    )
    action_hash = compute_action_hash(payload)
    return {
        "schema": 1,
        "operation": "PROMOTE_CHANGE",
        "action_hash": action_hash,
        "evidence_digest": "sha256:" + "9" * 64,
        "subject": {"ref": "pr:195", "revision": HEAD},
        "target": {"ref": "main", "revision": TARGET},
        "live": {"subject_revision": HEAD, "target_revision": TARGET},
        "policy": {"ref": "policy:final-action-gate", "version": "0.1.0"},
        "qa": {"verdict": "PASS", "subject_revision": HEAD},
        "integration": {"verdict": "PASS", "subject_revision": HEAD, "target_revision": TARGET},
        "authorization": {
            "verdict": "ALLOW",
            "action_hash": action_hash,
            "subject_revision": HEAD,
            "target_ref": "main",
            "target_revision": TARGET,
            "issued_at": "2026-09-14T09:00:00Z",
            "expires_at": "2026-09-14T21:00:00Z",
        },
    }


class FinalActionGateTests(unittest.TestCase):
    def test_allows_exact_fresh_authorized_action(self):
        self.assertEqual(evaluate(valid_snapshot(), now=NOW)["decision"], "ALLOW")

    def test_incident_regression_qa_pass_without_mtd_is_forbidden(self):
        data = valid_snapshot()
        data["authorization"] = None
        result = evaluate(data, now=NOW)
        self.assertEqual(result["decision"], "DENY")
        self.assertIn("AUTHORIZATION_MISSING", result["reason_codes"])

    def test_target_drift_is_stale(self):
        data = valid_snapshot()
        data["live"]["target_revision"] = "c" * 40
        result = evaluate(data, now=NOW)
        self.assertEqual(result["decision"], "STALE")
        self.assertIn("TARGET_DRIFT", result["reason_codes"])

    def test_head_drift_is_stale(self):
        data = valid_snapshot()
        data["live"]["subject_revision"] = "c" * 40
        self.assertEqual(evaluate(data, now=NOW)["decision"], "STALE")

    def test_replayed_authorization_for_old_head_is_denied(self):
        data = valid_snapshot()
        data["authorization"]["subject_revision"] = "c" * 40
        result = evaluate(data, now=NOW)
        self.assertEqual(result["decision"], "DENY")
        self.assertIn("AUTHORIZATION_SUBJECT_MISMATCH", result["reason_codes"])

    def test_expired_authorization_is_denied(self):
        data = valid_snapshot()
        data["authorization"]["expires_at"] = "2026-09-14T09:30:00Z"
        result = evaluate(data, now=NOW)
        self.assertEqual(result["decision"], "DENY")
        self.assertIn("AUTHORIZATION_EXPIRED", result["reason_codes"])

    def test_action_hash_mismatch_is_denied(self):
        data = valid_snapshot()
        data["action_hash"] = "sha256:" + "0" * 64
        self.assertEqual(evaluate(data, now=NOW)["decision"], "DENY")

    def test_github_adapter_requires_owner_structured_mtd(self):
        checks = {"check_runs": [quality_check()]}
        qa = {"id": 1, "author_association": "OWNER", "created_at": "2026-09-14T09:00:00Z", "body": f"FAST-QA-PASS | worker=ChatGPT | qa=AGY | head={HEAD}"}
        snapshot = build_snapshot(github_pr(), [qa], checks)
        self.assertEqual(evaluate(snapshot, now=NOW)["decision"], "DENY")

        action_hash = snapshot["action_hash"]
        mtd = {
            "id": 2,
            "author_association": "OWNER",
            "created_at": "2026-09-14T09:10:00Z",
            "body": "\n".join([
                "KAT9I-CONTROL/1 | OWNER-MTD",
                "target_pr=195",
                f"exact_head={HEAD}",
                "target_ref=main",
                f"target_revision={TARGET}",
                f"gate_evidence_digest={snapshot['evidence_digest']}",
                f"action_hash={action_hash}",
                "issued_at=2026-09-14T09:10:00Z",
                "expires_at=2026-09-14T21:10:00Z",
            ]),
        }
        snapshot = build_snapshot(github_pr(), [qa, mtd], checks)
        self.assertEqual(evaluate(snapshot, now=NOW)["decision"], "ALLOW")

    def test_non_owner_mtd_is_ignored(self):
        checks = {"check_runs": [quality_check()]}
        base = build_snapshot(github_pr(), [], checks)
        mtd = {
            "id": 2,
            "author_association": "CONTRIBUTOR",
            "created_at": "2026-09-14T09:10:00Z",
            "body": "\n".join([
                "KAT9I-CONTROL/1 | OWNER-MTD",
                "target_pr=195",
                f"exact_head={HEAD}",
                "target_ref=main",
                f"target_revision={TARGET}",
                f"gate_evidence_digest={base['evidence_digest']}",
                f"action_hash={base['action_hash']}",
            ]),
        }
        self.assertIsNone(build_snapshot(github_pr(), [mtd], checks)["authorization"])

    def test_new_evidence_invalidates_old_mtd(self):
        checks = {"check_runs": [quality_check()]}
        qa = {"id": 1, "author_association": "OWNER", "created_at": "2026-09-14T09:00:00Z", "body": f"FAST-QA-PASS | worker=ChatGPT | qa=AGY | head={HEAD}"}
        base = build_snapshot(github_pr(), [qa], checks)
        mtd = {
            "id": 2,
            "author_association": "OWNER",
            "created_at": "2026-09-14T09:10:00Z",
            "body": "\n".join([
                "KAT9I-CONTROL/1 | OWNER-MTD",
                "target_pr=195",
                f"exact_head={HEAD}",
                "target_ref=main",
                f"target_revision={TARGET}",
                f"gate_evidence_digest={base['evidence_digest']}",
                f"action_hash={base['action_hash']}",
            ]),
        }
        self.assertIsNotNone(build_snapshot(github_pr(), [qa, mtd], checks)["authorization"])
        checks["check_runs"].append(quality_check(check_id=101, completed_at="2026-09-14T09:20:00Z"))
        refreshed = build_snapshot(github_pr(), [qa, mtd], checks)
        self.assertIsNone(refreshed["authorization"])
        self.assertNotEqual(base["evidence_digest"], refreshed["evidence_digest"])

    def test_fast_marker_without_agy_is_not_qa_evidence(self):
        checks = {"check_runs": [quality_check()]}
        fake_fast = {"id": 1, "author_association": "OWNER", "created_at": "2026-09-14T09:00:00Z", "body": f"FAST-QA-PASS | worker=ChatGPT | qa=OTHER | head={HEAD}"}
        snapshot = build_snapshot(github_pr(), [fake_fast], checks)
        self.assertEqual(snapshot["qa"]["verdict"], "BLOCKED")
        self.assertEqual(evaluate(snapshot, now=NOW)["decision"], "DENY")

    def test_old_quality_target_is_not_integration_evidence(self):
        checks = {"check_runs": [quality_check(target_revision="c" * 40)]}
        qa = {"id": 1, "author_association": "OWNER", "created_at": "2026-09-14T09:00:00Z", "body": f"FAST-QA-PASS | worker=ChatGPT | qa=AGY | head={HEAD}"}
        snapshot = build_snapshot(github_pr(), [qa], checks)
        self.assertEqual(snapshot["integration"]["verdict"], "BLOCKED")
        self.assertIn("INTEGRATION_NOT_PASS", evaluate(snapshot, now=NOW)["reason_codes"])

    def test_target_not_ancestor_is_not_integration_evidence(self):
        checks = {"check_runs": [quality_check()]}
        qa = {"id": 1, "author_association": "OWNER", "created_at": "2026-09-14T09:00:00Z", "body": f"FAST-QA-PASS | worker=ChatGPT | qa=AGY | head={HEAD}"}
        snapshot = build_snapshot(github_pr(target_is_ancestor=False), [qa], checks)
        self.assertEqual(snapshot["integration"]["verdict"], "BLOCKED")
        self.assertIn("INTEGRATION_NOT_PASS", evaluate(snapshot, now=NOW)["reason_codes"])

    def test_workflow_uses_trusted_default_branch_and_no_pr_checkout(self):
        workflow = ROOT / ".github" / "workflows" / "final-action-gate.yml"
        if not workflow.exists():
            self.skipTest("workflow fixture not present in local isolated run")
        text = workflow.read_text(encoding="utf-8")
        self.assertIn("pull_request_target:", text)
        self.assertIn("ref: ${{ github.event.repository.default_branch }}", text)
        self.assertIn("compare/${TARGET_SHA}...${HEAD_SHA}", text)
        self.assertNotIn("github.event.pull_request.head.sha }}", text)


if __name__ == "__main__":
    unittest.main()
