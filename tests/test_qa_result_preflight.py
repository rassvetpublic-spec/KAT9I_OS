from __future__ import annotations

import unittest

from scripts.qa_result_bridge import BridgeError, COMMAND_MARKER, RESULT_FIELDS, RESULT_MARKER
from scripts.qa_result_preflight import preflight

HEAD = "a" * 40
OTHER_HEAD = "b" * 40
COMMAND_ID = "QAC-145-AAAAAAAA-001"


def command_body(command_id: str = COMMAND_ID, head: str = HEAD, **overrides: str) -> str:
    values = {
        "command_id": command_id,
        "target_pr": "161",
        "controller": "ChatGPT",
        "executor": "AGY",
        "role": "QA_EXECUTOR",
        "exact_head": head,
        "qa_mode": "FULL",
        "result_sink": "PR_REVIEW",
        "allow_issue_create": "false",
        "allow_merge": "false",
        "allow_fast_marker": "false",
        "allow_code_mutation": "false",
        "project_lifecycle_mutation": "false",
    }
    values.update(overrides)
    return COMMAND_MARKER + "\n" + "\n".join(f"{key}={value}" for key, value in values.items()) + "\n\nSCOPE: test"


def result_body(command_id: str = COMMAND_ID, head: str = HEAD, **overrides: str) -> str:
    values = {
        "command_id": command_id,
        "target_pr": "161",
        "controller": "ChatGPT",
        "executor": "Antigravity",
        "role": "QA_EXECUTOR",
        "exact_head": head,
        "qa_mode": "FULL",
        "result_sink": "PR_REVIEW",
        "verdict": "QA PASS",
        "blocking_findings": "0",
        "follow_up_candidates": "0",
    }
    values.update(overrides)
    return RESULT_MARKER + "\n" + "\n".join(f"{key}={value}" for key, value in values.items()) + "\n\nFOLLOW_UP_CANDIDATES\n"


def comment(body: str | None = None, *, created_at: str = "2026-09-11T12:00:00Z", comment_id: int = 1, association: str = "OWNER") -> dict:
    return {
        "id": comment_id,
        "body": body or command_body(),
        "created_at": created_at,
        "author_association": association,
    }


def live_pr(head: str = HEAD, *, state: str = "open", number: int = 161) -> dict:
    return {"number": number, "state": state, "head": {"sha": head}}


class QaResultPreflightTests(unittest.TestCase):
    def test_valid_result_passes_shared_contract_and_command_binding(self) -> None:
        result = preflight(result_body(), [comment()], live_pr())
        self.assertEqual(result["verdict"], "PASS")
        self.assertEqual(result["authority"], "VALIDATION_ONLY")
        self.assertEqual(result["contract_fields"], sorted(RESULT_FIELDS))
        self.assertEqual(result["command_id"], COMMAND_ID)
        self.assertEqual(result["exact_head"], HEAD)

    def test_pr131_missing_result_sink_fails_before_review_publication(self) -> None:
        malformed = result_body().replace("result_sink=PR_REVIEW\n", "")
        with self.assertRaisesRegex(BridgeError, "missing envelope keys: result_sink"):
            preflight(malformed, [comment()], live_pr())

    def test_duplicate_and_unicode_spoofed_keys_fail_closed(self) -> None:
        duplicate = result_body().replace("controller=ChatGPT", "controller=ChatGPT\ncontroller=ChatGPT")
        with self.assertRaisesRegex(BridgeError, "duplicate envelope key"):
            preflight(duplicate, [comment()], live_pr())
        spoofed = result_body().replace("controller=ChatGPT", "contrоller=ChatGPT")
        with self.assertRaises(BridgeError):
            preflight(spoofed, [comment()], live_pr())

    def test_result_sink_and_enum_hijack_fail_closed(self) -> None:
        with self.assertRaisesRegex(BridgeError, "result_sink"):
            preflight(result_body(result_sink="ISSUE_COMMENT"), [comment()], live_pr())
        with self.assertRaisesRegex(BridgeError, "qa_mode"):
            preflight(result_body(qa_mode="MAGIC"), [comment()], live_pr())
        with self.assertRaisesRegex(BridgeError, "verdict"):
            preflight(result_body(verdict="PASS"), [comment()], live_pr())

    def test_pass_with_blocking_findings_fails_closed(self) -> None:
        with self.assertRaisesRegex(BridgeError, "cannot contain blocking"):
            preflight(result_body(blocking_findings="1"), [comment()], live_pr())

    def test_follow_up_section_is_mandatory_and_nonempty_when_declared(self) -> None:
        missing = result_body().split("\n\nFOLLOW_UP_CANDIDATES", 1)[0]
        with self.assertRaisesRegex(BridgeError, "FOLLOW_UP_CANDIDATES"):
            preflight(missing, [comment()], live_pr())
        empty_positive = result_body(follow_up_candidates="1")
        with self.assertRaisesRegex(BridgeError, "section has no content"):
            preflight(empty_positive, [comment()], live_pr())

    def test_stale_or_wrong_live_head_fails_closed(self) -> None:
        with self.assertRaisesRegex(BridgeError, "live PR HEAD"):
            preflight(result_body(), [comment()], live_pr(head=OTHER_HEAD))
        stale_command = comment(body=command_body(head=OTHER_HEAD))
        with self.assertRaisesRegex(BridgeError, "command/result mismatch: exact_head"):
            preflight(result_body(), [stale_command], live_pr())

    def test_wrong_target_or_closed_pr_fails_closed(self) -> None:
        with self.assertRaisesRegex(BridgeError, "target_pr"):
            preflight(result_body(), [comment()], live_pr(number=162))
        with self.assertRaisesRegex(BridgeError, "not open"):
            preflight(result_body(), [comment()], live_pr(state="closed"))

    def test_latest_authoritative_command_supersedes_old_result(self) -> None:
        newer_id = "QAC-145-BBBBBBBB-002"
        newer = comment(
            body=command_body(command_id=newer_id),
            created_at="2026-09-11T12:01:00Z",
            comment_id=2,
        )
        with self.assertRaisesRegex(BridgeError, "superseded command"):
            preflight(result_body(), [comment(), newer], live_pr())

    def test_duplicate_command_id_and_non_owner_command_fail_closed(self) -> None:
        duplicate = comment(created_at="2026-09-11T11:59:00Z", comment_id=2)
        with self.assertRaisesRegex(BridgeError, "duplicate command_id"):
            preflight(result_body(), [duplicate, comment()], live_pr())
        with self.assertRaisesRegex(BridgeError, "no owner QA-COMMAND"):
            preflight(result_body(), [comment(association="CONTRIBUTOR")], live_pr())

    def test_command_result_binding_uses_same_executor_normalization(self) -> None:
        bound = preflight(result_body(executor="Антигравити"), [comment(body=command_body(executor="AGY"))], live_pr())
        self.assertEqual(bound["verdict"], "PASS")


if __name__ == "__main__":
    unittest.main()
