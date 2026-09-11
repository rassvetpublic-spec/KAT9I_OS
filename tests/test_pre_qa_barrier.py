from __future__ import annotations

import unittest

from scripts.pre_qa_barrier import (
    AUTHORITY,
    PreQaBarrierError,
    evaluate,
    parse_barrier_section,
    render_barrier_section,
)
from scripts.required_check_state import QUALITY_WORKFLOW_NAME, QUALITY_WORKFLOW_PATH

HEAD = "a" * 40


def current_pr(*, head: str = HEAD, state: str = "open", draft: bool = False, number: int = 137) -> dict:
    return {"number": number, "state": state, "draft": draft, "head": {"sha": head}}


def quality_run(
    *,
    head: str = HEAD,
    conclusion: str = "success",
    status: str = "completed",
    number: int = 137,
    name: str = QUALITY_WORKFLOW_NAME,
    path: str = QUALITY_WORKFLOW_PATH,
) -> dict:
    return {
        "id": 12345,
        "name": name,
        "path": path,
        "head_sha": head,
        "status": status,
        "conclusion": conclusion,
        "pull_requests": [{"number": number}],
    }


def thread(thread_id: str, *, resolved: bool) -> dict:
    return {
        "id": thread_id,
        "isResolved": resolved,
        "comments": {"nodes": [{"id": thread_id + "-c"}], "pageInfo": {"hasNextPage": False}},
    }


def review_threads(*nodes: dict, number: int = 137, has_next: bool = False) -> dict:
    return {
        "data": {
            "repository": {
                "pullRequest": {
                    "number": number,
                    "reviewThreads": {
                        "nodes": list(nodes),
                        "pageInfo": {"hasNextPage": has_next},
                    },
                }
            }
        }
    }


class PreQaBarrierTests(unittest.TestCase):
    def test_valid_barrier_produces_validation_only_receipt(self) -> None:
        result = evaluate(current_pr(), review_threads(), quality_run(), "ChatGPT", "Antigravity (AGY)")
        self.assertEqual(result["verdict"], "PASS")
        self.assertEqual(result["authority"], AUTHORITY)
        self.assertEqual(result["exact_head"], HEAD)
        self.assertEqual(result["qa"], "AGY")
        self.assertEqual(result["blocking_threads"], 0)
        self.assertEqual(len(result["receipt_digest"]), 64)

    def test_unresolved_thread_blocks_before_qa(self) -> None:
        payload = review_threads(thread("T1", resolved=False), thread("T2", resolved=True))
        with self.assertRaisesRegex(PreQaBarrierError, "PRE_QA_BLOCKED.*T1"):
            evaluate(current_pr(), payload, quality_run(), "ChatGPT", "AGY")

    def test_incomplete_thread_or_comment_inventory_fails_closed(self) -> None:
        with self.assertRaisesRegex(PreQaBarrierError, "INVENTORY_INCOMPLETE"):
            evaluate(current_pr(), review_threads(has_next=True), quality_run(), "ChatGPT", "AGY")
        nested = review_threads(thread("T1", resolved=True))
        nested["data"]["repository"]["pullRequest"]["reviewThreads"]["nodes"][0]["comments"]["pageInfo"]["hasNextPage"] = True
        with self.assertRaisesRegex(PreQaBarrierError, "INVENTORY_INCOMPLETE"):
            evaluate(current_pr(), nested, quality_run(), "ChatGPT", "AGY")

    def test_quality_must_be_successful_on_exact_head_and_target_pr(self) -> None:
        with self.assertRaisesRegex(PreQaBarrierError, "QUALITY_STALE"):
            evaluate(current_pr(), review_threads(), quality_run(head="b" * 40), "ChatGPT", "AGY")
        with self.assertRaisesRegex(PreQaBarrierError, "QUALITY_FAIL"):
            evaluate(current_pr(), review_threads(), quality_run(conclusion="failure"), "ChatGPT", "AGY")
        with self.assertRaisesRegex(PreQaBarrierError, "another PR"):
            evaluate(current_pr(), review_threads(), quality_run(number=999), "ChatGPT", "AGY")

    def test_quality_requires_both_canonical_path_and_name(self) -> None:
        with self.assertRaisesRegex(PreQaBarrierError, "QUALITY_MISMATCH"):
            evaluate(
                current_pr(),
                review_threads(),
                quality_run(path=".github/workflows/not-quality.yml"),
                "ChatGPT",
                "AGY",
            )
        with self.assertRaisesRegex(PreQaBarrierError, "QUALITY_MISMATCH"):
            evaluate(
                current_pr(),
                review_threads(),
                quality_run(name="Другой workflow"),
                "ChatGPT",
                "AGY",
            )

    def test_worker_and_qa_must_be_separate(self) -> None:
        with self.assertRaisesRegex(PreQaBarrierError, "ROLE_COLLISION"):
            evaluate(current_pr(), review_threads(), quality_run(), "AGY", "Antigravity")

    def test_draft_closed_or_malformed_head_cannot_enter_qa(self) -> None:
        with self.assertRaisesRegex(PreQaBarrierError, "draft PR"):
            evaluate(current_pr(draft=True), review_threads(), quality_run(), "ChatGPT", "AGY")
        with self.assertRaisesRegex(PreQaBarrierError, "not open"):
            evaluate(current_pr(state="closed"), review_threads(), quality_run(), "ChatGPT", "AGY")
        with self.assertRaisesRegex(PreQaBarrierError, "HEAD_MALFORMED"):
            evaluate(current_pr(head="ABC"), review_threads(), quality_run(head="ABC"), "ChatGPT", "AGY")

    def test_receipt_roundtrip_is_deterministic(self) -> None:
        receipt = evaluate(current_pr(), review_threads(), quality_run(), "ChatGPT", "AGY")
        section = render_barrier_section(receipt)
        parsed = parse_barrier_section("prefix\n\n" + section + "\n\nSCOPE")
        self.assertEqual(parsed["receipt_digest"], receipt["receipt_digest"])
        self.assertEqual(parsed["exact_head"], HEAD)

    def test_receipt_duplicate_unknown_unicode_and_digest_tamper_fail_closed(self) -> None:
        receipt = evaluate(current_pr(), review_threads(), quality_run(), "ChatGPT", "AGY")
        section = render_barrier_section(receipt)
        duplicate = section.replace("worker=ChatGPT", "worker=ChatGPT\nworker=ChatGPT")
        with self.assertRaisesRegex(PreQaBarrierError, "duplicate barrier key"):
            parse_barrier_section(duplicate)
        unknown = section.replace("worker=ChatGPT", "worker=ChatGPT\nmerge=true")
        with self.assertRaisesRegex(PreQaBarrierError, "unknown barrier key"):
            parse_barrier_section(unknown)
        spoofed = section.replace("worker=ChatGPT", "wоrker=ChatGPT")
        with self.assertRaisesRegex(PreQaBarrierError, "invalid barrier key"):
            parse_barrier_section(spoofed)
        tampered = section.replace("quality_run_id=12345", "quality_run_id=12346")
        with self.assertRaisesRegex(PreQaBarrierError, "receipt_digest mismatch"):
            parse_barrier_section(tampered)

    def test_receipt_target_and_review_inventory_must_match_pr(self) -> None:
        with self.assertRaisesRegex(PreQaBarrierError, "another PR"):
            evaluate(current_pr(), review_threads(number=999), quality_run(), "ChatGPT", "AGY")


if __name__ == "__main__":
    unittest.main()
