#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from scripts.required_check_state import QUALITY_WORKFLOW_NAME, QUALITY_WORKFLOW_PATH

SCHEMA = "KAT9I_PRE_QA_BARRIER/1"
SECTION_HEADER = "PRE_QA_BARRIER"
BARRIER_VERSION = "1"
AUTHORITY = "VALIDATION_ONLY"
SHA40_RE = re.compile(r"^[0-9a-f]{40}$")
KEY_RE = re.compile(r"^[a-z][a-z0-9_]*$")
RECEIPT_FIELDS = {
    "barrier_version",
    "target_pr",
    "exact_head",
    "worker",
    "qa",
    "quality_run_id",
    "quality_verdict",
    "blocking_threads",
    "inventory_verdict",
    "schema_process_verdict",
    "authority",
    "receipt_digest",
}
CORE_FIELDS = tuple(sorted(RECEIPT_FIELDS - {"receipt_digest"}))


class PreQaBarrierError(ValueError):
    pass


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _positive_int(value: Any, field: str) -> int:
    text = str(value)
    if not re.fullmatch(r"[1-9][0-9]*", text):
        raise PreQaBarrierError(f"{field} must be a positive integer")
    return int(text)


def _nonnegative_int(value: Any, field: str) -> int:
    text = str(value)
    if not re.fullmatch(r"0|[1-9][0-9]*", text):
        raise PreQaBarrierError(f"{field} must be a non-negative integer")
    return int(text)


def _identity(value: str) -> str:
    normalized = re.sub(r"\s+", " ", str(value or "").strip()).lower()
    aliases = {
        "chatgpt": "ChatGPT",
        "agy": "AGY",
        "antigravity": "AGY",
        "antigravity (agy)": "AGY",
        "антигравити": "AGY",
    }
    if normalized in aliases:
        return aliases[normalized]
    if not normalized:
        raise PreQaBarrierError("identity must not be empty")
    return str(value).strip()


def _review_threads(payload: Any, target_pr: int) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        raise PreQaBarrierError("INVENTORY_INCOMPLETE: review threads payload must be GraphQL object")
    try:
        pr = payload["data"]["repository"]["pullRequest"]
        threads = pr["reviewThreads"]
    except (KeyError, TypeError) as exc:
        raise PreQaBarrierError("INVENTORY_INCOMPLETE: review threads payload has unexpected shape") from exc

    number = pr.get("number")
    if number is not None and int(number) != target_pr:
        raise PreQaBarrierError("review thread inventory belongs to another PR")
    page_info = threads.get("pageInfo") or {}
    if page_info.get("hasNextPage") is not False:
        raise PreQaBarrierError("INVENTORY_INCOMPLETE: review thread pagination is incomplete")
    nodes = threads.get("nodes")
    if not isinstance(nodes, list):
        raise PreQaBarrierError("INVENTORY_INCOMPLETE: review thread nodes must be a list")

    result: list[dict[str, Any]] = []
    for thread in nodes:
        if not isinstance(thread, dict):
            raise PreQaBarrierError("INVENTORY_INCOMPLETE: review thread must be an object")
        thread_id = thread.get("id")
        resolved = thread.get("isResolved")
        if not isinstance(thread_id, str) or not thread_id:
            raise PreQaBarrierError("INVENTORY_INCOMPLETE: review thread id is missing")
        if not isinstance(resolved, bool):
            raise PreQaBarrierError("INVENTORY_INCOMPLETE: review thread isResolved must be boolean")
        comments = thread.get("comments") or {}
        comments_page = comments.get("pageInfo") if isinstance(comments, dict) else None
        if not isinstance(comments_page, dict) or comments_page.get("hasNextPage") is not False:
            raise PreQaBarrierError("INVENTORY_INCOMPLETE: review comment pagination is incomplete")
        result.append({"id": thread_id, "isResolved": resolved})
    return result


