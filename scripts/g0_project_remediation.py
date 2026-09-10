#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from g0_control_plane_audit import (
    CONTROLLED_EXECUTION_STATES,
    CONTROLLED_STATUS_STATES,
    EXPECTED_SELECTS,
    EXPECTED_VIEWS,
    PRIORITY_RE,
    collect_live,
    item_fields,
    validate as audit_validate,
)

OWNER = "rassvetpublic-spec"
REPOSITORY = "KAT9I_OS"
PROJECT_NUMBER = 2
PROJECT_URL_PREFIX = f"https://github.com/{OWNER}/{REPOSITORY}"

STAGE_BY_GATE = {
    "G0": "G0 — Порядок проекта и задач",
    "G1": "G1 — ТЗ и базовая архитектура",
    "G2": "G2 — Машинные контракты",
    "G3": "G3 — Основа исполняемой системы",
    "G4": "G4 — Сквозная версия v0.1",
    "G5": "G5 — После v0.1",
}
GATE_RE = re.compile(r"\[(G[0-5])\]", re.IGNORECASE)
TZ_PHASE_RE = re.compile(r"\[T[0-5]\]", re.IGNORECASE)

CANONICAL_WORKERS = ["ChatGPT", "AGY", "Codex", "Человек", "Другой"]
WORKER_COLORS = {
    "ChatGPT": "GREEN",
    "AGY": "BLUE",
    "Codex": "PURPLE",
    "Человек": "ORANGE",
    "Другой": "GRAY",
}
WORKER_DESCRIPTIONS = {
    "ChatGPT": "ChatGPT.",
    "AGY": "Antigravity (AGY), независимый QA Executor.",
    "Codex": "Codex.",
    "Человек": "Человек.",
    "Другой": "Другой исполнитель.",
}
AGY_LEGACY_NAMES = {"Antigravity", "Антигравити", "Agy", "Antigravity (AGY)", "Антигравити (AGY)"}
REMOVABLE_UNUSED_WORKER_OPTIONS = {"Kat9i_OS"}

CANONICAL_VIEWS = set(EXPECTED_VIEWS)
LEGACY_VIEWS = {
    "00 — Центр управления",
    "01 — Архитектура G1",
    "02 — Готово к работе",
    "03 — Активные исполнители",
    "04 — Очередь проверки",
    "05 — Заблокировано",
    "06 — План v0.1",
    "07 — Безопасность",
    "08 — Доказательства",
    "09 — Без классификации",
}


class RemediationError(RuntimeError):
    pass


@dataclass(frozen=True)
class ItemEdit:
    url: str
    item_id: str
    field: str
    field_id: str
    option: str
    option_id: str
    reason: str


@dataclass
class RemediationPlan:
    worker_field_update: dict[str, Any] | None
    delete_views: list[dict[str, str]]
    item_edits: list[ItemEdit]
    missing_open_items: list[str]

    def jsonable(self) -> dict[str, Any]:
        return {
            "worker_field_update": self.worker_field_update,
            "delete_views": self.delete_views,
            "item_edits": [asdict(edit) for edit in self.item_edits],
            "missing_open_items": self.missing_open_items,
        }


