from __future__ import annotations

import unittest

from scripts.qa_accept_preflight import preflight
from scripts.qa_result_bridge import ATTEST_FIELDS, ATTEST_MARKER, BridgeError

HEAD = "a" * 40


def body(**overrides: str) -> str:
    values = {
        "command_id": "QAC-158-7FEBBF1E-002",
        "target_pr": "158",
        "controller": "ChatGPT",
        "executor": "AGY",
        "role": "QA_EXECUTOR",
        "review_id": "5177797955",
        "exact_head": HEAD,
        "verdict": "QA PASS",
    }
    values.update(overrides)
    return ATTEST_MARKER + "\n" + "\n".join(f"{key}={values[key]}" for key in values) + "\n"


class QaAcceptPreflightTests(unittest.TestCase):
    def test_canonical_attestation_passes_shared_contract(self) -> None:
        result = preflight(body())
        self.assertEqual(result["verdict"], "PASS")
        self.assertEqual(result["contract_fields"], sorted(ATTEST_FIELDS))
        self.assertEqual(result["review_id"], 5177797955)
        self.assertEqual(result["executor"], "AGY")

    def test_pr158_extra_blocking_findings_is_rejected_before_bridge(self) -> None:
        malformed = body().replace("verdict=QA PASS", "verdict=QA PASS\nblocking_findings=0")
        with self.assertRaisesRegex(BridgeError, "unknown envelope key: blocking_findings"):
            preflight(malformed)

    def test_duplicate_field_fails_closed(self) -> None:
        malformed = body().replace("controller=ChatGPT", "controller=ChatGPT\ncontroller=ChatGPT")
        with self.assertRaisesRegex(BridgeError, "duplicate envelope key"):
            preflight(malformed)

    def test_missing_field_fails_closed(self) -> None:
        malformed = body().replace(f"exact_head={HEAD}\n", "")
        with self.assertRaisesRegex(BridgeError, "missing envelope keys: exact_head"):
            preflight(malformed)

    def test_unicode_spoofed_key_fails_closed(self) -> None:
        malformed = body().replace("controller=ChatGPT", "contrоller=ChatGPT")
        with self.assertRaises(BridgeError):
            preflight(malformed)

    def test_malformed_values_use_production_validator(self) -> None:
        cases = (
            (body(review_id="0"), "review_id"),
            (body(exact_head="ABC"), "exact_head"),
            (body(executor="Controller"), "executor"),
            (body(verdict="PASS"), "verdict"),
        )
        for malformed, fragment in cases:
            with self.subTest(fragment=fragment):
                with self.assertRaisesRegex(BridgeError, fragment):
                    preflight(malformed)


if __name__ == "__main__":
    unittest.main()
