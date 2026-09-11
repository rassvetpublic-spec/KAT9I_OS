from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.worker_kpi_ledger import (
    AUTHORITY,
    EVENT_SCHEMA,
    INVALIDATION_REASONS,
    LEDGER_SCHEMA,
    PHASES,
    QA_MODES,
    WAIT_REASONS,
    KpiLedgerError,
    append_event,
    summarize,
    validate_event,
    validate_ledger,
)

HEAD = "a" * 40
HEAD2 = "b" * 40


def event(
    event_id: str,
    phase: str,
    started_at: str,
    ended_at: str,
    *,
    head: str = HEAD,
    issue: int = 136,
    pr: int = 165,
    worker: str = "ChatGPT",
    qa: str = "AGY",
    **extra,
) -> dict:
    payload = {
        "schema": EVENT_SCHEMA,
        "event_id": event_id,
        "issue_number": issue,
        "pr_number": pr,
        "worker": worker,
        "qa": qa,
        "exact_head": head,
        "phase": phase,
        "started_at": started_at,
        "ended_at": ended_at,
        "authority": AUTHORITY,
    }
    payload.update(extra)
    return payload


def ledger(*events: dict) -> dict:
    return {"schema": LEDGER_SCHEMA, "authority": AUTHORITY, "events": list(events)}


