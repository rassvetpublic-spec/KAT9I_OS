import tempfile
import unittest
from pathlib import Path

from scripts.qa_evidence_epoch import (
    ATTEST_MARKER,
    COMMAND_MARKER,
    EPOCH_HEADER,
    POLICY_FILES,
    RESULT_MARKER,
    EvidenceEpochError,
    build_snapshot,
    canonical_gate_state,
    canonical_review_state,
    policy_digest,
    render_epoch_section,
    validate_current_epoch,
)


HEAD = "a" * 40
COMMAND_ID = "QAC-135-aaaaaaaa-001"


def threads(nodes=None):
    return {
        "data": {
            "repository": {
                "pullRequest": {
                    "reviewThreads": {
                        "nodes": nodes or [],
                    }
                }
            }
        }
    }


def thread(thread_id="PRRT_1", resolved=False, body="P1 finding", comment_id="PRRC_1"):
    return {
        "id": thread_id,
        "isResolved": resolved,
        "comments": {
            "nodes": [
                {
                    "id": comment_id,
                    "body": body,
                    "path": "scripts/example.py",
                    "line": 10,
                    "startLine": None,
                    "outdated": False,
                }
            ]
        },
    }


def reviews(extra=None):
    return extra or []


def checks(conclusion="success"):
    return {
        "check_runs": [
            {
                "id": 10,
                "name": "Контроль качества репозитория",
                "status": "completed",
                "conclusion": conclusion,
                "completed_at": "2026-09-10T19:00:00Z",
                "app": {"slug": "github-actions"},
            },
            {
                "id": 11,
                "name": "Project synchronize",
                "status": "completed",
                "conclusion": "success",
                "completed_at": "2026-09-10T19:00:01Z",
                "app": {"slug": "github-actions"},
            },
        ]
    }


def statuses(state="success"):
    return {
        "statuses": [
            {
                "id": 20,
                "context": "external-policy",
                "state": state,
                "updated_at": "2026-09-10T19:00:02Z",
            }
        ]
    }


def machine_body(marker, fields, snapshot, tail=""):
    body = marker + "\n" + "\n".join(f"{key}={value}" for key, value in fields.items())
    body += "\n\n" + render_epoch_section(snapshot)
    if tail:
        body += "\n\n" + tail
    return body


def command_body(snapshot):
    return machine_body(
        COMMAND_MARKER,
        {
            "command_id": COMMAND_ID,
            "target_pr": "135",
            "controller": "ChatGPT",
            "executor": "AGY",
            "role": "QA_EXECUTOR",
            "exact_head": HEAD,
        },
        snapshot,
        "SCOPE: test",
    )


def result_body(snapshot, verdict="QA PASS"):
    return machine_body(
        RESULT_MARKER,
        {
            "command_id": COMMAND_ID,
            "target_pr": "135",
            "controller": "ChatGPT",
            "executor": "AGY",
            "role": "QA_EXECUTOR",
            "exact_head": HEAD,
            "verdict": verdict,
        },
        snapshot,
        "FOLLOW_UP_CANDIDATES\n- none",
    )


def attest_body(snapshot, verdict="QA PASS"):
    return machine_body(
        ATTEST_MARKER,
        {
            "command_id": COMMAND_ID,
            "target_pr": "135",
            "controller": "ChatGPT",
            "executor": "AGY",
            "role": "QA_EXECUTOR",
            "review_id": "9001",
            "exact_head": HEAD,
            "verdict": verdict,
        },
        snapshot,
        "Controller attestation",
    )


def comments(snapshot):
    return [
        {
            "id": 1001,
            "author_association": "OWNER",
            "body": command_body(snapshot),
            "created_at": "2026-09-10T19:01:00Z",
        }
    ]


def qa_review(snapshot, verdict="QA PASS"):
    return {
        "id": 9001,
        "body": result_body(snapshot, verdict=verdict),
        "author_association": "OWNER",
        "commit_id": HEAD,
        "state": "COMMENTED",
    }


def event(snapshot, verdict="QA PASS"):
    return {"comment": {"body": attest_body(snapshot, verdict=verdict)}}


class QaEvidenceEpochTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        for index, relative in enumerate(POLICY_FILES):
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"policy-{index}\n", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def snapshot(self, review_threads=None, review_list=None, check_payload=None, status_payload=None):
        return build_snapshot(
            HEAD,
            review_threads if review_threads is not None else threads(),
            review_list if review_list is not None else reviews(),
            check_payload if check_payload is not None else checks(),
            status_payload if status_payload is not None else statuses(),
            self.root,
        )

    def validate(self, snapshot, review_threads=None, review_list=None, check_payload=None, status_payload=None, verdict="QA PASS"):
        return validate_current_epoch(
            command_id=COMMAND_ID,
            comments_payload=comments(snapshot),
            review_payload=qa_review(snapshot, verdict=verdict),
            event_payload=event(snapshot, verdict=verdict),
            current_head=HEAD,
            threads_payload=review_threads if review_threads is not None else threads(),
            reviews_payload=review_list if review_list is not None else reviews(),
            checks_payload=check_payload if check_payload is not None else checks(),
            statuses_payload=status_payload if status_payload is not None else statuses(),
            root=self.root,
        )

    def test_unchanged_epoch_accepts_pass(self):
        snapshot = self.snapshot()
        resolved = self.validate(snapshot)
        self.assertEqual("FRESH", resolved["decision"])
        self.assertEqual(snapshot["evidence_digest"], resolved["evidence_digest"])

    def test_pr131_race_new_review_thread_invalidates_pass(self):
        snapshot = self.snapshot()
        changed = threads([thread()])
        with self.assertRaisesRegex(EvidenceEpochError, "REVIEW_DRIFT"):
            self.validate(snapshot, review_threads=changed)

    def test_resolving_existing_thread_changes_epoch(self):
        before = threads([thread(resolved=False)])
        snapshot = self.snapshot(review_threads=before)
        after = threads([thread(resolved=True)])
        with self.assertRaisesRegex(EvidenceEpochError, "REVIEW_DRIFT"):
            self.validate(snapshot, review_threads=after)

    def test_external_review_submission_changes_epoch_but_qa_result_is_excluded(self):
        snapshot = self.snapshot()
        external = [{"id": 33, "state": "CHANGES_REQUESTED", "commit_id": HEAD, "body": "needs work"}]
        with self.assertRaisesRegex(EvidenceEpochError, "REVIEW_DRIFT"):
            self.validate(snapshot, review_list=external)
        qa_only = [{"id": 9001, "state": "COMMENTED", "commit_id": HEAD, "body": result_body(snapshot)}]
        self.assertEqual(
            canonical_review_state(threads(), []),
            canonical_review_state(threads(), qa_only),
        )

    def test_gate_state_change_invalidates_pass(self):
        snapshot = self.snapshot()
        with self.assertRaisesRegex(EvidenceEpochError, "GATE_DRIFT"):
            self.validate(snapshot, check_payload=checks(conclusion="failure"))
        with self.assertRaisesRegex(EvidenceEpochError, "GATE_DRIFT"):
            self.validate(snapshot, status_payload=statuses(state="failure"))

    def test_policy_change_invalidates_pass(self):
        snapshot = self.snapshot()
        (self.root / "QA_PROTOCOL.md").write_text("changed-policy\n", encoding="utf-8")
        with self.assertRaisesRegex(EvidenceEpochError, "POLICY_DRIFT"):
            self.validate(snapshot)

    def test_head_change_invalidates_before_other_components(self):
        snapshot = self.snapshot()
        with self.assertRaisesRegex(EvidenceEpochError, "HEAD_DRIFT"):
            validate_current_epoch(
                command_id=COMMAND_ID,
                comments_payload=comments(snapshot),
                review_payload=qa_review(snapshot),
                event_payload=event(snapshot),
                current_head="b" * 40,
                threads_payload=threads(),
                reviews_payload=reviews(),
                checks_payload=checks(),
                statuses_payload=statuses(),
                root=self.root,
            )

    def test_blocking_verdict_can_publish_block_even_when_review_state_changed(self):
        snapshot = self.snapshot()
        resolved = self.validate(snapshot, review_threads=threads([thread()]), verdict="CHANGES REQUESTED")
        self.assertEqual("BLOCKING_VERDICT_SAFE", resolved["decision"])

    def test_snapshot_is_order_independent(self):
        a = thread(thread_id="PRRT_A", comment_id="PRRC_A")
        b = thread(thread_id="PRRT_B", comment_id="PRRC_B")
        left = self.snapshot(review_threads=threads([a, b]))
        right = self.snapshot(review_threads=threads([b, a]))
        self.assertEqual(left["review_digest"], right["review_digest"])
        self.assertEqual(left["evidence_digest"], right["evidence_digest"])

    def test_duplicate_epoch_section_is_malformed(self):
        snapshot = self.snapshot()
        bad = qa_review(snapshot)
        bad["body"] += "\n\n" + EPOCH_HEADER + "\nepoch_version=1"
        with self.assertRaisesRegex(EvidenceEpochError, "MALFORMED_EVIDENCE"):
            validate_current_epoch(
                command_id=COMMAND_ID,
                comments_payload=comments(snapshot),
                review_payload=bad,
                event_payload=event(snapshot),
                current_head=HEAD,
                threads_payload=threads(),
                reviews_payload=reviews(),
                checks_payload=checks(),
                statuses_payload=statuses(),
                root=self.root,
            )

    def test_gate_canonicalization_ignores_same_result_rerun_id(self):
        first = checks()
        rerun = checks()
        rerun["check_runs"][0] = {
            **rerun["check_runs"][0],
            "id": 999,
            "completed_at": "2026-09-10T19:30:00Z",
        }
        self.assertEqual(canonical_gate_state(first, statuses()), canonical_gate_state(rerun, statuses()))

    def test_policy_digest_machine_receipt(self):
        root = Path(__file__).resolve().parents[1]
        digest = policy_digest(root)
        self.assertRegex(digest, r"^[0-9a-f]{64}$")
        print(f"KAT9I_POLICY_DIGEST={digest}")

    def test_workflow_revalidates_epoch_immediately_before_fast_publication(self):
        workflow = (Path(__file__).resolve().parents[1] / ".github" / "workflows" / "qa-result-bridge.yml").read_text(encoding="utf-8")
        self.assertIn("reviewThreads", workflow)
        self.assertGreaterEqual(workflow.count("qa_evidence_epoch.py validate"), 2)
        self.assertIn("checks: read", workflow)
        self.assertIn("statuses: read", workflow)


if __name__ == "__main__":
    unittest.main()
