from __future__ import annotations

import unittest

from scripts.project_card_authorization import MARKER, authorize

SHA = "a" * 40


def event(body: str, *, issue: int = 150, association: str = "OWNER", login: str = "rassvetpublic-spec") -> dict:
    return {
        "repository": {"full_name": "rassvetpublic-spec/KAT9I_OS"},
        "action": "created",
        "issue": {"number": issue},
        "comment": {"author_association": association, "user": {"login": login}, "body": body},
    }


class ProjectCardAuthorizationTests(unittest.TestCase):
    def test_exact_two_line_owner_command_passes(self) -> None:
        body = f"{MARKER}\nexpected_head={SHA}"
        self.assertEqual(authorize("issue_comment", event(body), "rassvetpublic-spec", SHA, "refs/heads/main"), SHA)

    def test_extra_line_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "ровно marker"):
            authorize("issue_comment", event(f"{MARKER}\nexpected_head={SHA}\nWORKER-NOTE"), "rassvetpublic-spec", SHA, "refs/heads/main")

    def test_stale_head_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "exact HEAD"):
            authorize("issue_comment", event(f"{MARKER}\nexpected_head={'b' * 40}"), "rassvetpublic-spec", SHA, "refs/heads/main")

    def test_non_owner_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            authorize("issue_comment", event(f"{MARKER}\nexpected_head={SHA}", association="CONTRIBUTOR", login="other"), "rassvetpublic-spec", SHA, "refs/heads/main")


if __name__ == "__main__":
    unittest.main()
