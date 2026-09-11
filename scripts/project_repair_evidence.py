#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scripts.g0_control_plane_audit import summarize, validate
from scripts.project_audit_domains import DOMAIN_ORDER, enrich

SCHEMA = "KAT9I_PROJECT_REPAIR_EVIDENCE/1"
AUDIT_SCHEMA = "KAT9I_G0_AUDIT/1"


def _enriched_audit(summary: dict[str, Any]) -> dict[str, Any]:
    if summary.get("schema") != AUDIT_SCHEMA:
        raise ValueError(f"Ожидалась schema {AUDIT_SCHEMA}")
    return enrich(summary)


def audit_from_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    return _enriched_audit(summarize(snapshot, validate(snapshot)))


def build_summary(
    *,
    target_domain: str,
    apply_outcome: str,
    before_snapshot: dict[str, Any],
    after_audit: dict[str, Any],
) -> dict[str, Any]:
    if target_domain not in DOMAIN_ORDER or target_domain == "other":
        raise ValueError(f"Unsupported target_domain: {target_domain}")
    if apply_outcome not in {"success", "failure", "cancelled", "skipped"}:
        raise ValueError(f"Unsupported apply_outcome: {apply_outcome}")

    before = _enriched_audit(audit_from_snapshot(before_snapshot))
    after = _enriched_audit(after_audit)
    before_counts = {domain: int(before["domain_counts"].get(domain, 0)) for domain in DOMAIN_ORDER}
    after_counts = {domain: int(after["domain_counts"].get(domain, 0)) for domain in DOMAIN_ORDER}
    unrelated_regressions = {
        domain: {"before": before_counts[domain], "after": after_counts[domain]}
        for domain in DOMAIN_ORDER
        if domain not in {target_domain, "other"} and after_counts[domain] > before_counts[domain]
    }
    if after_counts["other"] > before_counts["other"]:
        unrelated_regressions["other"] = {"before": before_counts["other"], "after": after_counts["other"]}

    target_cleared = after_counts[target_domain] == 0
    repair_pass = apply_outcome == "success" and target_cleared and not unrelated_regressions
    if apply_outcome != "success":
        repair_reason = f"apply_outcome={apply_outcome}"
    elif not target_cleared:
        repair_reason = f"target domain {target_domain} still has {after_counts[target_domain]} findings"
    elif unrelated_regressions:
        repair_reason = "unrelated domain regression detected"
    else:
        repair_reason = "target domain cleared without new unrelated drift"

    return {
        "schema": SCHEMA,
        "authority": "EVIDENCE_ONLY",
        "target_domain": target_domain,
        "apply_outcome": apply_outcome,
        "repair_verdict": "PASS" if repair_pass else "FAIL",
        "repair_reason": repair_reason,
        "target_before": before_counts[target_domain],
        "target_after": after_counts[target_domain],
        "before_domain_counts": before_counts,
        "after_domain_counts": after_counts,
        "unrelated_regressions": unrelated_regressions,
        "global_audit_verdict": str(after.get("verdict") or "ERROR"),
        "global_finding_count": int(after.get("finding_count") or 0),
    }


def _read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} должен содержать JSON object")
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description="Разделить bounded repair verdict и full post-audit verdict")
    parser.add_argument("--target-domain", choices=[d for d in DOMAIN_ORDER if d != "other"])
    parser.add_argument("--apply-outcome", choices=["success", "failure", "cancelled", "skipped"])
    parser.add_argument("--before", type=Path)
    parser.add_argument("--after-audit", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--check-summary", type=Path)
    args = parser.parse_args()

    if args.check_summary:
        summary = _read_json(args.check_summary)
        if summary.get("schema") != SCHEMA or summary.get("repair_verdict") != "PASS":
            print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
            return 1
        print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
        return 0

    required = (args.target_domain, args.apply_outcome, args.before, args.after_audit, args.output)
    if any(value is None for value in required):
        parser.error("build mode requires --target-domain, --apply-outcome, --before, --after-audit and --output")

    summary = build_summary(
        target_domain=str(args.target_domain),
        apply_outcome=str(args.apply_outcome),
        before_snapshot=_read_json(args.before),
        after_audit=_read_json(args.after_audit),
    )
    args.output.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
