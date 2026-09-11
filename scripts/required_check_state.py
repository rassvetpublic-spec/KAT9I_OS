#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

SCHEMA = "KAT9I_REQUIRED_CHECK_STATE/1"
POLICY_SCHEMA = "KAT9I_REQUIRED_CHECK_POLICY/1"
SHA40_RE = re.compile(r"^[0-9a-f]{40}$")
POLICY_PATH = Path(__file__).resolve().parents[1] / "config" / "required_checks.json"


def _load_policy(path: Path = POLICY_PATH) -> dict[str, Any]:
    policy = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(policy, dict) or policy.get("schema") != POLICY_SCHEMA:
        raise ValueError("required-check policy schema mismatch")
    check = policy.get("required_check")
    if not isinstance(check, dict):
        raise ValueError("required_check policy entry is missing")
    required = {
        "workflow_path",
        "workflow_name",
        "check_name",
        "applies_to_pull_requests",
        "docs_only_exempt",
    }
    if set(check) != required:
        raise ValueError("required_check policy fields mismatch")
    for field in ("workflow_path", "workflow_name", "check_name"):
        if not isinstance(check[field], str) or not check[field].strip():
            raise ValueError(f"required_check.{field} must be non-empty string")
    if check["applies_to_pull_requests"] is not True:
        raise ValueError("canonical required check must apply to pull requests")
    if check["docs_only_exempt"] is not False:
        raise ValueError("docs-only PR must not be exempt from required check")
    return check


POLICY = _load_policy()
QUALITY_WORKFLOW_PATH = POLICY["workflow_path"]
QUALITY_WORKFLOW_NAME = POLICY["workflow_name"]
REQUIRED_CHECK_NAME = POLICY["check_name"]


def _receipt_id(receipt: dict[str, Any]) -> int:
    value = receipt.get("id", 0)
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _normalize_receipts(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        receipts = payload
    elif isinstance(payload, dict):
        if isinstance(payload.get("check_runs"), list):
            receipts = payload["check_runs"]
        elif isinstance(payload.get("receipts"), list):
            receipts = payload["receipts"]
        else:
            raise ValueError("check payload must contain check_runs or receipts list")
    else:
        raise ValueError("check payload must be object or list")
    if not all(isinstance(item, dict) for item in receipts):
        raise ValueError("every check receipt must be an object")
    return list(receipts)


def classify_required_check(
    current_head: str,
    payload: Any,
    required_name: str = REQUIRED_CHECK_NAME,
) -> dict[str, Any]:
    head = str(current_head or "").strip().lower()
    if not SHA40_RE.fullmatch(head):
        raise ValueError("current_head must be exact 40-char lowercase SHA")
    receipts = _normalize_receipts(payload)
    matching = [item for item in receipts if str(item.get("name") or "") == required_name]
    exact = [item for item in matching if str(item.get("head_sha") or "").lower() == head]
    stale = [item for item in matching if str(item.get("head_sha") or "").lower() != head]

    selected: dict[str, Any] | None = None
    if exact:
        selected = max(exact, key=_receipt_id)
        status = str(selected.get("status") or "").lower()
        conclusion = str(selected.get("conclusion") or "").lower()
        if status != "completed":
            state = "REQUIRED_CHECK_PENDING"
        elif conclusion == "success":
            state = "REQUIRED_CHECK_SUCCESS"
        else:
            state = "REQUIRED_CHECK_FAILED"
    elif stale:
        selected = max(stale, key=_receipt_id)
        state = "REQUIRED_CHECK_STALE"
    else:
        state = "REQUIRED_CHECK_MISSING"

    result: dict[str, Any] = {
        "schema": SCHEMA,
        "authority": "DIAGNOSTIC_ONLY",
        "current_head": head,
        "required_check": required_name,
        "state": state,
    }
    if selected is not None:
        result["receipt"] = {
            "id": selected.get("id"),
            "head_sha": selected.get("head_sha"),
            "status": selected.get("status"),
            "conclusion": selected.get("conclusion"),
            "html_url": selected.get("html_url"),
        }
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Classify KAT9I_OS canonical required-check state")
    parser.add_argument("--current-head", required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        payload = json.loads(args.input.read_text(encoding="utf-8"))
        result = classify_required_check(args.current_head, payload)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"KAT9I_REQUIRED_CHECK_STATE=FAIL | {exc}")
        return 2
    text = json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    print(f"KAT9I_REQUIRED_CHECK_STATE={result['state']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
