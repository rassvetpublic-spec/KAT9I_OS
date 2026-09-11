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

try:
    from scripts.g0_control_plane_audit import collect_live, item_fields
except ModuleNotFoundError:
    from g0_control_plane_audit import collect_live, item_fields

ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "config" / "project_card_classification.json"
OWNER = "rassvetpublic-spec"
REPOSITORY = "KAT9I_OS"
PROJECT_NUMBER = 2
GATE_RE = re.compile(r"\[(G[0-5])\]", re.IGNORECASE)
TZ_RE = re.compile(r"\[T[0-5]\]", re.IGNORECASE)
TAG_RE = re.compile(r"\[([A-Z0-9_-]+)\]", re.IGNORECASE)

UPDATE_ITEM_MUTATION = """
mutation($project:ID!,$item:ID!,$field:ID!,$option:String!){
  updateProjectV2ItemFieldValue(input:{
    projectId:$project,
    itemId:$item,
    fieldId:$field,
    value:{singleSelectOptionId:$option}
  }){projectV2Item{id}}
}
"""


class ClassificationError(RuntimeError):
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


def load_policy() -> dict[str, Any]:
    policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    if policy.get("version") != 1:
        raise ClassificationError("Неподдерживаемая версия project_card_classification.json")
    if not isinstance(policy.get("stage_by_gate"), dict) or not isinstance(policy.get("stage_by_tag"), dict):
        raise ClassificationError("SSOT классификации должен содержать stage_by_gate и stage_by_tag")
    try:
        re.compile(str(policy["priority_pattern"]), re.IGNORECASE)
    except re.error as exc:
        raise ClassificationError("Некорректный priority_pattern в SSOT") from exc
    return policy


