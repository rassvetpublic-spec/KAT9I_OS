import json
from pathlib import Path
import unittest

import yaml

from scripts.required_check_state import (
    POLICY,
    REQUIRED_CHECK_NAME,
    classify_required_check,
)


ROOT = Path(__file__).resolve().parents[1]
QUALITY = ROOT / ".github" / "workflows" / "quality.yml"
OBSERVER = ROOT / ".github" / "workflows" / "required-check-observer.yml"
POLICY_PATH = ROOT / "config" / "required_checks.json"
HEAD = "a" * 40
OLD_HEAD = "b" * 40


def receipt(*, rid=1, head=HEAD, status="completed", conclusion="success", name=REQUIRED_CHECK_NAME):
    return {
        "id": rid,
        "name": name,
        "head_sha": head,
        "status": status,
        "conclusion": conclusion,
        "html_url": f"https://example.invalid/check/{rid}",
    }


class RequiredCheckStateTests(unittest.TestCase):
    def test_policy_forbids_docs_only_exemption(self):
        raw = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        self.assertEqual("KAT9I_REQUIRED_CHECK_POLICY/1", raw["schema"])
        self.assertTrue(POLICY["applies_to_pull_requests"])
        self.assertFalse(POLICY["docs_only_exempt"])

    def test_quality_workflow_is_unconditional_for_pull_requests(self):
        doc = yaml.load(QUALITY.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
        triggers = doc["on"]
        self.assertIn("pull_request", triggers)
        pull_request = triggers.get("pull_request") or {}
        if isinstance(pull_request, dict):
            self.assertNotIn("paths", pull_request)
            self.assertNotIn("paths-ignore", pull_request)
        job = doc["jobs"]["quality"]
        self.assertEqual(REQUIRED_CHECK_NAME, job["name"])
        self.assertNotIn("if", job)

    def test_missing_pending_failed_stale_success(self):
        cases = (
            ({"receipts": []}, "REQUIRED_CHECK_MISSING"),
            ({"receipts": [receipt(status="queued", conclusion=None)]}, "REQUIRED_CHECK_PENDING"),
            ({"receipts": [receipt(status="in_progress", conclusion=None)]}, "REQUIRED_CHECK_PENDING"),
            ({"receipts": [receipt(conclusion="failure")]}, "REQUIRED_CHECK_FAILED"),
            ({"receipts": [receipt(conclusion="cancelled")]}, "REQUIRED_CHECK_FAILED"),
            ({"receipts": [receipt(head=OLD_HEAD)]}, "REQUIRED_CHECK_STALE"),
            ({"receipts": [receipt()]}, "REQUIRED_CHECK_SUCCESS"),
        )
        for payload, expected in cases:
            with self.subTest(expected=expected):
                result = classify_required_check(HEAD, payload)
                self.assertEqual(expected, result["state"])
                self.assertEqual("DIAGNOSTIC_ONLY", result["authority"])

    def test_latest_exact_receipt_wins_and_stale_does_not_override_current(self):
        payload = {
            "receipts": [
                receipt(rid=3, head=OLD_HEAD),
                receipt(rid=5, status="completed", conclusion="failure"),
                receipt(rid=9, status="completed", conclusion="success"),
            ]
        }
        result = classify_required_check(HEAD, payload)
        self.assertEqual("REQUIRED_CHECK_SUCCESS", result["state"])
        self.assertEqual(9, result["receipt"]["id"])

    def test_unrelated_check_cannot_satisfy_required_context(self):
        payload = {"receipts": [receipt(name="Другой check")]}
        self.assertEqual("REQUIRED_CHECK_MISSING", classify_required_check(HEAD, payload)["state"])

    def test_malformed_head_fails_closed(self):
        for head in ("", "abc", "A" * 40, "a" * 39, "a" * 41):
            with self.subTest(head=head):
                with self.assertRaises(ValueError):
                    classify_required_check(head, {"receipts": []})

    def test_observer_is_read_only(self):
        text = OBSERVER.read_text(encoding="utf-8")
        self.assertIn("DIAGNOSTIC_ONLY", text)
        self.assertIn("checks: read", text)
        self.assertIn("pull-requests: read", text)
        self.assertNotIn("issues: write", text)
        self.assertNotIn("pull-requests: write", text)
        self.assertNotIn("contents: write", text)
        self.assertNotIn("gh pr merge", text)
        self.assertNotIn("project item-edit", text)


if __name__ == "__main__":
    unittest.main()
