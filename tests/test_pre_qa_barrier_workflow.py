from __future__ import annotations

import unittest
from pathlib import Path

WORKFLOW = Path(".github/workflows/pre-qa-barrier.yml")


class PreQaBarrierWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = WORKFLOW.read_text(encoding="utf-8")

    def test_owner_issue_comment_is_the_only_control_trigger(self) -> None:
        self.assertIn("issue_comment:", self.text)
        self.assertIn("author_association == 'OWNER'", self.text)
        self.assertIn("KAT9I-CONTROL/1 | PRE-QA-CHECK", self.text)
        self.assertIn("pull_request", self.text)

    def test_workflow_uses_trusted_default_branch_code(self) -> None:
        self.assertIn("actions/checkout@v4", self.text)
        self.assertIn("github.event.repository.default_branch", self.text)
        self.assertIn("scripts/pre_qa_barrier.py", self.text)

    def test_evidence_inventory_is_exact_head_and_fail_closed(self) -> None:
        self.assertIn("LIVE_HEAD", self.text)
        self.assertIn("EXPECTED_HEAD", self.text)
        self.assertIn("reviewThreads(first:100)", self.text)
        self.assertIn("pageInfo{hasNextPage endCursor}", self.text)
        self.assertIn("actions/workflows/quality.yml/runs", self.text)
        self.assertIn("QUALITY_MISSING", self.text)

    def test_quality_definition_is_bound_to_trusted_default_branch(self) -> None:
        self.assertIn("contents/.github/workflows/quality.yml?ref=${EXPECTED_HEAD}", self.text)
        self.assertIn("contents/.github/workflows/quality.yml?ref=${DEFAULT_BRANCH}", self.text)
        self.assertIn("QUALITY_POLICY_DRIFT", self.text)
        self.assertIn("HEAD_QUALITY_SHA", self.text)
        self.assertIn("TRUSTED_QUALITY_SHA", self.text)

    def test_project_sync_is_required_on_exact_head(self) -> None:
        self.assertIn("actions/workflows/project-queue-sync.yml/runs", self.text)
        self.assertIn("PROJECT_SYNC_MISSING", self.text)
        self.assertIn("PROJECT_SYNC_FAIL", self.text)
        self.assertIn("PROJECT_SYNC_DRIFT", self.text)
        self.assertIn("Project — синхронизация очереди", self.text)

    def test_review_inventory_is_rechecked_before_publication(self) -> None:
        self.assertIn("review-threads-final.json", self.text)
        self.assertIn("FINAL_LIVE_HEAD", self.text)
        self.assertIn("PRE_QA_REVIEW_DRIFT", self.text)
        self.assertIn("PRE_QA_EVIDENCE_DRIFT", self.text)
        final_read = self.text.index("review-threads-final.json")
        publication = self.text.index('pulls/${PR_NUMBER}/reviews\" \\\n            -f event=COMMENT')
        self.assertLess(final_read, publication)

    def test_duplicate_detection_parses_structured_receipt(self) -> None:
        self.assertIn("parse_barrier_section", self.text)
        self.assertIn("PreQaBarrierError", self.text)
        self.assertIn("PRE_QA_DUPLICATE", self.text)
        self.assertIn("receipt.get('exact_head') == expected_head", self.text)
        self.assertNotIn("contains($digest)", self.text)

    def test_receipt_is_a_comment_review_anchored_to_exact_commit(self) -> None:
        self.assertIn("KAT9I-PRE-QA-BARRIER/1", self.text)
        self.assertIn("-f event=COMMENT", self.text)
        self.assertIn('-f commit_id="$EXPECTED_HEAD"', self.text)
        self.assertIn("pulls/${PR_NUMBER}/reviews", self.text)
        self.assertIn("VALIDATION_ONLY", self.text)

    def test_workflow_does_not_contain_merge_or_fast_authority(self) -> None:
        self.assertNotIn("pulls/${PR_NUMBER}/merge", self.text)
        self.assertNotIn("merge_pull_request", self.text)
        self.assertNotIn("FAST-QA-PASS |", self.text)
        self.assertNotIn("FAST-BLOCKED |", self.text)
        self.assertNotIn("project_lifecycle_mutation=true", self.text)


if __name__ == "__main__":
    unittest.main()
