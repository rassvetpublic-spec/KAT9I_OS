import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from graveyard_pr_salvage import build_audit, render_markdown


class GraveyardPrSalvageTests(unittest.TestCase):
    def _payload(self, **overrides):
        pr = {
            "number": 86,
            "title": "Параллельная архитектура CacheEngine",
            "body": "## Что сделано\n- Добавить строгий машинный контракт CacheEntry для межмодульного обмена\n- Сохранить RAM-first CacheEngine как отдельный Rust-процесс\n",
            "state": "closed",
            "merged": False,
            "head_sha": "8" * 40,
            "changed_files": 8,
            "additions": 600,
            "deletions": 20,
            "commits": 9,
            "labels": [],
        }
        pr.update(overrides.pop("pr", {}))
        payload = {
            "repository": "rassvetpublic-spec/KAT9I_OS",
            "canon_revision": "b" * 40,
            "pr": pr,
            "files": [
                {"filename": "docs/architecture/34_CACHE_ENGINE.md", "status": "modified", "sha": "1" * 40, "main_blob_sha": "1" * 40},
                {"filename": "schemas/v1/CacheEntry.json", "status": "added", "sha": "2" * 40, "main_blob_sha": None},
            ],
            "review_comments": [],
            "issue_comments": [],
        }
        payload.update(overrides)
        return payload

    def _root(self):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        (root / "docs" / "architecture").mkdir(parents=True)
        (root / "schemas" / "v1").mkdir(parents=True)
        (root / "docs" / "architecture" / "34_CACHE_ENGINE.md").write_text(
            "CacheEngine — отдельный Rust-процесс. RAM-first. Строгий CacheEntry пока не материализован отдельной схемой.",
            encoding="utf-8",
        )
        return temp, root

    def test_merged_pr_is_skipped(self):
        temp, root = self._root()
        with temp:
            report = build_audit(self._payload(pr={"merged": True}), root=root)
            self.assertFalse(report["audit_required"])
            self.assertEqual(report["audit_reason"], "MERGED_INTO_CANON")

    def test_small_closed_pr_is_skipped_without_superseded_signal(self):
        temp, root = self._root()
        with temp:
            payload = self._payload(pr={"title": "Мелкая правка", "body": "", "changed_files": 1, "additions": 3, "deletions": 1, "commits": 1})
            report = build_audit(payload, root=root)
            self.assertFalse(report["audit_required"])
            self.assertEqual(report["audit_reason"], "CLOSED_UNMERGED_SMALL")

    def test_explicit_superseded_small_pr_is_audited(self):
        temp, root = self._root()
        with temp:
            payload = self._payload(pr={"title": "Устаревшая параллельная реализация", "body": "", "changed_files": 1, "additions": 3, "deletions": 1, "commits": 1})
            report = build_audit(payload, root=root)
            self.assertTrue(report["audit_required"])
            self.assertEqual(report["audit_reason"], "CLOSED_UNMERGED_EXPLICITLY_SUPERSEDED")

    def test_exact_blob_match_is_already_in_main(self):
        temp, root = self._root()
        with temp:
            report = build_audit(self._payload(), root=root)
            categories = [item["category"] for item in report["items"]]
            self.assertIn("ALREADY_IN_MAIN", categories)
            self.assertIn("NEEDS_SEMANTIC_REVIEW", categories)

    def test_pr_body_produces_unique_candidate_not_control(self):
        temp, root = self._root()
        with temp:
            report = build_audit(self._payload(), root=root)
            unique = [item for item in report["items"] if item["category"] == "UNIQUE_IDEA_CANDIDATE"]
            self.assertTrue(unique)
            self.assertFalse(report["actionable"])
            self.assertFalse(report["control"])
            self.assertFalse(report["canonical"])
            self.assertFalse(report["auto_promotion"])
            self.assertTrue(report["promotion_requires_owner_approval"])

    def test_review_finding_becomes_negative_test_candidate(self):
        temp, root = self._root()
        with temp:
            payload = self._payload(review_comments=[{
                "body": "**P1 Badge — CacheKey collision**\nDifferent owners must not produce the same key.",
                "path": "schemas/v1/CacheEntry.json",
                "line": 10,
                "url": "https://example.invalid/review",
            }])
            report = build_audit(payload, root=root)
            negative = [item for item in report["items"] if item["category"] == "NEGATIVE_TEST_CANDIDATE"]
            self.assertEqual(len(negative), 1)
            self.assertEqual(negative[0]["evidence"]["path"], "schemas/v1/CacheEntry.json")

    def test_superseded_closing_comment_becomes_rejected_candidate(self):
        temp, root = self._root()
        with temp:
            payload = self._payload(issue_comments=[{
                "body": "Закрывается как устаревшая параллельная реализация.\n- Старую схему автоматически не переносить в main.",
                "url": "https://example.invalid/comment",
            }])
            report = build_audit(payload, root=root)
            rejected = [item for item in report["items"] if item["category"] == "REJECTED_OPTION_CANDIDATE"]
            self.assertTrue(rejected)

    def test_secret_like_values_are_redacted(self):
        temp, root = self._root()
        with temp:
            payload = self._payload(pr={"body": "- Идея содержит github_pat_ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890 и не должна сохранять секрет"})
            report = build_audit(payload, root=root)
            serialized = json.dumps(report, ensure_ascii=False)
            self.assertNotIn("github_pat_ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890", serialized)
            self.assertIn("УДАЛЁН_СЕКРЕТ", serialized)

    def test_markdown_repeats_data_only_boundary(self):
        temp, root = self._root()
        with temp:
            text = render_markdown(build_audit(self._payload(), root=root))
            self.assertIn("DATA ONLY", text)
            self.assertIn("не создаёт работу", text)
            self.assertIn("Human Approval", text)


if __name__ == "__main__":
    unittest.main()
