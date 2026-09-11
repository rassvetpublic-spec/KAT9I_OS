#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "config" / "project_views.json"
STAGING_PREFIX = "__KAT9I_VIEWS_APPLY__ "

HISTORICAL_LEGACY_VIEWS = {
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

VISIBLE_FIELD_ALIASES = (
    ("Title",),
    ("Assignees",),
    ("Статус", "Status"),
    ("Этап",),
    ("Приоритет",),
    ("Область",),
    ("Тип",),
    ("Размер",),
    ("Итерация",),
    ("Исполнитель",),
    ("Проверяющий",),
    ("Исполнение",),
    ("Цель",),
    ("Риск",),
    ("Доказательство",),
    ("Linked pull requests",),
    ("Sub-issues progress",),
)

PROJECT_QUERY = """
query($login:String!,$number:Int!){
  user(login:$login){
    projectV2(number:$number){
      id title
      fields(first:100){
        nodes{
          __typename
          ... on ProjectV2Field{id name}
          ... on ProjectV2SingleSelectField{id name}
          ... on ProjectV2IterationField{id name}
        }
        pageInfo{hasNextPage}
      }
      views(first:100){nodes{id name layout filter} pageInfo{hasNextPage}}
    }
  }
}
"""

CREATE_VIEW_MUTATION = """
mutation($input:CreateProjectV2ViewInput!){
  createProjectV2View(input:$input){projectV2View{id}}
}
"""

UPDATE_VIEW_MUTATION = """
mutation($input:UpdateProjectV2ViewInput!){
  updateProjectV2View(input:$input){projectV2View{id}}
}
"""

DELETE_VIEW_MUTATION = """
mutation($input:DeleteProjectV2ViewInput!){
  deleteProjectV2View(input:$input){projectV2View{id}}
}
"""


def load_policy() -> dict[str, Any]:
    return json.loads(POLICY_PATH.read_text(encoding="utf-8"))


def layout_capabilities(policy: dict[str, Any]) -> dict[str, dict[str, bool]]:
    raw = policy.get("layout_capabilities")
    if not isinstance(raw, dict) or not raw:
        raise RuntimeError("project_views.json не содержит layout_capabilities")
    result: dict[str, dict[str, bool]] = {}
    for layout, capabilities in raw.items():
        if not isinstance(layout, str) or not layout:
            raise RuntimeError("layout_capabilities содержит пустое имя layout")
        if not isinstance(capabilities, dict):
            raise RuntimeError(f"layout_capabilities.{layout} должен быть объектом")
        visible_fields = capabilities.get("visible_fields")
        filter_capability = capabilities.get("filter")
        if not isinstance(visible_fields, bool) or not isinstance(filter_capability, bool):
            raise RuntimeError(f"layout_capabilities.{layout} должен явно задавать boolean visible_fields и filter")
        result[layout] = {"visible_fields": visible_fields, "filter": filter_capability}
    used_layouts = {str(view.get("layout")) for view in policy.get("views", [])}
    missing = sorted(layout for layout in used_layouts if layout not in result)
    if missing:
        raise RuntimeError("Для layout отсутствует capability contract: " + ", ".join(missing))
    return result


def run_graphql(query: str, variables: dict[str, Any]) -> dict[str, Any]:
    payload = json.dumps({"query": query, "variables": variables}, ensure_ascii=False)
    proc = subprocess.run(["gh", "api", "graphql", "--input", "-"], input=payload, text=True, encoding="utf-8", capture_output=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError("GitHub GraphQL API завершился с ошибкой")
    try:
        result = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("GitHub GraphQL API вернул не-JSON ответ") from exc
    errors = result.get("errors") or []
    if errors:
        messages = "; ".join(str(error.get("message") or error) for error in errors)
        raise RuntimeError(messages)
    return result


def collect_project(owner: str, project_number: int) -> dict[str, Any]:
    result = run_graphql(PROJECT_QUERY, {"login": owner, "number": project_number})
    project = ((result.get("data") or {}).get("user") or {}).get("projectV2")
    if not project:
        raise RuntimeError(f"Project #{project_number} не найден")
    for section in ("fields", "views"):
        if (project.get(section) or {}).get("pageInfo", {}).get("hasNextPage"):
            raise RuntimeError(f"Project {section} содержит больше 100 элементов; частичный снимок запрещён")
    return project


def status_name(project: dict[str, Any]) -> str:
    matches = [field for field in (project.get("fields") or {}).get("nodes", []) if field.get("name") in {"Статус", "Status"}]
    if len(matches) != 1:
        raise RuntimeError(f"Ожидалось ровно одно поле Status/Статус, найдено {len(matches)}")
    return str(matches[0]["name"])


def canonical_views(policy: dict[str, Any], actual_status_name: str) -> list[dict[str, str]]:
    layout_capabilities(policy)
    return [{"name": str(view["name"]), "layout": str(view["layout"]), "filter": str(view["filter"]).replace("{status}", actual_status_name)} for view in policy["views"]]


def staged_name(canonical_name: str) -> str:
    return f"{STAGING_PREFIX}{canonical_name}"


def legacy_names(policy: dict[str, Any]) -> set[str]:
    return {str(name) for name in policy.get("legacy_views", [])} | HISTORICAL_LEGACY_VIEWS


def visible_field_ids(project: dict[str, Any]) -> list[str]:
    fields = list((project.get("fields") or {}).get("nodes", []))
    ids: list[str] = []
    for aliases in VISIBLE_FIELD_ALIASES:
        match = next((field for field in fields if field.get("name") in aliases and field.get("id")), None)
        if match and str(match["id"]) not in ids:
            ids.append(str(match["id"]))
    return ids


def _view_map(views: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    mapped: dict[str, list[dict[str, Any]]] = {}
    for view in views:
        mapped.setdefault(str(view.get("name")), []).append(view)
    return mapped


def preflight(actual_views: list[dict[str, Any]], expected_views: list[dict[str, str]], allowed_legacy: set[str]) -> list[dict[str, Any]]:
    expected_by_name = {view["name"]: view for view in expected_views}
    staged_by_name = {staged_name(name): expected for name, expected in expected_by_name.items()}
    known_names = set(expected_by_name) | set(staged_by_name) | allowed_legacy
    unexpected = sorted({str(view.get("name")) for view in actual_views if str(view.get("name")) not in known_names})
    if unexpected:
        raise RuntimeError("Project содержит неизвестные или регистрово отличающиеся представления: " + ", ".join(unexpected))
    mapped = _view_map(actual_views)
    duplicates = sorted(name for name, matches in mapped.items() if len(matches) > 1)
    if duplicates:
        raise RuntimeError("Project содержит дубли представлений: " + ", ".join(duplicates))
    pending: list[dict[str, Any]] = []
    for name, expected in expected_by_name.items():
        canonical_matches = mapped.get(name, [])
        staged_matches = mapped.get(staged_name(name), [])
        if canonical_matches and staged_matches:
            raise RuntimeError(f"Одновременно существуют canonical и staging представления для '{name}'")
        if canonical_matches:
            actual = canonical_matches[0]
            if actual.get("layout") != expected["layout"] or str(actual.get("filter") or "") != expected["filter"]:
                raise RuntimeError(f"Представление '{name}' нарушает контракт layout/filter; автоматическое исправление остановлено")
            continue
        if staged_matches:
            actual = staged_matches[0]
            actual_filter = str(actual.get("filter") or "")
            if actual.get("layout") != expected["layout"] or actual_filter not in {"", expected["filter"]}:
                raise RuntimeError(f"Staging-представление для '{name}' нарушает recoverable контракт; автоматическое исправление остановлено")
            work = dict(expected)
            work["_staged_id"] = str(actual.get("id") or "")
            if not work["_staged_id"]:
                raise RuntimeError(f"Staging-представление для '{name}' не содержит id")
            pending.append(work)
            continue
        pending.append(dict(expected))
    return pending


def _capability_for(view: dict[str, str], capabilities: dict[str, dict[str, bool]]) -> dict[str, bool]:
    layout = view["layout"]
    capability = capabilities.get(layout)
    if capability is None:
        raise RuntimeError(f"Для layout {layout} отсутствует capability contract")
    return capability


def build_create_input(project_id: str, view: dict[str, str], field_ids: list[str], capabilities: dict[str, dict[str, bool]], *, name: str | None = None) -> dict[str, Any]:
    capability = _capability_for(view, capabilities)
    result: dict[str, Any] = {"projectId": project_id, "name": name or view["name"], "layout": view["layout"]}
    if capability["visible_fields"]:
        result["configuration"] = {"visibleFieldIds": field_ids}
    return result


def build_update_input(view_id: str, view: dict[str, str], field_ids: list[str], capabilities: dict[str, dict[str, bool]], *, finalize_name: str | None = None) -> dict[str, Any]:
    capability = _capability_for(view, capabilities)
    result: dict[str, Any] = {"viewId": view_id}
    if capability["filter"]:
        result["filter"] = view["filter"]
    if finalize_name:
        result["name"] = finalize_name
    if capability["visible_fields"]:
        result["configuration"] = {"visibleFieldIds": field_ids}
    return result


def assert_canonical_complete(actual_views: list[dict[str, Any]], expected_views: list[dict[str, str]]) -> None:
    mapped = _view_map(actual_views)
    for expected in expected_views:
        matches = mapped.get(expected["name"], [])
        if len(matches) != 1:
            raise RuntimeError(f"После создания представление '{expected['name']}' существует неоднозначно: экземпляров {len(matches)}")
        actual = matches[0]
        if actual.get("layout") != expected["layout"] or str(actual.get("filter") or "") != expected["filter"]:
            raise RuntimeError(f"После создания представление '{expected['name']}' не соответствует контракту")
    staging = sorted(str(view.get("name")) for view in actual_views if str(view.get("name")).startswith(STAGING_PREFIX))
    if staging:
        raise RuntimeError("После создания остались staging-представления: " + ", ".join(staging))


def wait_for_complete(owner: str, project_number: int, expected_views: list[dict[str, str]]) -> dict[str, Any]:
    last_error: Exception | None = None
    for attempt in range(10):
        project = collect_project(owner, project_number)
        try:
            assert_canonical_complete(list(project["views"]["nodes"]), expected_views)
            return project
        except RuntimeError as exc:
            last_error = exc
            if attempt < 9:
                time.sleep(2)
    raise RuntimeError(str(last_error or "GitHub не подтвердил полный набор Views"))


def reconcile(owner: str, project_number: int) -> None:
    policy = load_policy()
    capabilities = layout_capabilities(policy)
    project = collect_project(owner, project_number)
    expected = canonical_views(policy, status_name(project))
    allowed_legacy = legacy_names(policy)
    pending = preflight(list(project["views"]["nodes"]), expected, allowed_legacy)
    fields = visible_field_ids(project)
    for view in pending:
        view_id = str(view.get("_staged_id") or "")
        if not view_id:
            created = run_graphql(CREATE_VIEW_MUTATION, {"input": build_create_input(str(project["id"]), view, fields, capabilities, name=staged_name(view["name"]))})
            view_id = str(((((created.get("data") or {}).get("createProjectV2View") or {}).get("projectV2View") or {}).get("id")) or "")
            if not view_id:
                raise RuntimeError(f"GitHub не вернул id созданного staging-представления '{view['name']}'")
        update_input = build_update_input(view_id, view, fields, capabilities, finalize_name=view["name"])
        if len(update_input) > 1:
            run_graphql(UPDATE_VIEW_MUTATION, {"input": update_input})
        print(f"Создано или восстановлено представление: {view['name']}")
    project = wait_for_complete(owner, project_number, expected)
    for view in list(project["views"]["nodes"]):
        if str(view.get("name")) in allowed_legacy:
            run_graphql(DELETE_VIEW_MUTATION, {"input": {"viewId": str(view["id"])}})
            print(f"Удалено устаревшее представление: {view['name']}")
    final_project = collect_project(owner, project_number)
    final_views = list(final_project["views"]["nodes"])
    assert_canonical_complete(final_views, expected)
    if len(final_views) != len(expected):
        expected_names = {entry["name"] for entry in expected}
        extras = sorted(str(view.get("name")) for view in final_views if str(view.get("name")) not in expected_names)
        raise RuntimeError(f"После очистки Project содержит {len(final_views)} Views вместо {len(expected)}; лишние: {', '.join(extras)}")
    print("PASS: Project содержит ровно 8 канонических Views; layout capabilities применены из SSOT, staging recovery завершён.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Безопасная идемпотентная миграция восьми Views GitHub Project")
    parser.add_argument("--owner", default="rassvetpublic-spec")
    parser.add_argument("--project-number", type=int, default=2)
    args = parser.parse_args()
    reconcile(args.owner, args.project_number)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
