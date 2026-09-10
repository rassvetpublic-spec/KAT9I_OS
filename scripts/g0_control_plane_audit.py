#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

EXPECTED_PROJECT_TITLE = "KAT9I_OS — разработка"
EXPECTED_VIEWS = {
    "00 — Все задачи": ("TABLE_LAYOUT", "is:open"),
    "01 — Готово к работе": ("TABLE_LAYOUT", None),
    "02 — В работе": ("BOARD_LAYOUT", None),
    "03 — Проверка": ("BOARD_LAYOUT", None),
    "04 — Заблокировано": ("TABLE_LAYOUT", None),
}
EXPECTED_SELECTS = {
    "Статус": ["Входящие", "Нужно разобрать", "Готово к работе", "В работе", "Проверка QA", "Заблокировано", "Готово"],
    "Этап": ["G0 — Порядок проекта и задач", "G1 — ТЗ и базовая архитектура", "G2 — Машинные контракты", "G3 — Основа исполняемой системы", "G4 — Сквозная версия v0.1", "G5 — После v0.1"],
    "Приоритет": ["P0", "P1", "P2", "P3"],
    "Тип": ["ТЗ / архитектура", "Документация", "Исследование", "Инфраструктура", "Контракты", "Исполняемая система", "Безопасность", "Проверка качества / оценка"],
    "Область": ["Архитектура и документация", "Контекст и знания", "Исполнение и исполнители", "Безопасность и управление", "Интерфейс и визуализация", "Инженерная инфраструктура", "Общее / не определено"],
    "Размер": ["XS — совсем маленькая", "S — маленькая", "M — средняя", "L — большая", "XL — очень большая"],
    "Исполнитель": ["ChatGPT", "AGY", "Codex", "Человек", "Другой"],
    "Проверяющий": ["ChatGPT", "AGY", "Codex", "Человек", "Другой"],
    "Исполнение": ["Свободно", "В очереди", "Активно", "На проверке", "Заблокировано", "Освобождено"],
    "Цель": ["Базовая архитектура", "v0.1", "v0.2", "v1.0", "Позже"],
    "Риск": ["Критический", "Высокий", "Средний", "Низкий"],
    "Доказательство": ["Нет", "Частично", "Автопроверки пройдены", "Проверка качества пройдена"],
}
EXPECTED_MILESTONES = {"Architecture Baseline", "v0.1 — Deterministic Vertical", "v0.2", "v1.0"}
RULESET_ID = 22520270
QUALITY_CONTEXT = "Базовые проверки качества и целостности"
PRIORITY_RE = re.compile(r"\[(P[01])\]", re.IGNORECASE)

@dataclass
class Finding:
    code: str
    message: str


def run_json(cmd: list[str], *, input_text: str | None = None) -> Any:
    proc = subprocess.run(cmd, input=input_text, text=True, encoding="utf-8", capture_output=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"command failed ({proc.returncode}): {' '.join(cmd)}: {proc.stderr.strip()}")
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"invalid JSON from {' '.join(cmd)}") from exc


def gh_graphql(query: str, variables: dict[str, Any]) -> Any:
    args = ["gh", "api", "graphql", "-f", f"query={query}"]
    for key, value in variables.items():
        if value is None:
            continue
        args.extend(["-F", f"{key}={value}"])
    return run_json(args)