class WorkerKpiLedgerTests(unittest.TestCase):
    def test_schema_enums_match_executable_contract(self) -> None:
        schema = json.loads(Path("config/worker_kpi_event.schema.json").read_text(encoding="utf-8"))
        props = schema["properties"]
        self.assertEqual(set(props["phase"]["enum"]), PHASES)
        self.assertEqual(set(props["wait_reason"]["enum"]) - {None}, WAIT_REASONS)
        self.assertEqual(set(props["qa_mode"]["enum"]) - {None}, QA_MODES)
        self.assertEqual(set(props["qa_invalidation_reason"]["enum"]) - {None}, INVALIDATION_REASONS)
        self.assertEqual(props["authority"]["const"], AUTHORITY)

    def test_event_is_typed_and_bound_to_issue_pr_worker_qa_and_head(self) -> None:
        normalized = validate_event(
            event(
                "evt.exec.001",
                "EXECUTION",
                "2026-09-11T10:00:00Z",
                "2026-09-11T10:10:00Z",
            )
        )
        self.assertEqual(normalized["issue_number"], 136)
        self.assertEqual(normalized["pr_number"], 165)
        self.assertEqual(normalized["worker"], "ChatGPT")
        self.assertEqual(normalized["qa"], "AGY")
        self.assertEqual(normalized["exact_head"], HEAD)
        self.assertEqual(normalized["authority"], "DATA_ONLY")

    def test_negative_zero_or_timezone_less_intervals_fail_closed(self) -> None:
        with self.assertRaisesRegex(KpiLedgerError, "ended_at > started_at"):
            validate_event(event("evt.bad.001", "EXECUTION", "2026-09-11T10:10:00Z", "2026-09-11T10:00:00Z"))
        with self.assertRaisesRegex(KpiLedgerError, "ended_at > started_at"):
            validate_event(event("evt.bad.002", "EXECUTION", "2026-09-11T10:00:00Z", "2026-09-11T10:00:00Z"))
        with self.assertRaisesRegex(KpiLedgerError, "timezone"):
            validate_event(event("evt.bad.003", "EXECUTION", "2026-09-11T10:00:00", "2026-09-11T10:10:00"))

    def test_wait_reason_and_qa_mode_semantics_are_enforced(self) -> None:
        with self.assertRaisesRegex(KpiLedgerError, "wait_reason is required"):
            validate_event(event("evt.wait.001", "QUEUE_WAIT", "2026-09-11T10:00:00Z", "2026-09-11T10:10:00Z"))
        with self.assertRaisesRegex(KpiLedgerError, "OWNER_GATE"):
            validate_event(event("evt.wait.002", "OWNER_WAIT", "2026-09-11T10:00:00Z", "2026-09-11T10:10:00Z", wait_reason="POLICY"))
        with self.assertRaisesRegex(KpiLedgerError, "qa_mode is required"):
            validate_event(event("evt.qa.001", "QA_ACTIVE", "2026-09-11T10:00:00Z", "2026-09-11T10:10:00Z"))
        with self.assertRaisesRegex(KpiLedgerError, "not allowed for active phase"):
            validate_event(event("evt.exec.002", "EXECUTION", "2026-09-11T10:00:00Z", "2026-09-11T10:10:00Z", wait_reason="CI"))

    def test_rework_and_verdict_fields_are_phase_safe(self) -> None:
        with self.assertRaisesRegex(KpiLedgerError, "REWORK requires"):
            validate_event(event("evt.rework.001", "REWORK", "2026-09-11T10:00:00Z", "2026-09-11T10:10:00Z"))
        with self.assertRaisesRegex(KpiLedgerError, "only allowed for REWORK"):
            validate_event(event("evt.exec.003", "EXECUTION", "2026-09-11T10:00:00Z", "2026-09-11T10:10:00Z", rework_cycle_id=1))
        with self.assertRaisesRegex(KpiLedgerError, "requires issued"):
            validate_event(event("evt.qa.002", "QA_ACTIVE", "2026-09-11T10:00:00Z", "2026-09-11T10:10:00Z", qa_mode="FULL", accepted_qa_verdict=True))

    def test_overlap_duplicate_and_mixed_identity_fail_closed(self) -> None:
        first = event("evt.exec.010", "EXECUTION", "2026-09-11T10:00:00Z", "2026-09-11T10:20:00Z")
        overlap = event("evt.wait.010", "QUEUE_WAIT", "2026-09-11T10:10:00Z", "2026-09-11T10:30:00Z", wait_reason="PREDECESSOR")
        with self.assertRaisesRegex(KpiLedgerError, "overlap"):
            validate_ledger(ledger(first, overlap))
        duplicate = {**first}
        with self.assertRaisesRegex(KpiLedgerError, "duplicate event_id"):
            validate_ledger(ledger(first, duplicate))
        changed_worker = event("evt.exec.011", "EXECUTION", "2026-09-11T10:20:00Z", "2026-09-11T10:30:00Z", worker="Other")
        with self.assertRaisesRegex(KpiLedgerError, "worker"):
            validate_ledger(ledger(first, changed_worker))

    def test_append_only_rejects_rewrite_and_accepts_new_head_after_rework(self) -> None:
        base = ledger(event("evt.exec.020", "EXECUTION", "2026-09-11T10:00:00Z", "2026-09-11T10:10:00Z"))
        appended = append_event(
            base,
            event("evt.rework.020", "REWORK", "2026-09-11T10:10:00Z", "2026-09-11T10:20:00Z", head=HEAD2, rework_cycle_id=1),
        )
        self.assertEqual(len(appended["events"]), 2)
        self.assertEqual(appended["events"][-1]["exact_head"], HEAD2)
        with self.assertRaisesRegex(KpiLedgerError, "overlap or rewrite"):
            append_event(base, event("evt.exec.021", "EXECUTION", "2026-09-11T10:05:00Z", "2026-09-11T10:15:00Z"))

    def test_wait_reasons_cover_required_control_plane_causes(self) -> None:
        self.assertTrue({"PREDECESSOR", "QA", "REWORK", "CI", "OWNER_GATE", "BLOCKED_DEPENDENCY", "POLICY"}.issubset(WAIT_REASONS))

    def test_131_133_style_wait_does_not_penalize_worker_execution(self) -> None:
        sample = ledger(
            event("evt.queue.131", "QUEUE_WAIT", "2026-09-11T08:00:00Z", "2026-09-11T09:00:00Z", wait_reason="PREDECESSOR"),
            event("evt.exec.131", "EXECUTION", "2026-09-11T09:00:00Z", "2026-09-11T09:10:00Z"),
            event("evt.qwait.131", "QA_WAIT", "2026-09-11T09:10:00Z", "2026-09-11T09:20:00Z", wait_reason="QA", qa_mode="FULL"),
            event(
                "evt.qa.131",
                "QA_ACTIVE",
                "2026-09-11T09:20:00Z",
                "2026-09-11T09:25:00Z",
                qa_mode="FULL",
                first_pass_findings=0,
                issued_qa_verdict=True,
                accepted_qa_verdict=True,
            ),
            event("evt.owner.131", "OWNER_WAIT", "2026-09-11T09:25:00Z", "2026-09-11T11:25:00Z", wait_reason="OWNER_GATE"),
        )
        summary = summarize(sample)
        self.assertEqual(summary["execution_time_seconds"], 600.0)
        self.assertEqual(summary["qa_active_time_seconds"], 300.0)
        self.assertEqual(summary["active_processing_time_seconds"], 900.0)
        self.assertEqual(summary["queue_wait_time_seconds"], 3600.0)
        self.assertEqual(summary["qa_wait_time_seconds"], 600.0)
        self.assertEqual(summary["owner_wait_time_seconds"], 7200.0)
        self.assertEqual(summary["waiting_time_seconds"], 11400.0)
        self.assertEqual(summary["lead_time_seconds"], 12300.0)
        self.assertTrue(summary["first_pass_pass"])

    def test_rework_invalidations_candidate_rebuild_and_verdict_counters_are_separate(self) -> None:
        sample = ledger(
            event("evt.exec.030", "EXECUTION", "2026-09-11T10:00:00Z", "2026-09-11T10:05:00Z"),
            event("evt.rework.030", "REWORK", "2026-09-11T10:05:00Z", "2026-09-11T10:15:00Z", head=HEAD2, rework_cycle_id=1, qa_invalidation_reason="HEAD_DRIFT", candidate_rebuild=True),
            event(
                "evt.qa.030",
                "QA_ACTIVE",
                "2026-09-11T10:15:00Z",
                "2026-09-11T10:20:00Z",
                head=HEAD2,
                qa_mode="DELTA",
                first_pass_findings=2,
                issued_qa_verdict=True,
                stale_or_false_safe_verdict=True,
            ),
        )
        summary = summarize(sample)
        self.assertEqual(summary["rework_cycles"], 1)
        self.assertEqual(summary["qa_invalidation_count"], 1)
        self.assertEqual(summary["qa_invalidations_by_reason"]["HEAD_DRIFT"], 1)
        self.assertEqual(summary["candidate_rebuild_count"], 1)
        self.assertEqual(summary["issued_qa_verdicts"], 1)
        self.assertEqual(summary["accepted_qa_verdicts"], 0)
        self.assertEqual(summary["false_safe_or_stale_verdict_count"], 1)
        self.assertFalse(summary["first_pass_pass"])
        self.assertEqual(summary["qa_modes"]["DELTA"], 1)


if __name__ == "__main__":
    unittest.main()