def project_fields(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    return list((((snapshot.get("project") or {}).get("fields") or {}).get("nodes") or []))


def find_select_field(snapshot: dict[str, Any], name: str) -> dict[str, Any]:
    matches = [field for field in project_fields(snapshot) if field.get("name") == name]
    if len(matches) != 1:
        raise ClassificationError(f"Ожидалось ровно одно поле {name!r}, найдено {len(matches)}")
    field = matches[0]
    if field.get("__typename") != "ProjectV2SingleSelectField":
        raise ClassificationError(f"Поле {name!r} должно быть single-select")
    return field


def option_map(field: dict[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    for option in field.get("options") or []:
        name = str(option.get("name") or "")
        option_id = str(option.get("id") or "")
        if not name or not option_id or name in result:
            raise ClassificationError(f"Поле {field.get('name')!r} содержит неоднозначные options")
        result[name] = option_id
    return result


def item_by_url(snapshot: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for item in (snapshot.get("project") or {}).get("items") or []:
        url = str((item.get("content") or {}).get("url") or "")
        if not url:
            continue
        if url in result:
            raise ClassificationError(f"Дублирующая карточка Project: {url}")
        result[url] = item
    return result


def derive_priority(title: str, policy: dict[str, Any]) -> str | None:
    match = re.search(str(policy["priority_pattern"]), title or "", re.IGNORECASE)
    return match.group(1).upper() if match else None


def derive_stage(title: str, policy: dict[str, Any]) -> str | None:
    gate = GATE_RE.search(title or "")
    if gate:
        return str(policy["stage_by_gate"].get(gate.group(1).upper()) or "") or None
    if TZ_RE.search(title or ""):
        return str(policy["stage_by_gate"].get("G1") or "") or None
    by_tag = {str(key).upper(): str(value) for key, value in policy["stage_by_tag"].items()}
    for tag in TAG_RE.findall(title or ""):
        value = by_tag.get(tag.upper())
        if value:
            return value
    return None


def build_plan(snapshot: dict[str, Any], policy: dict[str, Any]) -> list[ItemEdit]:
    priority_field = find_select_field(snapshot, "Приоритет")
    stage_field = find_select_field(snapshot, "Этап")
    priorities = option_map(priority_field)
    stages = option_map(stage_field)
    items = item_by_url(snapshot)
    edits: list[ItemEdit] = []
    for work in snapshot.get("open_work") or []:
        title = str(work.get("title") or "")
        priority = derive_priority(title, policy)
        if priority not in {"P0", "P1"}:
            continue
        url = str(work.get("url") or "")
        item = items.get(url)
        if not item:
            raise ClassificationError(f"Открытая P0/P1 задача отсутствует в Project: {url}")
        values = item_fields(item)
        priority_option_id = priorities.get(priority)
        if not priority_option_id:
            raise ClassificationError(f"В поле Приоритет отсутствует option {priority}")
        if values.get("Приоритет") != priority:
            edits.append(ItemEdit(url, str(item["id"]), "Приоритет", str(priority_field["id"]), priority, priority_option_id, "TITLE_PRIORITY"))
        stage = derive_stage(title, policy)
        current_stage = values.get("Этап")
        if not stage:
            if not current_stage:
                raise ClassificationError(f"Для P0/P1 задачи не определён Этап: {url} title={title!r}")
            continue
        stage_option_id = stages.get(stage)
        if not stage_option_id:
            raise ClassificationError(f"В поле Этап отсутствует option {stage!r}")
        if current_stage != stage:
            edits.append(ItemEdit(url, str(item["id"]), "Этап", str(stage_field["id"]), stage, stage_option_id, "TITLE_STAGE"))
    keys = [(edit.url, edit.field) for edit in edits]
    if len(keys) != len(set(keys)):
        raise ClassificationError("План содержит дублирующиеся изменения карточек")
    return edits


def run_graphql(query: str, variables: dict[str, Any]) -> dict[str, Any]:
    payload = json.dumps({"query": query, "variables": variables}, ensure_ascii=False)
    proc = subprocess.run(["gh", "api", "graphql", "--input", "-"], input=payload, text=True, encoding="utf-8", capture_output=True, check=False)
    if proc.returncode != 0:
        raise ClassificationError("GitHub GraphQL mutation завершилась с ошибкой")
    try:
        result = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise ClassificationError("GitHub GraphQL mutation вернула не-JSON") from exc
    if result.get("errors"):
        raise ClassificationError("GitHub GraphQL mutation вернула errors")
    return result


def apply_plan(project_id: str, edits: list[ItemEdit]) -> None:
    for edit in edits:
        run_graphql(UPDATE_ITEM_MUTATION, {"project": project_id, "item": edit.item_id, "field": edit.field_id, "option": edit.option_id})
        print(f"Обновлено {edit.url}: {edit.field}={edit.option}")


def reconcile(owner: str, repository: str, project_number: int, *, apply: bool) -> dict[str, Any]:
    if (owner, repository, project_number) != (OWNER, REPOSITORY, PROJECT_NUMBER):
        raise ClassificationError("Reconciler закреплён за KAT9I_OS Project #2")
    policy = load_policy()
    before = collect_live(owner, repository, project_number)
    plan = build_plan(before, policy)
    report: dict[str, Any] = {
        "schema": "KAT9I_PROJECT_CARD_CLASSIFICATION/1",
        "mode": "APPLY" if apply else "PLAN",
        "planned_edits": [asdict(edit) for edit in plan],
        "planned_count": len(plan),
    }
    if not apply:
        report["verdict"] = "PASS"
        return report
    project_id = str((before.get("project") or {}).get("id") or "")
    if not project_id:
        raise ClassificationError("Project id отсутствует")
    apply_plan(project_id, plan)
    after = collect_live(owner, repository, project_number)
    remaining = build_plan(after, policy)
    report["remaining_edits"] = [asdict(edit) for edit in remaining]
    report["remaining_count"] = len(remaining)
    report["verdict"] = "PASS" if not remaining else "FAIL"
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Bounded reconciler классификации P0/P1 карточек Project #2")
    parser.add_argument("--owner", default=OWNER)
    parser.add_argument("--repository", default=REPOSITORY)
    parser.add_argument("--project-number", type=int, default=PROJECT_NUMBER)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not os.environ.get("GH_TOKEN"):
        print(json.dumps({"schema": "KAT9I_PROJECT_CARD_CLASSIFICATION/1", "verdict": "ERROR", "reason": "GH_TOKEN is required"}, ensure_ascii=False))
        return 2
    try:
        report = reconcile(args.owner, args.repository, args.project_number, apply=args.apply)
    except ClassificationError as exc:
        report = {"schema": "KAT9I_PROJECT_CARD_CLASSIFICATION/1", "verdict": "ERROR", "reason": str(exc)}
    text = json.dumps(report, ensure_ascii=False, indent=2)
    print(text)
    if args.output:
        args.output.write_text(text + "\n", encoding="utf-8")
    return 0 if report.get("verdict") == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
