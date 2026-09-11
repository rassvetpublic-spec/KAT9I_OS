#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from scripts.qa_result_bridge import (
    ATTEST_FIELDS,
    ATTEST_MARKER,
    BridgeError,
    parse_envelope,
    validate_attestation,
)

SCHEMA = "KAT9I_QA_ACCEPT_PREFLIGHT/1"


def preflight(body: str) -> dict[str, Any]:
    meta = parse_envelope(body, ATTEST_MARKER, ATTEST_FIELDS)
    validated = validate_attestation(meta)
    return {
        "schema": SCHEMA,
        "verdict": "PASS",
        "contract_marker": ATTEST_MARKER,
        "contract_fields": sorted(ATTEST_FIELDS),
        "command_id": validated["command_id"],
        "target_pr": validated["target_pr"],
        "controller": validated["controller"],
        "executor": validated["executor_canonical"],
        "role": validated["role"],
        "review_id": validated["review_id"],
        "exact_head": validated["exact_head"],
        "qa_verdict": validated["verdict"],
    }


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
        description="Fail-closed preflight Controller QA-ACCEPT на том же контракте, что production bridge"
    )
    parser.add_argument("input", nargs="?", default="-", help="Файл с QA-ACCEPT или '-' для stdin")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    try:
        result = preflight(_read_body(args.input))
    except (BridgeError, OSError) as exc:
        _write_result({"schema": SCHEMA, "verdict": "FAIL", "reason": str(exc)}, args.output)
        return 2

    _write_result(result, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