def _validate_quality_run(payload: Any, target_pr: int, head: str) -> int:
    if not isinstance(payload, dict):
        raise PreQaBarrierError("QUALITY_MISSING: quality run payload must be an object")
    run_id = _positive_int(payload.get("id"), "quality_run_id")
    if payload.get("path") != QUALITY_WORKFLOW_PATH or payload.get("name") != QUALITY_WORKFLOW_NAME:
        raise PreQaBarrierError("QUALITY_MISMATCH: expected canonical quality workflow")
    if str(payload.get("head_sha") or "").lower() != head:
        raise PreQaBarrierError("QUALITY_STALE: quality run HEAD does not match live PR HEAD")
    if payload.get("status") != "completed" or payload.get("conclusion") != "success":
        raise PreQaBarrierError("QUALITY_FAIL: canonical quality run is not successful")
    pull_requests = payload.get("pull_requests")
    if isinstance(pull_requests, list) and pull_requests:
        numbers = {int(item.get("number")) for item in pull_requests if isinstance(item, dict) and item.get("number") is not None}
        if target_pr not in numbers:
            raise PreQaBarrierError("QUALITY_MISMATCH: quality run belongs to another PR")
    return run_id


def _receipt_core(receipt: dict[str, Any]) -> dict[str, str]:
    return {key: str(receipt[key]) for key in CORE_FIELDS}


def evaluate(
    current_pr: dict[str, Any],
    review_threads_payload: Any,
    quality_run: dict[str, Any],
    worker: str,
    qa: str,
) -> dict[str, Any]:
    if not isinstance(current_pr, dict):
        raise PreQaBarrierError("current PR payload must be an object")
    target_pr = _positive_int(current_pr.get("number"), "target_pr")
    if current_pr.get("state") != "open":
        raise PreQaBarrierError("PR_STATE: current PR is not open")
    if current_pr.get("draft") is True:
        raise PreQaBarrierError("PR_STATE: draft PR cannot enter QA")
    head = str(((current_pr.get("head") or {}).get("sha") or "")).lower()
    if not SHA40_RE.fullmatch(head):
        raise PreQaBarrierError("HEAD_MALFORMED: live PR HEAD must be 40-char lowercase SHA")

    canonical_worker = _identity(worker)
    canonical_qa = _identity(qa)
    if canonical_worker.casefold() == canonical_qa.casefold():
        raise PreQaBarrierError("ROLE_COLLISION: Worker and QA must be different identities")

    quality_run_id = _validate_quality_run(quality_run, target_pr, head)
    threads = _review_threads(review_threads_payload, target_pr)
    unresolved = sorted(item["id"] for item in threads if not item["isResolved"])
    if unresolved:
        raise PreQaBarrierError("PRE_QA_BLOCKED: unresolved review threads: " + ",".join(unresolved))

    receipt: dict[str, Any] = {
        "barrier_version": BARRIER_VERSION,
        "target_pr": target_pr,
        "exact_head": head,
        "worker": canonical_worker,
        "qa": canonical_qa,
        "quality_run_id": quality_run_id,
        "quality_verdict": "PASS",
        "blocking_threads": 0,
        "inventory_verdict": "PASS",
        "schema_process_verdict": "PASS",
        "authority": AUTHORITY,
    }
    receipt["receipt_digest"] = _digest(_receipt_core(receipt))
    return {"schema": SCHEMA, "verdict": "PASS", **receipt}


