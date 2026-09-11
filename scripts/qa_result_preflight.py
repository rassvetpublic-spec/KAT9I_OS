#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.qa_result_bridge import (
    FOLLOW_UP_HEADER,
    RESULT_FIELDS,
    RESULT_MARKER,
    BridgeError,
    _flatten_comments,
    _latest_command,
    _section_lines,
    parse_envelope,
    validate_result,
)

SCHEMA = "KAT9I_QA_RESULT_PREFLIGHT/1"
_FUTURE = datetime.max.replace(tzinfo=timezone.utc)


def preflight(body: str, comments_payload: Any, current_pr: dict[str, Any]) -> dict[str, Any]:
    """Проверить proposed QA-RESULT до публикации review, без side effects."""
    result = validate_result(parse_envelope(body, RESULT_MARKER, RESULT_FIELDS))
    follow_up_lines = _section_lines(body, FOLLOW_UP_HEADER)
    if follow_up_lines is None:
        raise BridgeError("QA result must contain a separate FOLLOW_UP_CANDIDATES section")
    if result["follow_up_candidates"] > 0 and not follow_up_lines:
        raise BridgeError("QA result declares follow-up candidates but section has no content")

    pr_number = current_pr.get("number")
    if not isinstance(pr_number, int) or pr_number <= 0:
        raise BridgeError("current PR does not contain a valid number")
    if current_pr.get("state") != "open":
        raise BridgeError("current PR is not open")
    live_head = str(((current_pr.get("head") or {}).get("sha") or "")).lower()
    if result["target_pr"] != pr_number:
        raise BridgeError("QA result target_pr does not match current PR")
    if result["exact_head"] != live_head:
        raise BridgeError("QA result exact_head is stale against live PR HEAD")

    comments = _flatten_comments(comments_payload)
    _, command = _latest_command(
        comments,
        pr_number=pr_number,
        before=_FUTURE,
        expected_command_id=result["command_id"],
    )
    for field in ("controller", "role", "exact_head", "qa_mode", "result_sink"):
        if command[field] != result[field]:
            raise BridgeError(f"command/result mismatch: {field}")
    if command["executor_canonical"] != result["executor_canonical"]:
        raise BridgeError("command/result mismatch: executor")
    if command["exact_head"] != live_head:
        raise BridgeError("QA-COMMAND exact_head is stale against live PR HEAD")

    return {
        "schema": SCHEMA,
        "authority": "VALIDATION_ONLY",
        "verdict": "PASS",
        "contract_marker": RESULT_MARKER,
        "contract_fields": sorted(RESULT_FIELDS),
        "command_id": result["command_id"],
        "target_pr": result["target_pr"],
        "exact_head": live_head,
        "qa_mode": result["qa_mode"],
        "qa_verdict": result["verdict"],
        "blocking_findings": result["blocking_findings"],
        "follow_up_candidates": result["follow_up_candidates"],
    }


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_body(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    return Path(path).read_text(encoding="utf-8")


def _write_result(result: dict[str, Any], output: Path | None) -> None:
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if output:
        output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fail-closed pre-publication QA-RESULT preflight на production bridge contract"
    )
    parser.add_argument("input", nargs="?", default="-", help="Proposed QA-RESULT или '-' для stdin")
    parser.add_argument("--comments", type=Path, required=True, help="Owner PR conversation comments JSON")
    parser.add_argument("--current-pr", type=Path, required=True, help="Live PR JSON")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    try:
        result = preflight(_read_body(args.input), _read_json(args.comments), _read_json(args.current_pr))
    except (BridgeError, OSError, json.JSONDecodeError) as exc:
        _write_result({"schema": SCHEMA, "authority": "VALIDATION_ONLY", "verdict": "FAIL", "reason": str(exc)}, args.output)
        return 2

    _write_result(result, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
