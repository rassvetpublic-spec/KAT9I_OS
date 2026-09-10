#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict
from pathlib import Path
from typing import Any

try:
    from scripts import g0_project_remediation as core
except ModuleNotFoundError:  # Direct `python scripts/...` execution.
    import g0_project_remediation as core


def _canonical_identity(value: str | None) -> str:
    text = str(value or "").strip()
    folded = text.casefold()
    agy_aliases = {"agy"} | {name.casefold() for name in core.AGY_LEGACY_NAMES}
    if folded in agy_aliases:
        return "AGY"
    return folded


def assert_no_canonical_self_qa(snapshot: dict[str, Any]) -> None:
    for item in (snapshot.get("project") or {}).get("items") or []:
        values = core.item_fields(item)
        if not core.is_controlled(values):
            continue
        content = item.get("content") or {}
        state = str(content.get("state") or "").upper()
        title = str(content.get("title") or "")
        if state != "OPEN" or title.startswith("[DATA]"):
            continue
        worker = values.get("Исполнитель")
        qa = values.get("Проверяющий")
        if not worker or not qa:
            continue
        if _canonical_identity(worker) == _canonical_identity(qa):
            ref = str(content.get("url") or item.get("id") or "unknown")
            raise core.RemediationError(
                f"Open controlled item has canonical self-QA after identity normalization: {ref}"
            )


def _readback_into_report(
    report: dict[str, Any], owner: str, repository: str, project_number: int
) -> list[Any] | None:
    try:
        after = core.collect_live(owner, repository, project_number)
        findings = core.audit_validate(after)
        report["after_audit"] = [asdict(f) for f in findings]
        return findings
    except Exception as exc:  # Evidence must survive even when read-back itself fails.
        report["after_audit"] = []
        report["readback_error"] = str(exc)
        return None


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
    assert_no_canonical_self_qa(before)

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
    try:
        core.apply_worker_field_update(plan.worker_field_update)
        core.apply_delete_views(plan.delete_views)
        core.apply_item_edits(project_id, plan.item_edits)
    except core.RemediationError as exc:
        report["verdict"] = "FAIL"
        report["reason"] = str(exc)
        _readback_into_report(report, owner, repository, project_number)
        return report

    findings = _readback_into_report(report, owner, repository, project_number)
    if findings is None:
        report["verdict"] = "FAIL"
        report["reason"] = "Post-remediation read-back failed"
        return report
    if findings:
        report["verdict"] = "FAIL"
        report["reason"] = "Post-remediation G0 audit still has findings: " + ", ".join(
            f.code for f in findings
        )
        return report

    report["verdict"] = "PASS"
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
        return 0 if report.get("verdict") != "FAIL" else 2
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