def validate_receipt(receipt: dict[str, Any]) -> dict[str, str]:
    if not isinstance(receipt, dict):
        raise PreQaBarrierError("receipt must be an object")
    normalized = {key: str(value) for key, value in receipt.items() if key not in {"schema", "verdict"}}
    missing = sorted(RECEIPT_FIELDS - normalized.keys())
    unknown = sorted(normalized.keys() - RECEIPT_FIELDS)
    if missing:
        raise PreQaBarrierError("missing receipt fields: " + ", ".join(missing))
    if unknown:
        raise PreQaBarrierError("unknown receipt fields: " + ", ".join(unknown))
    if normalized["barrier_version"] != BARRIER_VERSION:
        raise PreQaBarrierError("unsupported barrier_version")
    _positive_int(normalized["target_pr"], "target_pr")
    if not SHA40_RE.fullmatch(normalized["exact_head"]):
        raise PreQaBarrierError("invalid exact_head")
    worker = _identity(normalized["worker"])
    qa = _identity(normalized["qa"])
    if worker.casefold() == qa.casefold():
        raise PreQaBarrierError("ROLE_COLLISION: Worker and QA must be different identities")
    _positive_int(normalized["quality_run_id"], "quality_run_id")
    _nonnegative_int(normalized["blocking_threads"], "blocking_threads")
    if normalized["blocking_threads"] != "0":
        raise PreQaBarrierError("receipt contains blocking review threads")
    for field in ("quality_verdict", "inventory_verdict", "schema_process_verdict"):
        if normalized[field] != "PASS":
            raise PreQaBarrierError(f"{field} must be PASS")
    if normalized["authority"] != AUTHORITY:
        raise PreQaBarrierError("receipt authority must be VALIDATION_ONLY")
    expected = _digest({key: normalized[key] for key in CORE_FIELDS})
    if normalized["receipt_digest"] != expected:
        raise PreQaBarrierError("receipt_digest mismatch")
    return normalized


def render_barrier_section(receipt: dict[str, Any]) -> str:
    normalized = validate_receipt(receipt)
    order = (
        "barrier_version", "target_pr", "exact_head", "worker", "qa",
        "quality_run_id", "quality_verdict", "blocking_threads",
        "inventory_verdict", "schema_process_verdict", "authority", "receipt_digest",
    )
    return SECTION_HEADER + "\n" + "\n".join(f"{key}={normalized[key]}" for key in order)


def parse_barrier_section(body: str) -> dict[str, str]:
    lines = (body or "").splitlines()
    positions = [index for index, raw in enumerate(lines) if raw.strip() == SECTION_HEADER]
    if len(positions) != 1:
        raise PreQaBarrierError("exactly one PRE_QA_BARRIER section is required")
    meta: dict[str, str] = {}
    for raw in lines[positions[0] + 1:]:
        line = raw.strip()
        if not line or "=" not in line:
            break
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not KEY_RE.fullmatch(key):
            raise PreQaBarrierError(f"invalid barrier key: {key}")
        if key not in RECEIPT_FIELDS:
            raise PreQaBarrierError(f"unknown barrier key: {key}")
        if not value:
            raise PreQaBarrierError(f"empty barrier value: {key}")
        if key in meta:
            raise PreQaBarrierError(f"duplicate barrier key: {key}")
        meta[key] = value
    return validate_receipt(meta)


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path | None, payload: Any) -> None:
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if path:
        path.write_text(text, encoding="utf-8")
    else:
        print(text, end="")


def main() -> int:
    parser = argparse.ArgumentParser(description="KAT9I_OS deterministic PRE-QA barrier")
    parser.add_argument("--current-pr", type=Path, required=True)
    parser.add_argument("--review-threads", type=Path, required=True)
    parser.add_argument("--quality-run", type=Path, required=True)
    parser.add_argument("--worker", required=True)
    parser.add_argument("--qa", required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--section-output", type=Path)
    args = parser.parse_args()
    try:
        result = evaluate(
            _load(args.current_pr),
            _load(args.review_threads),
            _load(args.quality_run),
            args.worker,
            args.qa,
        )
        _write(args.output, result)
        if args.section_output:
            args.section_output.write_text(render_barrier_section(result) + "\n", encoding="utf-8")
        print(f"KAT9I_PRE_QA_BARRIER=PASS | {result['receipt_digest']}")
        return 0
    except (PreQaBarrierError, OSError, json.JSONDecodeError) as exc:
        _write(args.output, {"schema": SCHEMA, "authority": AUTHORITY, "verdict": "FAIL", "reason": str(exc)})
        print(f"KAT9I_PRE_QA_BARRIER=FAIL | {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