def gh_json(args: list[str], *, stdin: str | None = None) -> Any:
    proc = subprocess.run(
        ["gh", *args],
        input=stdin,
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RemediationError(f"GitHub CLI failed ({proc.returncode}): gh {' '.join(args)}")
    text = proc.stdout.strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise RemediationError(f"GitHub CLI returned invalid JSON: gh {' '.join(args)}") from exc


def gql_mutation(query: str, variables: dict[str, Any]) -> Any:
    payload = json.dumps({"query": query, "variables": variables}, ensure_ascii=False)
    result = gh_json(["api", "graphql", "--input", "-"], stdin=payload)
    if not isinstance(result, dict):
        raise RemediationError("GraphQL mutation returned empty/non-object payload")
    if result.get("errors"):
        raise RemediationError("GraphQL mutation returned errors")
    return result


def project_fields(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    return list((((snapshot.get("project") or {}).get("fields") or {}).get("nodes") or []))


def find_select_field(snapshot: dict[str, Any], name: str) -> dict[str, Any]:
    aliases = {name}
    if name == "Статус":
        aliases.add("Status")
    matches = [f for f in project_fields(snapshot) if f.get("name") in aliases]
    if len(matches) != 1:
        raise RemediationError(f"Expected exactly one field {name!r}, found {len(matches)}")
    field = matches[0]
    if field.get("__typename") != "ProjectV2SingleSelectField":
        raise RemediationError(f"Field {name!r} is not single-select")
    return field


def field_option_map(field: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for option in field.get("options") or []:
        name = str(option.get("name") or "")
        if not name or name in result:
            raise RemediationError(f"Field {field.get('name')!r} contains empty/duplicate option name")
        if not option.get("id"):
            raise RemediationError(f"Field {field.get('name')!r} option {name!r} has no id")
        result[name] = option
    return result


def item_by_url(snapshot: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for item in (snapshot.get("project") or {}).get("items") or []:
        url = str((item.get("content") or {}).get("url") or "")
        if not url:
            continue
        if url in result:
            raise RemediationError(f"Duplicate Project item for {url}")
        result[url] = item
    return result


def derive_stage(title: str) -> str | None:
    match = GATE_RE.search(title or "")
    if match:
        return STAGE_BY_GATE[match.group(1).upper()]
    if TZ_PHASE_RE.search(title or ""):
        return STAGE_BY_GATE["G1"]
    return None


def is_controlled(values: dict[str, str]) -> bool:
    status = values.get("Статус") or values.get("Status")
    execution = values.get("Исполнение")
    return execution in CONTROLLED_EXECUTION_STATES or status in CONTROLLED_STATUS_STATES


def worker_option_plan(snapshot: dict[str, Any]) -> dict[str, Any] | None:
    worker_field = find_select_field(snapshot, "Исполнитель")
    options = field_option_map(worker_field)
    option_names = set(options)

    legacy_agy = sorted(option_names & AGY_LEGACY_NAMES)
    if "AGY" in option_names and legacy_agy:
        raise RemediationError("Исполнитель contains both canonical AGY and legacy AGY aliases")
    if len(legacy_agy) > 1:
        raise RemediationError(f"Исполнитель has ambiguous AGY aliases: {legacy_agy}")

    allowed = set(CANONICAL_WORKERS) | AGY_LEGACY_NAMES | REMOVABLE_UNUSED_WORKER_OPTIONS
    unknown = sorted(option_names - allowed)
    if unknown:
        raise RemediationError(f"Исполнитель has unknown options: {unknown}")

    missing_non_agy = [name for name in CANONICAL_WORKERS if name != "AGY" and name not in options]
    if missing_non_agy:
        raise RemediationError(f"Исполнитель is missing canonical options: {missing_non_agy}")
    if "AGY" not in options and not legacy_agy:
        raise RemediationError("Исполнитель is missing AGY and has no known legacy AGY option to rename")

    values_using_removable: dict[str, list[str]] = {name: [] for name in REMOVABLE_UNUSED_WORKER_OPTIONS}
    for item in (snapshot.get("project") or {}).get("items") or []:
        values = item_fields(item)
        worker_value = values.get("Исполнитель")
        if worker_value in values_using_removable:
            ref = str((item.get("content") or {}).get("url") or item.get("id") or "unknown")
            values_using_removable[worker_value].append(ref)
    in_use = {name: refs for name, refs in values_using_removable.items() if refs}
    if in_use:
        raise RemediationError(f"Refusing to remove used legacy worker options: {in_use}")

    if option_names == set(CANONICAL_WORKERS):
        return None

    canonical_inputs: list[dict[str, Any]] = []
    for name in CANONICAL_WORKERS:
        source = options.get(name)
        if name == "AGY" and source is None:
            source = options[legacy_agy[0]]
        assert source is not None
        canonical_inputs.append(
            {
                "id": source["id"],
                "name": name,
                "color": WORKER_COLORS[name],
                "description": WORKER_DESCRIPTIONS[name],
            }
        )
    return {"field_id": worker_field["id"], "options": canonical_inputs}


def view_delete_plan(snapshot: dict[str, Any]) -> list[dict[str, str]]:
    views = list((((snapshot.get("project") or {}).get("views") or {}).get("nodes") or []))
    by_name: dict[str, list[dict[str, Any]]] = {}
    for view in views:
        by_name.setdefault(str(view.get("name") or ""), []).append(view)
    duplicates = sorted(name for name, values in by_name.items() if len(values) != 1)
    if duplicates:
        raise RemediationError(f"Project has duplicate/ambiguous view names: {duplicates}")
    missing = sorted(CANONICAL_VIEWS - set(by_name))
    if missing:
        raise RemediationError(f"Project is missing canonical views: {missing}")
    extra_names = set(by_name) - CANONICAL_VIEWS
    unknown = sorted(extra_names - LEGACY_VIEWS)
    if unknown:
        raise RemediationError(f"Refusing to delete unknown Project views: {unknown}")
    return [
        {"id": str(by_name[name][0]["id"]), "name": name}
        for name in sorted(extra_names)
    ]


def missing_open_items(snapshot: dict[str, Any]) -> list[str]:
    items = item_by_url(snapshot)
    missing: list[str] = []
    for work in snapshot.get("open_work") or []:
        url = str(work.get("url") or "")
        if not url:
            raise RemediationError("Open work contains item without URL")
        if url not in items:
            missing.append(url)
    return sorted(set(missing))


def resolve_binding(snapshot: dict[str, Any], field_name: str, option_name: str) -> tuple[str, str]:
    field = find_select_field(snapshot, field_name)
    options = field_option_map(field)
    option = options.get(option_name)
    if not option:
        raise RemediationError(f"Missing option {field_name}={option_name}")
    return str(field["id"]), str(option["id"])


def build_plan(snapshot: dict[str, Any], closed_outcomes: dict[str, str]) -> RemediationPlan:
    static_worker_update = worker_option_plan(snapshot)
    static_view_delete = view_delete_plan(snapshot)
    missing = missing_open_items(snapshot)
    if missing:
        return RemediationPlan(static_worker_update, static_view_delete, [], missing)

    items = item_by_url(snapshot)
    edits: dict[tuple[str, str], ItemEdit] = {}

    def add_edit(url: str, field: str, option: str, reason: str) -> None:
        item = items.get(url)
        if not item:
            raise RemediationError(f"Project item missing for planned edit: {url}")
        current = item_fields(item).get(field)
        if current == option:
            return
        field_id, option_id = resolve_binding(snapshot, field, option)
        key = (url, field)
        candidate = ItemEdit(url, str(item["id"]), field, field_id, option, option_id, reason)
        previous = edits.get(key)
        if previous and previous.option != option:
            raise RemediationError(f"Conflicting planned values for {url} {field}: {previous.option} vs {option}")
        edits[key] = candidate

    # Все открытые P0/P1 должны иметь priority и stage. При наличии Gx/Tz в title stage выводится детерминированно.
    for work in snapshot.get("open_work") or []:
        title = str(work.get("title") or "")
        match = PRIORITY_RE.search(title)
        if not match:
            continue
        url = str(work.get("url") or "")
        priority = match.group(1).upper()
        values = item_fields(items[url])
        add_edit(url, "Приоритет", priority, "OPEN_P01_CLASSIFICATION")
        expected_stage = derive_stage(title)
        current_stage = values.get("Этап")
        if expected_stage:
            add_edit(url, "Этап", expected_stage, "OPEN_P01_CLASSIFICATION")
        elif not current_stage:
            raise RemediationError(f"Open {priority} item has no derivable/non-empty Этап: {url} title={title!r}")

    # Исторические controlled cards нормализуются по фактическому GitHub state, а не backfill identity.
    for url, item in items.items():
        values = item_fields(item)
        if not is_controlled(values):
            continue
        content = item.get("content") or {}
        state = str(content.get("state") or "").upper()
        title = str(content.get("title") or "")
        if state == "CLOSED":
            outcome = closed_outcomes.get(url)
            if outcome not in {"DONE", "BLOCKED"}:
                raise RemediationError(f"Missing trusted closed outcome for controlled item {url}")
            if outcome == "DONE":
                add_edit(url, "Исполнение", "Освобождено", "CLOSED_ITEM_NORMALIZATION")
                add_edit(url, "Статус", "Готово", "CLOSED_ITEM_NORMALIZATION")
            else:
                add_edit(url, "Исполнение", "Заблокировано", "CLOSED_ITEM_NORMALIZATION")
                add_edit(url, "Статус", "Заблокировано", "CLOSED_ITEM_NORMALIZATION")
            continue
        if state == "OPEN" and title.startswith("[DATA]"):
            add_edit(url, "Исполнение", "Заблокировано", "DATA_ONLY_PARK")
            add_edit(url, "Статус", "Заблокировано", "DATA_ONLY_PARK")
            continue
        worker = values.get("Исполнитель")
        qa = values.get("Проверяющий")
        if not worker or not qa:
            raise RemediationError(f"Open controlled non-DATA item lacks Worker/QA; refusing to guess: {url}")
        if worker.strip().casefold() == qa.strip().casefold():
            raise RemediationError(f"Open controlled item has self-QA: {url}")

    return RemediationPlan(
        worker_field_update=static_worker_update,
        delete_views=static_view_delete,
        item_edits=sorted(edits.values(), key=lambda edit: (edit.url, edit.field)),
        missing_open_items=[],
    )


def collect_closed_outcomes(snapshot: dict[str, Any]) -> dict[str, str]:
    repo = f"{OWNER}/{REPOSITORY}"
    outcomes: dict[str, str] = {}
    for item in (snapshot.get("project") or {}).get("items") or []:
        values = item_fields(item)
        if not is_controlled(values):
            continue
        content = item.get("content") or {}
        if str(content.get("state") or "").upper() != "CLOSED":
            continue
        number = content.get("number")
        url = str(content.get("url") or "")
        kind = content.get("__typename")
        if not number or not url:
            raise RemediationError("Closed controlled Project item lacks number/url")
        if kind == "PullRequest":
            data = gh_json(["api", f"repos/{repo}/pulls/{number}"])
            outcomes[url] = "DONE" if data.get("merged_at") else "BLOCKED"
        elif kind == "Issue":
            data = gh_json(["api", f"repos/{repo}/issues/{number}"])
            outcomes[url] = "DONE" if data.get("state_reason") == "completed" else "BLOCKED"
        else:
            raise RemediationError(f"Unsupported controlled content type for {url}: {kind}")
    return outcomes


def apply_worker_field_update(update: dict[str, Any] | None) -> None:
    if not update:
        return
    query = """
mutation($input:UpdateProjectV2FieldInput!){
  updateProjectV2Field(input:$input){
    projectV2Field{... on ProjectV2SingleSelectField{id name options{id name}}}
  }
}
"""
    gql_mutation(
        query,
        {"input": {"fieldId": update["field_id"], "singleSelectOptions": update["options"]}},
    )


def apply_delete_views(views: list[dict[str, str]]) -> None:
    query = """
mutation($input:DeleteProjectV2ViewInput!){
  deleteProjectV2View(input:$input){projectV2View{id}}
}
"""
    for view in views:
        gql_mutation(query, {"input": {"viewId": view["id"]}})


def apply_item_edits(project_id: str, edits: list[ItemEdit]) -> None:
    # Status/Статус остаётся commit marker: для каждого item остальные поля раньше статуса.
    ordered = sorted(edits, key=lambda e: (e.url, e.field in {"Статус", "Status"}, e.field))
    for edit in ordered:
        proc = subprocess.run(
            [
                "gh", "project", "item-edit",
                "--id", edit.item_id,
                "--project-id", project_id,
                "--field-id", edit.field_id,
                "--single-select-option-id", edit.option_id,
            ],
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=False,
        )
        if proc.returncode != 0:
            raise RemediationError(f"Project item edit failed for {edit.url} {edit.field}={edit.option}")


def add_missing_items(urls: list[str]) -> None:
    for url in urls:
        proc = subprocess.run(
            ["gh", "project", "item-add", str(PROJECT_NUMBER), "--owner", OWNER, "--url", url, "--format", "json"],
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=False,
        )
        if proc.returncode != 0:
            raise RemediationError(f"Failed to add expected open Project item: {url}")


def remediation(owner: str, repository: str, project_number: int, *, apply: bool) -> dict[str, Any]:
    if (owner, repository, project_number) != (OWNER, REPOSITORY, PROJECT_NUMBER):
        raise RemediationError("This bounded remediation is pinned to KAT9I_OS Project #2")

    before = collect_live(owner, repository, project_number)
    # Static safety checks run before any mutation.
    worker_option_plan(before)
    view_delete_plan(before)
    find_select_field(before, "Приоритет")
    find_select_field(before, "Этап")
    find_select_field(before, "Исполнение")
    find_select_field(before, "Статус")

    missing = missing_open_items(before)
    if missing and apply:
        add_missing_items(missing)
        before = collect_live(owner, repository, project_number)
        still_missing = missing_open_items(before)
        if still_missing:
            raise RemediationError(f"Open Project inventory still incomplete after item-add: {still_missing}")

    outcomes = collect_closed_outcomes(before) if apply or not missing else {}
    plan = build_plan(before, outcomes)
    report: dict[str, Any] = {
        "schema": "KAT9I_G0_REMEDIATION/1",
        "mode": "APPLY" if apply else "PLAN",
        "before_audit": [asdict(f) for f in audit_validate(before)],
        "plan": plan.jsonable(),
    }
    if not apply:
        return report
    if plan.missing_open_items:
        raise RemediationError(f"Cannot apply while open Project items are missing: {plan.missing_open_items}")

    project_id = str((before.get("project") or {}).get("id") or "")
    if not project_id:
        raise RemediationError("Project id missing")

    apply_worker_field_update(plan.worker_field_update)
    apply_delete_views(plan.delete_views)
    apply_item_edits(project_id, plan.item_edits)

    after = collect_live(owner, repository, project_number)
    findings = audit_validate(after)
    report["after_audit"] = [asdict(f) for f in findings]
    report["verdict"] = "PASS" if not findings else "FAIL"
    if findings:
        raise RemediationError("Post-remediation G0 audit still has findings: " + ", ".join(f.code for f in findings))
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Bounded fail-closed G0 Project remediation for Issue #134")
    parser.add_argument("--owner", default=OWNER)
    parser.add_argument("--repository", default=REPOSITORY)
    parser.add_argument("--project-number", type=int, default=PROJECT_NUMBER)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    if not os.environ.get("GH_TOKEN"):
        print("KAT9I_G0_REMEDIATION=ERROR | GH_TOKEN is required")
        return 2
    try:
        report = remediation(args.owner, args.repository, args.project_number, apply=args.apply)
        text = json.dumps(report, ensure_ascii=False, indent=2)
        print(text)
        if args.output:
            args.output.write_text(text + "\n", encoding="utf-8")
        verdict = report.get("verdict", "PLAN_READY")
        print(f"KAT9I_G0_REMEDIATION={verdict}")
        return 0
    except RemediationError as exc:
        error = {"schema": "KAT9I_G0_REMEDIATION/1", "verdict": "ERROR", "reason": str(exc)}
        text = json.dumps(error, ensure_ascii=False, indent=2)
        print(text)
        if args.output:
            args.output.write_text(text + "\n", encoding="utf-8")
        print(f"KAT9I_G0_REMEDIATION=ERROR | {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
