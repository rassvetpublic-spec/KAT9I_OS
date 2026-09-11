#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

EVENT_SCHEMA = "KAT9I_WORKER_KPI_EVENT/1"
LEDGER_SCHEMA = "KAT9I_WORKER_KPI_LEDGER/1"
SUMMARY_SCHEMA = "KAT9I_WORKER_KPI_SUMMARY/1"
AUTHORITY = "DATA_ONLY"
EVENT_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{5,127}$")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
PHASES = {
    "EXECUTION", "REWORK", "QA_WAIT", "QA_ACTIVE",
    "QUEUE_WAIT", "OWNER_WAIT", "CI_WAIT", "BLOCKED_WAIT",
}
WAIT_PHASES = {"QA_WAIT", "QUEUE_WAIT", "OWNER_WAIT", "CI_WAIT", "BLOCKED_WAIT"}
WAIT_REASONS = {"PREDECESSOR", "QA", "REWORK", "CI", "OWNER_GATE", "BLOCKED_DEPENDENCY", "POLICY"}
QA_MODES = {"FULL", "DELTA", "REUSE"}
INVALIDATION_REASONS = {
    "HEAD_DRIFT", "REVIEW_DRIFT", "GATE_DRIFT", "POLICY_DRIFT",
    "MALFORMED_EVIDENCE", "COMMAND_SUPERSEDED", "PRE_QA_BLOCKED",
}
REQUIRED_FIELDS = {
    "schema", "event_id", "issue_number", "pr_number", "worker", "qa",
    "exact_head", "phase", "started_at", "ended_at", "authority",
}
OPTIONAL_FIELDS = {
    "wait_reason", "qa_mode", "qa_invalidation_reason", "rework_cycle_id",
    "candidate_rebuild", "first_pass_findings", "issued_qa_verdict",
    "accepted_qa_verdict", "stale_or_false_safe_verdict", "promotion_id",
}
EVENT_FIELDS = REQUIRED_FIELDS | OPTIONAL_FIELDS


class KpiLedgerError(ValueError):
    pass


def _positive_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise KpiLedgerError(f"{field} must be a positive integer")
    return value


def _nonnegative_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise KpiLedgerError(f"{field} must be a non-negative integer")
    return value


