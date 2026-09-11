#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

SCHEMA = "KAT9I_G0_AUDIT/1"
DOMAIN_ORDER = ("views", "cards", "schema", "governance", "other")


def finding_domain(code: str) -> str:
    value = str(code or "")
    if value.startswith("VIEW_"):
        return "views"
    if value.startswith(("PROJECT_ITEM_", "OPEN_WORK_", "OPEN_P01_", "CONTROLLED_")) or value == "GATE_62":
        return "cards"
    if value.startswith(("FIELD_", "ITERATION_")) or value in {"PROJECT_TITLE", "PROJECT_LINK"}:
        return "schema"
    if value.startswith("RULESET_") or value in {"MILESTONE", "AUDIT_ERROR", "AUDIT_OUTPUT_MISSING"}:
        return "governance"
    return "other"


def enrich(summary: dict[str, Any]) -> dict[str, Any]:
    if summary.get("schema") != SCHEMA:
        raise ValueError(f"Ожидалась schema {SCHEMA}")
    findings = summary.get("findings")
    if not isinstance(findings, list):
        raise ValueError("findings должен быть списком")
    if summary.get("finding_count") != len(findings):
        raise ValueError("finding_count не совпадает с длиной findings")
    grouped: dict[str, list[dict[str, Any]]] = {domain: [] for domain in DOMAIN_ORDER}
    counts: Counter[str] = Counter()
    for finding in findings:
        if not isinstance(finding, dict) or not finding.get("code") or "message" not in finding:
            raise ValueError("Каждый finding должен содержать code и message")
        domain = finding_domain(str(finding["code"]))
        counts[domain] += 1
        grouped[domain].append({"code": finding["code"], "message": finding["message"]})
    result = dict(summary)
    result["domain_counts"] = {domain: counts.get(domain, 0) for domain in DOMAIN_ORDER}
    result["findings_by_domain"] = grouped
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Добавить домены к Evidence G0-аудита без изменения исходных findings")
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    data = json.loads(args.input.read_text(encoding="utf-8"))
    enriched = enrich(data)
    target = args.output or args.input
    target.write_text(json.dumps(enriched, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(enriched.get("domain_counts"), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
