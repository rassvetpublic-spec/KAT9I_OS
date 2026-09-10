import unittest

from scripts.project_queue_event import marker_from_body, resolve


class ProjectQueueEventTests(unittest.TestCase):
    def test_owner_fast_claim_is_control_and_preserves_worker(self):
        event = {
            "comment": {
                "author_association": "OWNER",
                "body": "FAST-CLAIM | worker=Codex | qa=Antigravity",
            },
            "issue": {"html_url": "https://github.com/rassvetpublic-spec/KAT9I_OS/issues/117"},
        }
        self.assertEqual(
            {
                "url": event["issue"]["html_url"],
                "state": "ACTIVE",
                "worker": "Codex",
                "qa": "Antigravity",
            },
            resolve("issue_comment", "created", event),
        )

    def test_owner_fast_ready_is_explicit_control(self):
        event = {
            "comment": {"author_association": "OWNER", "body": "FAST-READY | gate=G0"},
            "issue": {"html_url": "https://github.com/rassvetpublic-spec/KAT9I_OS/issues/117"},
        }
        self.assertEqual(
            {"url": event["issue"]["html_url"], "state": "READY"},
            resolve("issue_comment", "created", event),
        )

    def test_owner_qa_pass_enters_queue_not_merge_and_preserves_qa(self):
        event = {
            "comment": {
                "author_association": "OWNER",
                "body": "FAST-QA-PASS | qa=Antigravity (AGY) | head=abc",
            },
            "issue": {"html_url": "https://github.com/rassvetpublic-spec/KAT9I_OS/pull/113"},
        }
        resolved = resolve("issue_comment", "created", event)
        self.assertEqual("QUEUED", resolved["state"])
        self.assertEqual("Antigravity (AGY)", resolved["qa"])
        self.assertNotIn("worker", resolved)

    def test_non_owner_fast_marker_is_data(self):
        event = {
            "comment": {"author_association": "CONTRIBUTOR", "body": "FAST-QA-PASS | qa="},
            "issue": {"html_url": "https://github.com/rassvetpublic-spec/KAT9I_OS/issues/117"},
        }
        self.assertIsNone(resolve("issue_comment", "created", event))

    def test_marker_must_be_first_line_exact_token(self):
        self.assertIsNone(marker_from_body("текст FAST-CLAIM внутри DATA"))
        self.assertIsNone(marker_from_body("FAST-CLAIM-NOW | worker=x"))
        self.assertEqual("QA", marker_from_body("FAST-QA | qa=Antigravity\nnotes"))

    def test_malformed_identity_metadata_fails_closed(self):
        bad_bodies = (
            "FAST-CLAIM | worker",
            "FAST-QA | qa=",
            "FAST-CLAIM | worker=Codex | worker=ChatGPT",
            "FAST-QA | qa=AGY | qa=Codex",
            "FAST-CLAIM | worker-id=Codex",
            "FAST-QA | qa_worker=AGY",
            "FAST-CLAIM | worker-id",
            "FAST-QA | qa_worker",
            "FAST-CLAIM | worker:Codex",
            "FAST-QA | qa:AGY",
        )
        for body in bad_bodies:
            event = {
                "comment": {"author_association": "OWNER", "body": body},
                "issue": {"html_url": "https://github.com/rassvetpublic-spec/KAT9I_OS/issues/117"},
            }
            with self.subTest(body=body):
                with self.assertRaises(ValueError):
                    resolve("issue_comment", "created", event)

    def test_non_identity_metadata_remains_compatible(self):
        event = {
            "comment": {
                "author_association": "OWNER",
                "body": "FAST-QA-PASS | qa=AGY | head=abc | quality=123 | state=QUEUED",
            },
            "issue": {"html_url": "https://github.com/rassvetpublic-spec/KAT9I_OS/issues/117"},
        }
        resolved = resolve("issue_comment", "created", event)
        self.assertEqual("QUEUED", resolved["state"])
        self.assertEqual("AGY", resolved["qa"])
        self.assertNotIn("head", resolved)
        self.assertNotIn("quality", resolved)

    def test_issue_open_does_not_skip_triage(self):
        event = {"issue": {"html_url": "https://github.com/rassvetpublic-spec/KAT9I_OS/issues/117"}}
        self.assertEqual("INBOX", resolve("issues", "opened", event)["state"])
        self.assertEqual("INBOX", resolve("issues", "reopened", event)["state"])

    def test_issue_close_requires_completed_reason(self):
        completed = {
            "issue": {
                "html_url": "https://github.com/rassvetpublic-spec/KAT9I_OS/issues/117",
                "state_reason": "completed",
            }
        }
        not_planned = {
            "issue": {
                "html_url": "https://github.com/rassvetpublic-spec/KAT9I_OS/issues/117",
                "state_reason": "not_planned",
            }
        }
        missing_reason = {"issue": {"html_url": "https://github.com/rassvetpublic-spec/KAT9I_OS/issues/117"}}
        self.assertEqual("DONE", resolve("issues", "closed", completed)["state"])
        self.assertIsNone(resolve("issues", "closed", not_planned))
        self.assertIsNone(resolve("issues", "closed", missing_reason))

    def test_pr_synchronize_invalidates_queued_qa_without_overwriting_assignments(self):
        event = {"pull_request": {"html_url": "https://github.com/rassvetpublic-spec/KAT9I_OS/pull/113"}}
        self.assertEqual(
            {"url": event["pull_request"]["html_url"], "state": "ACTIVE"},
            resolve("pull_request", "synchronize", event),
        )

    def test_pr_close_is_done_or_blocked(self):
        merged = {
            "pull_request": {
                "html_url": "https://github.com/rassvetpublic-spec/KAT9I_OS/pull/113",
                "merged": True,
            }
        }
        closed = {
            "pull_request": {
                "html_url": "https://github.com/rassvetpublic-spec/KAT9I_OS/pull/113",
                "merged": False,
            }
        }
        self.assertEqual("DONE", resolve("pull_request", "closed", merged)["state"])
        self.assertEqual("BLOCKED", resolve("pull_request", "closed", closed)["state"])

    def test_unrecognized_events_are_noop(self):
        self.assertIsNone(resolve("pull_request", "opened", {"pull_request": {"html_url": "x"}}))
        self.assertIsNone(resolve("issue_comment", "edited", {}))


if __name__ == "__main__":
    unittest.main()
