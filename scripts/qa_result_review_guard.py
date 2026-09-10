#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

COMMAND_MARKER = "KAT9I-CONTROL/1 | QA-COMMAND"
RESULT_MARKER = "KAT9I-QA-RESULT/1"


class ReviewGuardError(ValueError):
    pass


def _time(value: Any) -> datetime:
    text = str(value or "")
    if not text:
        raise ReviewGuardError("MALFORMED_EVIDENCE: missing timestamp")
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ReviewGuardError("MALFORMED_EVIDENCE: invalid timestamp") from exc


def _flatten(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        return [value]
    if not isinstance(value, list):
        raise ReviewGuardError("MALFORMED_EVIDENCE: payload must be list/object")
    out: list[dict[str, Any]] = []
    for item in value:
        if isinstance(item, list):
            out.extend(_flatten(item))
        elif isinstance(item, dict):
            out.append(item)
        else:
            raise ReviewGuardError("MALFORMED_EVIDENCE: payload contains unsupported item")
    return out


def _first_line(body: Any) -> str:
    lines = str(body or "").splitlines()
    return lines[0].strip() if lines else ""


def _field(body: Any, key: str) -> str | None:
    for raw in str(body or "").splitlines()[1:]:
        line = raw.strip()
        if not line:
            break
        if "=" not in line:
            continue
        current, value = line.split("=", 1)
        if current.strip() == key:
            return value.strip()
    return None


def assert_single_result(
    comments_payload: Any,
    reviews_payload: Any,
    *,
    command_id: str,
    selected_review_id: int,
) -> None:
    commands: list[dict[str, Any]] = []
    for comment in _flatten(comments_payload):
        if comment.get("author_association") != "OWNER":
            continue
        body = comment.get("body") or ""
        if _first_line(body) != COMMAND_MARKER:
            continue
        if _field(body, "command_id") == command_id:
            commands.append(comment)
    if len(commands) != 1:
        raise ReviewGuardError(
            "MALFORMED_EVIDENCE: active command_id must resolve to exactly one owner QA-COMMAND"
        )
    command_time = _time(commands[0].get("created_at"))

    reviews = _flatten(reviews_payload)
    selected_seen = False
    competing: list[str] = []
    for review in reviews:
        review_id = review.get("id")
        if review_id is None:
            raise ReviewGuardError("MALFORMED_EVIDENCE: review without id")
        if int(review_id) == int(selected_review_id):
            selected_seen = True
            continue
        body = review.get("body") or ""
        if _first_line(body) != RESULT_MARKER:
            continue
        submitted = _time(review.get("submitted_at"))
        if submitted <= command_time:
            continue
        competing.append(str(review_id))

    if not selected_seen:
        raise ReviewGuardError("MALFORMED_EVIDENCE: selected QA review is absent from review inventory")
    if competing:
        raise ReviewGuardError(
            "REVIEW_DRIFT: competing structured QA-RESULT review(s) after active QA-COMMAND: "
            + ", ".join(sorted(competing))
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Reject conflicting structured QA results for active KAT9I QA command")
    parser.add_argument("--comments-path", type=Path, required=True)
    parser.add_argument("--reviews-path", type=Path, required=True)
    parser.add_argument("--command-id", required=True)
    parser.add_argument("--selected-review-id", type=int, required=True)
    args = parser.parse_args()
    try:
        assert_single_result(
            json.loads(args.comments_path.read_text(encoding="utf-8")),
            json.loads(args.reviews_path.read_text(encoding="utf-8")),
            command_id=args.command_id,
            selected_review_id=args.selected_review_id,
        )
        print("KAT9I_QA_RESULT_GUARD=PASS")
        return 0
    except (ReviewGuardError, OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"KAT9I_QA_RESULT_GUARD=REJECT | {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