def collect_project(owner: str, repository: str, number: int) -> dict[str, Any]:
    base_query = """
query($login:String!,$number:Int!,$repo:String!){
  user(login:$login){
    projectV2(number:$number){
      id title url
      repositories(first:100){nodes{nameWithOwner} pageInfo{hasNextPage}}
      fields(first:100){nodes{
        __typename
        ... on ProjectV2Field{id name dataType}
        ... on ProjectV2SingleSelectField{id name dataType options{id name}}
        ... on ProjectV2IterationField{id name dataType configuration{duration startDay}}
      } pageInfo{hasNextPage}}
      views(first:100){nodes{id name layout filter} pageInfo{hasNextPage}}
    }
  }
  repository(owner:$login,name:$repo){nameWithOwner}
}
"""
    data = gh_graphql(base_query, {"login": owner, "number": number, "repo": repository})["data"]
    project = data.get("user", {}).get("projectV2")
    if not project:
        raise RuntimeError(f"Project #{number} not found")
    for section in ("repositories", "fields", "views"):
        if project[section]["pageInfo"]["hasNextPage"]:
            raise RuntimeError(f"Project {section} exceeds 100 entries; audit refuses partial snapshot")

    item_query = """
query($login:String!,$number:Int!,$after:String){
  user(login:$login){projectV2(number:$number){items(first:100,after:$after){
    nodes{
      id
      content{__typename ... on Issue{url number title state} ... on PullRequest{url number title state}}
      fieldValues(first:100){nodes{
        __typename
        ... on ProjectV2ItemFieldSingleSelectValue{name field{... on ProjectV2SingleSelectField{name}}}
        ... on ProjectV2ItemFieldIterationValue{title field{... on ProjectV2IterationField{name}}}
      } pageInfo{hasNextPage}}
    }
    pageInfo{hasNextPage endCursor}
  }}}
}
"""
    items: list[dict[str, Any]] = []
    after = None
    while True:
        page = gh_graphql(item_query, {"login": owner, "number": number, "after": after})["data"]["user"]["projectV2"]["items"]
        for node in page["nodes"]:
            if node["fieldValues"]["pageInfo"]["hasNextPage"]:
                raise RuntimeError(f"Project item {node['id']} has >100 field values; refusing partial audit")
            items.append(node)
        if not page["pageInfo"]["hasNextPage"]:
            break
        after = page["pageInfo"]["endCursor"]
    project["items"] = items
    project["repository"] = data["repository"]["nameWithOwner"]
    return project


def collect_live(owner: str, repository: str, project_number: int) -> dict[str, Any]:
    repo = f"{owner}/{repository}"
    project = collect_project(owner, repository, project_number)
    ruleset = run_json(["gh", "api", f"repos/{repo}/rulesets/{RULESET_ID}"])
    milestones = run_json(["gh", "api", f"repos/{repo}/milestones?state=all&per_page=100"])
    issues = run_json(["gh", "issue", "list", "--repo", repo, "--state", "open", "--limit", "1000", "--json", "number,title,url,state"])
    prs = run_json(["gh", "pr", "list", "--repo", repo, "--state", "open", "--limit", "1000", "--json", "number,title,url,state"])
    if len(issues) >= 1000 or len(prs) >= 1000:
        raise RuntimeError("Open work reached 1000-item CLI cap; audit refuses potentially partial inventory")
    if len(milestones) >= 100:
        raise RuntimeError("Milestones reached 100-item API cap; audit refuses potentially partial inventory")
    return {"project": project, "ruleset": ruleset, "milestones": milestones, "open_work": issues + prs}


def field_name(node: dict[str, Any]) -> str | None:
    field = node.get("field") or {}
    return field.get("name")


