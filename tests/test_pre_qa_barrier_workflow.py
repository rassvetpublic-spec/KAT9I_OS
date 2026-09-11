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

    def test_receipt_is_a_comment_review_anchored_to_exact_commit(self) -> None:
        self.assertIn("KAT9I-PRE-QA-BARRIER/1", self.text)
        self.assertIn("-f event=COMMENT", self.text)
        self.assertIn('-f commit_id="$EXPECTED_HEAD"', self.text)
        self.assertIn("pulls/${PR_NUMBER}/reviews", self.text)
        self.assertIn("VALIDATION_ONLY", self.text)

    def test_workflow_does_not_contain_merge_or_fast_authority(self) -> None:
        self.assertNotIn("/merge", self.text)
        self.assertNotIn("FAST-QA-PASS", self.text)
        self.assertNotIn("FAST-BLOCKED", self.text)
        self.assertNotIn("project_lifecycle", self.text)


if __name__ == "__main__":
    unittest.main()
