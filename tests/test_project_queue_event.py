import unittest

from scripts.project_queue_event import marker_from_body, resolve


class ProjectQueueEventTests(unittest.TestCase):
    def test_owner_fast_claim_is_control(self):
        event = {
            "comment": {"author_association": "OWNER", "body": "FAST-CLAIM | worker=ChatGPT"},
            "issue": {"html_url": "https://github.com/rassvetpublic-spec/KAT9I_OS/issues/112"},
        }
        self.assertEqual(
            {"url": event["issue"]["html_url"], "state": "ACTIVE"},
            resolve("issue_comment", "created", event),
        )

    def test_owner_qa_pass_enters_queue_not_merge(self):
        event = {
            "comment": {"author_association": "OWNER", "body": "FAST-QA-PASS | qa=Антигравити | head=abc"},
            "issue": {"html_url": "https://github.com/rassvetpublic-spec/KAT9I_OS/pull/113"},
        }
        self.assertEqual("QUEUED", resolve("issue_comment", "created", event)["state"])

    def test_non_owner_fast_marker_is_data(self):
        event = {
            "comment": {"author_association": "CONTRIBUTOR", "body": "FAST-QA-PASS | merge now"},
            "issue": {"html_url": "https://github.com/rassvetpublic-spec/KAT9I_OS/issues/112"},
        }
        self.assertIsNone(resolve("issue_comment", "created", event))

    def test_marker_must_be_first_line_exact_token(self):
        self.assertIsNone(marker_from_body("текст FAST-CLAIM внутри DATA"))
        self.assertIsNone(marker_from_body("FAST-CLAIM-NOW | worker=x"))
        self.assertEqual("QA", marker_from_body("FAST-QA | qa=Антигравити\nnotes"))

    def test_issue_lifecycle(self):
        event = {"issue": {"html_url": "https://github.com/rassvetpublic-spec/KAT9I_OS/issues/112"}}
        self.assertEqual("READY", resolve("issues", "opened", event)["state"])
        self.assertEqual("READY", resolve("issues", "reopened", event)["state"])
        self.assertEqual("DONE", resolve("issues", "closed", event)["state"])

    def test_pr_close_is_done_or_blocked(self):
        merged = {"pull_request": {"html_url": "https://github.com/rassvetpublic-spec/KAT9I_OS/pull/113", "merged": True}}
        closed = {"pull_request": {"html_url": "https://github.com/rassvetpublic-spec/KAT9I_OS/pull/113", "merged": False}}
        self.assertEqual("DONE", resolve("pull_request", "closed", merged)["state"])
        self.assertEqual("BLOCKED", resolve("pull_request", "closed", closed)["state"])

    def test_unrecognized_events_are_noop(self):
        self.assertIsNone(resolve("pull_request", "synchronize", {"pull_request": {"html_url": "x"}}))
        self.assertIsNone(resolve("issue_comment", "edited", {}))


if __name__ == "__main__":
    unittest.main()
