#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict
from pathlib import Path
from typing import Any

import g0_project_remediation as core


def safe_remediation(owner: str, repository: str, project_number: int, *, apply: bool) -> dict[str, Any]:
    if (owner, repository, project_number) != (core.OWNER, core.REPOSITORY, core.PROJECT_NUMBER):
        raise core.RemediationError("This bounded remediation is pinned to KAT9I_OS Project #2")

    before = core.collect_live(owner, repository, project_number)

    # Полный fail-closed preflight обязан завершиться до первой mutation.
    core.worker_option_plan(before)
    core.view_delete_plan(before)
    core.find_select_field(before, "Приоритет")
    core.find_select_field(before, "Этап")
    core.find_select_field(before, "Исполнение")
    core.find_select_field(before, "Статус")

    missing = core.missing_open_items(before)
    if missing:
        raise core.RemediationError(
            "Open Project inventory is incomplete; remediation refuses mutation: " + ", ".join(missing)
        )

    outcomes = core.collect_closed_outcomes(before)
    plan = core.build_plan(before, outcomes)
    if plan.missing_open_items:
        raise core.RemediationError(
            "Preflight produced incomplete Project inventory: " + ", ".join(plan.missing_open_items)
        )

    report: dict[str, Any] = {
        "schema": "KAT9I_G0_REMEDIATION/1",
        "mode": "APPLY" if apply else "PLAN",
        "before_audit": [asdict(f) for f in core.audit_validate(before)],
        "plan": plan.jsonable(),
    }
    if not apply:
        return report

    project_id = str((before.get("project") or {}).get("id") or "")
    if not project_id:
        raise core.RemediationError("Project id missing")

    # Первая mutation разрешена только после полного build_plan выше.
    core.apply_worker_field_update(plan.worker_field_update)
    core.apply_delete_views(plan.delete_views)
    core.apply_item_edits(project_id, plan.item_edits)

    after = core.collect_live(owner, repository, project_number)
    findings = core.audit_validate(after)
    report["after_audit"] = [asdict(f) for f in findings]
    report["verdict"] = "PASS" if not findings else "FAIL"
    if findings:
        raise core.RemediationError(
            "Post-remediation G0 audit still has findings: " + ", ".join(f.code for f in findings)
        )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Production-safe G0 Project remediation for Issue #134")
    parser.add_argument("--owner", default=core.OWNER)
    parser.add_argument("--repository", default=core.REPOSITORY)
    parser.add_argument("--project-number", type=int, default=core.PROJECT_NUMBER)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    def write_report(report: dict[str, Any]) -> None:
        text = json.dumps(report, ensure_ascii=False, indent=2)
        print(text)
        if args.output:
            args.output.write_text(text + "\n", encoding="utf-8")

    if not os.environ.get("GH_TOKEN"):
        report = {
            "schema": "KAT9I_G0_REMEDIATION/1",
            "verdict": "ERROR",
            "reason": "GH_TOKEN is required",
        }
        write_report(report)
        return 2

    try:
        report = safe_remediation(args.owner, args.repository, args.project_number, apply=args.apply)
        write_report(report)
        return 0
    except core.RemediationError as exc:
        report = {
            "schema": "KAT9I_G0_REMEDIATION/1",
            "verdict": "ERROR",
            "reason": str(exc),
        }
        write_report(report)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