def item_fields(item: dict[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    for node in item.get("fieldValues", {}).get("nodes", []):
        name = field_name(node)
        if not name:
            continue
        if node.get("__typename") == "ProjectV2ItemFieldSingleSelectValue" and node.get("name") is not None:
            result[name] = str(node["name"])
        elif node.get("__typename") == "ProjectV2ItemFieldIterationValue" and node.get("title") is not None:
            result[name] = str(node["title"])
    return result


def normalize_status_field(fields: list[dict[str, Any]]) -> dict[str, Any] | None:
    exact = [f for f in fields if f.get("name") == "Статус"]
    if exact:
        return exact[0]
    system = [f for f in fields if f.get("name") == "Status"]
    if system:
        return system[0]
    return None


def validate(snapshot: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    p = snapshot.get("project") or {}
    ruleset = snapshot.get("ruleset") or {}
    milestones = snapshot.get("milestones") or []
    open_work = snapshot.get("open_work") or []

    if p.get("title") != EXPECTED_PROJECT_TITLE:
        findings.append(Finding("PROJECT_TITLE", f"Project title is {p.get('title')!r}"))
    expected_repo = p.get("repository")
    linked = {n.get("nameWithOwner") for n in p.get("repositories", {}).get("nodes", [])}
    if expected_repo not in linked:
        findings.append(Finding("PROJECT_LINK", f"Project is not linked to {expected_repo}"))

    fields = p.get("fields", {}).get("nodes", [])
    status_field = normalize_status_field(fields)
    if not status_field:
        findings.append(Finding("FIELD_STATUS", "Missing Status/Статус field"))
    else:
        actual = [o.get("name") for o in status_field.get("options", [])]
        if sorted(actual) != sorted(EXPECTED_SELECTS["Статус"]):
            findings.append(Finding("FIELD_STATUS_OPTIONS", f"Статус options mismatch: {actual}"))

    by_name = {f.get("name"): f for f in fields if f.get("name")}
    for name, expected_options in EXPECTED_SELECTS.items():
        if name == "Статус":
            continue
        f = by_name.get(name)
        if not f:
            findings.append(Finding("FIELD_MISSING", f"Missing field: {name}"))
            continue
        if f.get("__typename") != "ProjectV2SingleSelectField":
            findings.append(Finding("FIELD_TYPE", f"Field {name} is not single-select"))
            continue
        actual = [o.get("name") for o in f.get("options", [])]
        if sorted(actual) != sorted(expected_options):
            findings.append(Finding("FIELD_OPTIONS", f"Field {name} options mismatch: {actual}"))

    iteration = by_name.get("Итерация")
    if not iteration:
        findings.append(Finding("ITERATION_MISSING", "Missing Итерация field"))
    elif iteration.get("__typename") != "ProjectV2IterationField":
        findings.append(Finding("ITERATION_TYPE", "Итерация is not an iteration field"))
    elif int((iteration.get("configuration") or {}).get("duration") or 0) != 3:
        findings.append(Finding("ITERATION_DURATION", f"Итерация duration={(iteration.get('configuration') or {}).get('duration')}"))

    views = p.get("views", {}).get("nodes", [])
    if len(views) != 5:
        findings.append(Finding("VIEW_COUNT", f"Project has {len(views)} views, expected 5"))
    view_by_name = {v.get("name"): v for v in views}
    status_name = status_field.get("name") if status_field else "Status"
    expected_filters = {
        "00 — Все задачи": "is:open",
        "01 — Готово к работе": f'is:open {status_name}:"Готово к работе" -Исполнение:"Заблокировано"',
        "02 — В работе": f'is:open {status_name}:"В работе"',
        "03 — Проверка": f'is:open {status_name}:"Проверка QA"',
        "04 — Заблокировано": f'is:open {status_name}:"Заблокировано"',
    }
    for name, (layout, _) in EXPECTED_VIEWS.items():
        v = view_by_name.get(name)
        if not v:
            findings.append(Finding("VIEW_MISSING", f"Missing view: {name}"))
            continue
        if v.get("layout") != layout:
            findings.append(Finding("VIEW_LAYOUT", f"View {name} layout={v.get('layout')}, expected {layout}"))
        if str(v.get("filter") or "") != expected_filters[name]:
            findings.append(Finding("VIEW_FILTER", f"View {name} filter mismatch"))

    item_by_url: dict[str, dict[str, Any]] = {}
    for item in p.get("items", []):
        content = item.get("content") or {}
        if content.get("url"):
            item_by_url[content["url"]] = item
    repo_name = p.get("repository") or ""
    gate_url = f"https://github.com/{repo_name}/issues/62" if repo_name else ""
    if gate_url not in item_by_url:
        findings.append(Finding("GATE_62", "Issue #62 is not present in Project"))

    for work in open_work:
        title = work.get("title") or ""
        m = PRIORITY_RE.search(title)
        if not m:
            continue
        priority = m.group(1).upper()
        url = work.get("url")
        item = item_by_url.get(url)
        if not item:
            findings.append(Finding("OPEN_P01_MISSING", f"Open {priority} work missing from Project: {url}"))
            continue
        values = item_fields(item)
        if values.get("Приоритет") != priority:
            findings.append(Finding("OPEN_P01_PRIORITY", f"{url} priority={values.get('Приоритет')!r}, expected {priority}"))
        if not values.get("Этап"):
            findings.append(Finding("OPEN_P01_STAGE", f"{url} has no Этап"))

    for item in p.get("items", []):
        values = item_fields(item)
        is_active = values.get("Исполнение") == "Активно" or values.get("Статус") == "В работе" or values.get("Status") == "В работе"
        if not is_active:
            continue
        content = item.get("content") or {}
        ref = content.get("url") or item.get("id")
        if not values.get("Исполнитель"):
            findings.append(Finding("ACTIVE_WORKER", f"Active item {ref} has no Исполнитель"))
        if not values.get("Проверяющий"):
            findings.append(Finding("ACTIVE_QA", f"Active item {ref} has no Проверяющий"))

    titles = {m.get("title") for m in milestones}
    for required in sorted(EXPECTED_MILESTONES):
        if required not in titles:
            findings.append(Finding("MILESTONE", f"Missing milestone: {required}"))

    if ruleset.get("id") != RULESET_ID or ruleset.get("name") != "main-protection" or ruleset.get("enforcement") != "active":
        findings.append(Finding("RULESET_IDENTITY", "main-protection ruleset identity/enforcement mismatch"))
    if ruleset.get("bypass_actors") or ruleset.get("current_user_can_bypass") not in (None, "never"):
        findings.append(Finding("RULESET_BYPASS", "Ruleset has bypass actors or current user can bypass"))
    includes = ((ruleset.get("conditions") or {}).get("ref_name") or {}).get("include") or []
    if "~DEFAULT_BRANCH" not in includes:
        findings.append(Finding("RULESET_TARGET", "Ruleset does not target the default branch"))
    rule_by_type = {r.get("type"): r for r in ruleset.get("rules", [])}
    for required_type in ("deletion", "non_fast_forward", "pull_request", "required_status_checks"):
        if required_type not in rule_by_type:
            findings.append(Finding("RULESET_RULE", f"Missing ruleset rule: {required_type}"))
    pr_rule = rule_by_type.get("pull_request", {}).get("parameters", {})
    if not pr_rule.get("required_review_thread_resolution"):
        findings.append(Finding("RULESET_THREADS", "Review-thread resolution is not required"))
    status = rule_by_type.get("required_status_checks", {}).get("parameters", {})
    if not status.get("strict_required_status_checks_policy"):
        findings.append(Finding("RULESET_STRICT", "Strict required status checks policy is disabled"))
    contexts = {c.get("context") for c in status.get("required_status_checks", [])}
    if QUALITY_CONTEXT not in contexts:
        findings.append(Finding("RULESET_QUALITY", f"Required check {QUALITY_CONTEXT!r} missing"))

    return findings


def summarize(snapshot: dict[str, Any], findings: list[Finding]) -> dict[str, Any]:
    p = snapshot.get("project") or {}
    return {
        "schema": "KAT9I_G0_AUDIT/1",
        "verdict": "PASS" if not findings else "FAIL",
        "finding_count": len(findings),
        "findings": [asdict(f) for f in findings],
        "project": {
            "title": p.get("title"),
            "field_count": len((p.get("fields") or {}).get("nodes", [])),
            "view_count": len((p.get("views") or {}).get("nodes", [])),
            "item_count": len(p.get("items") or []),
        },
        "ruleset_id": (snapshot.get("ruleset") or {}).get("id"),
        "milestones": sorted(m.get("title") for m in snapshot.get("milestones", []) if m.get("title")),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--owner", default="rassvetpublic-spec")
    ap.add_argument("--repository", default="KAT9I_OS")
    ap.add_argument("--project-number", type=int, default=2)
    ap.add_argument("--fixture")
    ap.add_argument("--output")
    ns = ap.parse_args()
    try:
        if ns.fixture:
            snapshot = json.loads(Path(ns.fixture).read_text(encoding="utf-8"))
        else:
            if not os.environ.get("GH_TOKEN"):
                raise RuntimeError("GH_TOKEN is required for live audit")
            snapshot = collect_live(ns.owner, ns.repository, ns.project_number)
        findings = validate(snapshot)
        summary = summarize(snapshot, findings)
    except Exception as exc:
        summary = {
            "schema": "KAT9I_G0_AUDIT/1",
            "verdict": "ERROR",
            "finding_count": 1,
            "findings": [{"code": "AUDIT_ERROR", "message": str(exc)}],
        }
        findings = [Finding("AUDIT_ERROR", str(exc))]
    text = json.dumps(summary, ensure_ascii=False, indent=2)
    print(text)
    if ns.output:
        Path(ns.output).write_text(text + "\n", encoding="utf-8")
    return 0 if not findings else 1


if __name__ == "__main__":
    sys.exit(main())
