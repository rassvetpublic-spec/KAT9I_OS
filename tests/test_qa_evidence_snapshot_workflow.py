from __future__ import annotations

import unittest
from pathlib import Path


WORKFLOW = Path('.github/workflows/qa-evidence-snapshot.yml')
BRIDGE = Path('.github/workflows/qa-result-bridge.yml')


class QaEvidenceSnapshotWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = WORKFLOW.read_text(encoding='utf-8')
        cls.bridge = BRIDGE.read_text(encoding='utf-8')

    def test_owner_comment_is_exact_control_entrypoint(self) -> None:
        self.assertIn("github.event.comment.author_association == 'OWNER'", self.text)
        self.assertIn('github.event.comment.user.login == github.repository_owner', self.text)
        self.assertIn('KAT9I-CONTROL/1 | EVIDENCE-SNAPSHOT', self.text)
        self.assertIn('target_pr', self.text)
        self.assertIn('expected_head', self.text)

    def test_snapshot_uses_trusted_default_branch_code(self) -> None:
        self.assertIn('actions/checkout@v4', self.text)
        self.assertIn('github.event.repository.default_branch', self.text)
        self.assertIn('scripts/qa_evidence_epoch.py snapshot', self.text)

    def test_review_inventory_contract_matches_bridge(self) -> None:
        raw_fields = 'nodes{id body path line startLine outdated}'
        self.assertIn(raw_fields, self.text)
        self.assertIn(raw_fields, self.bridge)
        self.assertIn('reviewThreads(first:100)', self.text)
        self.assertIn('pulls/${PR_NUMBER}/reviews?per_page=100', self.text)
        self.assertIn('check-runs?per_page=100', self.text)
        self.assertIn('/status?per_page=100', self.text)
        self.assertIn('review thread inventory is incomplete', self.text)
        self.assertIn('review comment inventory is incomplete', self.text)
        self.assertIn('check-run inventory is incomplete', self.text)
        self.assertIn('commit-status inventory is incomplete', self.text)

    def test_snapshot_is_data_only_and_cannot_promote(self) -> None:
        self.assertIn('KAT9I-EVIDENCE-SNAPSHOT/1', self.text)
        self.assertIn('authority=DATA_ONLY', self.text)
        self.assertNotIn('FAST-QA-PASS |', self.text)
        self.assertNotIn('FAST-BLOCKED |', self.text)
        self.assertNotIn('pulls/${PR_NUMBER}/merge', self.text)
        self.assertNotIn('project_lifecycle_mutation=true', self.text)
        self.assertNotIn('KAT9I-CONTROL/1 | QA-ACCEPT', self.text)

    def test_head_is_checked_before_collection_and_publication(self) -> None:
        self.assertGreaterEqual(self.text.count('HEAD_DRIFT'), 2)
        self.assertGreaterEqual(self.text.count('LIVE_HEAD'), 2)
        self.assertIn('PR HEAD changed before snapshot publication', self.text)

    def test_snapshot_publication_uses_rest_issues_api(self) -> None:
        self.assertIn('issues/${PR_NUMBER}/comments', self.text)
        self.assertIn('gh api --method POST', self.text)
        self.assertIn("jq -Rs '{body: .}' snapshot-comment.md", self.text)
        self.assertNotIn('gh issue comment', self.text)

    def test_snapshot_can_publish_to_pr_conversation(self) -> None:
        self.assertIn('pull-requests: write', self.text)
        self.assertIn('issues: write', self.text)


if __name__ == '__main__':
    unittest.main()