def _parse_time(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise KpiLedgerError(f"{field} must be an ISO-8601 timestamp")
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise KpiLedgerError(f"{field} must be an ISO-8601 timestamp") from exc
    if dt.tzinfo is None:
        raise KpiLedgerError(f"{field} must contain timezone information")
    return dt.astimezone(timezone.utc)


def _optional_enum(value: Any, allowed: set[str], field: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or value not in allowed:
        raise KpiLedgerError(f"unsupported {field}: {value}")
    return value


def _optional_bool(value: Any, field: str) -> bool:
    if value is None:
        return False
    if not isinstance(value, bool):
        raise KpiLedgerError(f"{field} must be boolean")
    return value


def validate_event(event: Any) -> dict[str, Any]:
    if not isinstance(event, dict):
        raise KpiLedgerError("event must be an object")
    missing = sorted(REQUIRED_FIELDS - event.keys())
    unknown = sorted(event.keys() - EVENT_FIELDS)
    if missing:
        raise KpiLedgerError("missing event fields: " + ", ".join(missing))
    if unknown:
        raise KpiLedgerError("unknown event fields: " + ", ".join(unknown))
    if event["schema"] != EVENT_SCHEMA:
        raise KpiLedgerError("unsupported event schema")
    if event["authority"] != AUTHORITY:
        raise KpiLedgerError("KPI event authority must be DATA_ONLY")
    if not isinstance(event["event_id"], str) or not EVENT_ID_RE.fullmatch(event["event_id"]):
        raise KpiLedgerError("invalid event_id")
    issue_number = _positive_int(event["issue_number"], "issue_number")
    pr_number = _positive_int(event["pr_number"], "pr_number")
    worker = str(event["worker"] or "").strip()
    qa = str(event["qa"] or "").strip()
    if not worker or not qa:
        raise KpiLedgerError("worker and qa must be non-empty")
    head = str(event["exact_head"] or "").lower()
    if not SHA_RE.fullmatch(head) or head != event["exact_head"]:
        raise KpiLedgerError("exact_head must be lowercase 40-char SHA")
    phase = event["phase"]
    if phase not in PHASES:
        raise KpiLedgerError(f"unsupported phase: {phase}")
    started = _parse_time(event["started_at"], "started_at")
    ended = _parse_time(event["ended_at"], "ended_at")
    if ended <= started:
        raise KpiLedgerError("event interval must have ended_at > started_at")

    wait_reason = _optional_enum(event.get("wait_reason"), WAIT_REASONS, "wait_reason")
    if phase in WAIT_PHASES and wait_reason is None:
        raise KpiLedgerError(f"wait_reason is required for phase {phase}")
    if phase not in WAIT_PHASES and wait_reason is not None:
        raise KpiLedgerError(f"wait_reason is not allowed for active phase {phase}")
    if phase == "OWNER_WAIT" and wait_reason != "OWNER_GATE":
        raise KpiLedgerError("OWNER_WAIT requires wait_reason=OWNER_GATE")
    if phase == "CI_WAIT" and wait_reason != "CI":
        raise KpiLedgerError("CI_WAIT requires wait_reason=CI")
    if phase == "QA_WAIT" and wait_reason != "QA":
        raise KpiLedgerError("QA_WAIT requires wait_reason=QA")

    qa_mode = _optional_enum(event.get("qa_mode"), QA_MODES, "qa_mode")
    if phase in {"QA_WAIT", "QA_ACTIVE"} and qa_mode is None:
        raise KpiLedgerError(f"qa_mode is required for phase {phase}")
    if phase not in {"QA_WAIT", "QA_ACTIVE"} and qa_mode is not None:
        raise KpiLedgerError(f"qa_mode is not allowed for phase {phase}")

    invalidation_reason = _optional_enum(
        event.get("qa_invalidation_reason"), INVALIDATION_REASONS, "qa_invalidation_reason"
    )
    rework_cycle_id = event.get("rework_cycle_id")
    if phase == "REWORK":
        if rework_cycle_id is None:
            raise KpiLedgerError("REWORK requires rework_cycle_id")
        rework_cycle_id = _positive_int(rework_cycle_id, "rework_cycle_id")
    elif rework_cycle_id is not None:
        raise KpiLedgerError("rework_cycle_id is only allowed for REWORK")

    first_pass_findings = event.get("first_pass_findings")
    if first_pass_findings is not None:
        first_pass_findings = _nonnegative_int(first_pass_findings, "first_pass_findings")
        if phase != "QA_ACTIVE":
            raise KpiLedgerError("first_pass_findings is only allowed for QA_ACTIVE")

    candidate_rebuild = _optional_bool(event.get("candidate_rebuild"), "candidate_rebuild")
    issued = _optional_bool(event.get("issued_qa_verdict"), "issued_qa_verdict")
    accepted = _optional_bool(event.get("accepted_qa_verdict"), "accepted_qa_verdict")
    stale = _optional_bool(event.get("stale_or_false_safe_verdict"), "stale_or_false_safe_verdict")
    if any((issued, accepted, stale)) and phase != "QA_ACTIVE":
        raise KpiLedgerError("QA verdict counters are only allowed for QA_ACTIVE")
    if accepted and not issued:
        raise KpiLedgerError("accepted_qa_verdict requires issued_qa_verdict")
    if stale and not issued:
        raise KpiLedgerError("stale_or_false_safe_verdict requires issued_qa_verdict")

    promotion_id = event.get("promotion_id")
    if promotion_id is not None and (not isinstance(promotion_id, str) or not promotion_id.strip()):
        raise KpiLedgerError("promotion_id must be a non-empty string when present")

    return {
        "schema": EVENT_SCHEMA,
        "event_id": event["event_id"],
        "issue_number": issue_number,
        "pr_number": pr_number,
        "worker": worker,
        "qa": qa,
        "exact_head": head,
        "phase": phase,
        "started_at": event["started_at"],
        "ended_at": event["ended_at"],
        "wait_reason": wait_reason,
        "qa_mode": qa_mode,
        "qa_invalidation_reason": invalidation_reason,
        "rework_cycle_id": rework_cycle_id,
        "candidate_rebuild": candidate_rebuild,
        "first_pass_findings": first_pass_findings,
        "issued_qa_verdict": issued,
        "accepted_qa_verdict": accepted,
        "stale_or_false_safe_verdict": stale,
        "promotion_id": promotion_id.strip() if isinstance(promotion_id, str) else None,
        "authority": AUTHORITY,
    }


def validate_ledger(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise KpiLedgerError("ledger must be an object")
    if set(payload) != {"schema", "authority", "events"}:
        raise KpiLedgerError("ledger fields must be exactly schema, authority, events")
    if payload["schema"] != LEDGER_SCHEMA:
        raise KpiLedgerError("unsupported ledger schema")
    if payload["authority"] != AUTHORITY:
        raise KpiLedgerError("ledger authority must be DATA_ONLY")
    if not isinstance(payload["events"], list) or not payload["events"]:
        raise KpiLedgerError("ledger events must be a non-empty list")

    events = [validate_event(event) for event in payload["events"]]
    ids = [event["event_id"] for event in events]
    if len(ids) != len(set(ids)):
        raise KpiLedgerError("duplicate event_id in ledger")

    anchor = events[0]
    for event in events[1:]:
        for field in ("issue_number", "pr_number", "worker", "qa"):
            if event[field] != anchor[field]:
                raise KpiLedgerError(f"ledger mixes different {field} values")

    previous_end: datetime | None = None
    for event in events:
        started = _parse_time(event["started_at"], "started_at")
        ended = _parse_time(event["ended_at"], "ended_at")
        if previous_end is not None and started < previous_end:
            raise KpiLedgerError("event intervals overlap or are out of append-only order")
        previous_end = ended

    return {"schema": LEDGER_SCHEMA, "authority": AUTHORITY, "events": events}


def append_event(ledger: Any, event: Any) -> dict[str, Any]:
    current = validate_ledger(ledger)
    candidate = validate_event(event)
    if candidate["event_id"] in {item["event_id"] for item in current["events"]}:
        raise KpiLedgerError("duplicate event_id in append")
    anchor = current["events"][0]
    for field in ("issue_number", "pr_number", "worker", "qa"):
        if candidate[field] != anchor[field]:
            raise KpiLedgerError(f"appended event changes ledger {field}")
    last_end = _parse_time(current["events"][-1]["ended_at"], "ended_at")
    next_start = _parse_time(candidate["started_at"], "started_at")
    if next_start < last_end:
        raise KpiLedgerError("append would overlap or rewrite prior telemetry interval")
    return validate_ledger({**current, "events": [*current["events"], candidate]})


def _duration(event: dict[str, Any]) -> float:
    return (_parse_time(event["ended_at"], "ended_at") - _parse_time(event["started_at"], "started_at")).total_seconds()


def summarize(ledger: Any) -> dict[str, Any]:
    normalized = validate_ledger(ledger)
    events = normalized["events"]
    by_phase = {phase: 0.0 for phase in sorted(PHASES)}
    wait_by_reason = {reason: 0.0 for reason in sorted(WAIT_REASONS)}
    qa_modes = {mode: 0 for mode in sorted(QA_MODES)}
    invalidations = {reason: 0 for reason in sorted(INVALIDATION_REASONS)}
    rework_cycles: set[int] = set()
    first_pass_values: list[int] = []

    for event in events:
        seconds = _duration(event)
        by_phase[event["phase"]] += seconds
        if event["wait_reason"]:
            wait_by_reason[event["wait_reason"]] += seconds
        if event["qa_mode"] and event["phase"] == "QA_ACTIVE":
            qa_modes[event["qa_mode"]] += 1
        if event["qa_invalidation_reason"]:
            invalidations[event["qa_invalidation_reason"]] += 1
        if event["rework_cycle_id"] is not None:
            rework_cycles.add(event["rework_cycle_id"])
        if event["first_pass_findings"] is not None:
            first_pass_values.append(event["first_pass_findings"])

    first_start = _parse_time(events[0]["started_at"], "started_at")
    last_end = _parse_time(events[-1]["ended_at"], "ended_at")
    lead = (last_end - first_start).total_seconds()
    observed = sum(by_phase.values())
    active = by_phase["EXECUTION"] + by_phase["REWORK"] + by_phase["QA_ACTIVE"]
    waiting = sum(by_phase[phase] for phase in WAIT_PHASES)
    first_pass_findings = first_pass_values[0] if first_pass_values else None

    anchor = events[0]
    return {
        "schema": SUMMARY_SCHEMA,
        "authority": AUTHORITY,
        "issue_number": anchor["issue_number"],
        "pr_number": anchor["pr_number"],
        "worker": anchor["worker"],
        "qa": anchor["qa"],
        "exact_heads": sorted({event["exact_head"] for event in events}),
        "event_count": len(events),
        "lead_time_seconds": lead,
        "observed_interval_seconds": observed,
        "unattributed_time_seconds": lead - observed,
        "active_processing_time_seconds": active,
        "waiting_time_seconds": waiting,
        "execution_time_seconds": by_phase["EXECUTION"],
        "rework_time_seconds": by_phase["REWORK"],
        "rework_cycles": len(rework_cycles),
        "qa_wait_time_seconds": by_phase["QA_WAIT"],
        "qa_active_time_seconds": by_phase["QA_ACTIVE"],
        "queue_wait_time_seconds": by_phase["QUEUE_WAIT"] + by_phase["BLOCKED_WAIT"],
        "owner_wait_time_seconds": by_phase["OWNER_WAIT"],
        "ci_wait_time_seconds": by_phase["CI_WAIT"],
        "wait_by_reason_seconds": wait_by_reason,
        "qa_modes": qa_modes,
        "qa_invalidation_count": sum(invalidations.values()),
        "qa_invalidations_by_reason": invalidations,
        "candidate_rebuild_count": sum(1 for event in events if event["candidate_rebuild"]),
        "first_pass_findings": first_pass_findings,
        "first_pass_pass": None if first_pass_findings is None else first_pass_findings == 0,
        "issued_qa_verdicts": sum(1 for event in events if event["issued_qa_verdict"]),
        "accepted_qa_verdicts": sum(1 for event in events if event["accepted_qa_verdict"]),
        "false_safe_or_stale_verdict_count": sum(1 for event in events if event["stale_or_false_safe_verdict"]),
    }


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path | None, value: Any) -> None:
    text = json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if path:
        path.write_text(text, encoding="utf-8")
    else:
        print(text, end="")


def main() -> int:
    parser = argparse.ArgumentParser(description="KAT9I_OS DATA-only Worker KPI Ledger")
    sub = parser.add_subparsers(dest="command", required=True)
    validate_cmd = sub.add_parser("validate")
    validate_cmd.add_argument("ledger", type=Path)
    validate_cmd.add_argument("--output", type=Path)
    summary_cmd = sub.add_parser("summarize")
    summary_cmd.add_argument("ledger", type=Path)
    summary_cmd.add_argument("--output", type=Path)
    append_cmd = sub.add_parser("append")
    append_cmd.add_argument("ledger", type=Path)
    append_cmd.add_argument("event", type=Path)
    append_cmd.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "validate":
            result = validate_ledger(_load(args.ledger))
        elif args.command == "summarize":
            result = summarize(_load(args.ledger))
        else:
            result = append_event(_load(args.ledger), _load(args.event))
        _write(args.output, result)
        print(f"KAT9I_WORKER_KPI={args.command.upper()} | authority={AUTHORITY}")
        return 0
    except (KpiLedgerError, OSError, json.JSONDecodeError) as exc:
        print(f"KAT9I_WORKER_KPI=FAIL | {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
