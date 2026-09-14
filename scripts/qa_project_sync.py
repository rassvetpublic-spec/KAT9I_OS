#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / "config" / "qa_worker.json").read_text(encoding="utf-8"))
REPO = CONFIG["repository"]
OWNER, REPOSITORY = REPO.split("/", 1)
PROJECT_NUMBER = int(CONFIG["project"]["number"])
MANAGED_FIELDS = set(CONFIG["project"]["managed_fields"])

STATE_MAP = {
    "READY": {
        "логическая_фаза": "Готов к QA",
        "Статус": "Проверка QA",
        "Исполнение": "В очереди",
        "Проверяющий": "AGY",
        "Доказательство": "Автопроверки пройдены",
    },
    "IN_REVIEW": {
        "логическая_фаза": "На проверке QA",
        "Статус": "Проверка QA",
        "Исполнение": "На проверке",
        "Проверяющий": "AGY",
        "Доказательство": "Автопроверки пройдены",
    },
    "PASS": {
        "логическая_фаза": "QA пройден",
        "Статус": "Проверка QA",
        "Исполнение": "В очереди",
        "Проверяющий": "AGY",
        "Доказательство": "Проверка качества пройдена",
    },
    "BLOCKED": {
        "логическая_фаза": "QA заблокирован",
        "Статус": "Заблокировано",
        "Исполнение": "Заблокировано",
        "Проверяющий": "AGY",
        "Доказательство": "Частично",
    },
    "STALE": {
        "логическая_фаза": "QA устарел",
        "Статус": "Проверка QA",
        "Исполнение": "В очереди",
        "Проверяющий": "AGY",
        "Доказательство": "Частично",
    },
}

ADD_ITEM = """
mutation($input:AddProjectV2ItemByIdInput!){
  addProjectV2ItemById(input:$input){item{id}}
}
"""
UPDATE_ITEM = """
mutation($project:ID!,$item:ID!,$field:ID!,$option:String!){
  updateProjectV2ItemFieldValue(input:{
    projectId:$project,itemId:$item,fieldId:$field,
    value:{singleSelectOptionId:$option}
  }){projectV2Item{id}}
}
"""
BASE_QUERY = """
query($login:String!,$number:Int!,$repo:String!,$pr:Int!){
  user(login:$login){
    projectV2(number:$number){
      id
      fields(first:100){nodes{
        __typename
        ... on ProjectV2SingleSelectField{id name options{id name}}
      } pageInfo{hasNextPage}}
    }
  }
  repository(owner:$login,name:$repo){
    pullRequest(number:$pr){
      id url
      closingIssuesReferences(first:50){nodes{id url number} pageInfo{hasNextPage}}
    }
  }
}
"""
ITEMS_QUERY = """
query($login:String!,$number:Int!,$after:String){
  user(login:$login){projectV2(number:$number){items(first:100,after:$after){
    nodes{id content{... on PullRequest{id url number} ... on Issue{id url number}}}
    pageInfo{hasNextPage endCursor}
  }}}
}
"""


def gh_json(args: list[str], payload: dict[str, Any] | None = None) -> Any:
    data = None if payload is None else json.dumps(payload, ensure_ascii=False)
    proc = subprocess.run(["gh", *args], input=data, text=True, encoding="utf-8", capture_output=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"Команда GitHub завершилась с кодом {proc.returncode}")
    return json.loads(proc.stdout) if proc.stdout.strip() else None


def gql(query: str, variables: dict[str, Any]) -> Any:
    result = gh_json(["api", "graphql", "--input", "-"], {"query": query, "variables": variables})
    if result.get("errors"):
        raise RuntimeError("GitHub GraphQL вернул ошибку")
    return result["data"]


def base_snapshot(pr: int) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    data = gql(BASE_QUERY, {"login": OWNER, "number": PROJECT_NUMBER, "repo": REPOSITORY, "pr": pr})
    project = ((data.get("user") or {}).get("projectV2") or {})
    pull = ((data.get("repository") or {}).get("pullRequest") or {})
    if not project.get("id"):
        raise RuntimeError(f"Project #{PROJECT_NUMBER} не найден")
    if (project.get("fields") or {}).get("pageInfo", {}).get("hasNextPage"):
        raise RuntimeError("В Project больше 100 полей; частичная схема запрещена")
    if not pull.get("id") or not pull.get("url"):
        raise RuntimeError(f"PR #{pr} не найден")
    closing = pull.get("closingIssuesReferences") or {}
    if (closing.get("pageInfo") or {}).get("hasNextPage"):
        raise RuntimeError("PR закрывает больше 50 задач; частичная синхронизация запрещена")
    targets = [{"тип": "PR", "id": pull["id"], "url": pull["url"], "номер": pr}]
    for issue in closing.get("nodes") or []:
        if issue.get("id") and issue.get("url"):
            targets.append({"тип": "ISSUE", "id": issue["id"], "url": issue["url"], "номер": issue.get("number")})
    return project, targets


def select_fields(project: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for field in (project.get("fields") or {}).get("nodes") or []:
        if field.get("__typename") != "ProjectV2SingleSelectField":
            continue
        name = str(field.get("name") or "")
        if name in {"Status", "Статус"}:
            name = "Статус"
        if name:
            if name in result:
                raise RuntimeError(f"Неоднозначное поле Project: {name}")
            result[name] = field
    return result


def item_index() -> dict[str, str]:
    result: dict[str, str] = {}
    after = None
    while True:
        data = gql(ITEMS_QUERY, {"login": OWNER, "number": PROJECT_NUMBER, "after": after})
        page = (((data.get("user") or {}).get("projectV2") or {}).get("items") or {})
        for node in page.get("nodes") or []:
            url = str((node.get("content") or {}).get("url") or "")
            if not url:
                continue
            if url in result:
                raise RuntimeError(f"Дублирующая карточка Project: {url}")
            result[url] = str(node["id"])
        info = page.get("pageInfo") or {}
        if not info.get("hasNextPage"):
            return result
        after = info.get("endCursor")


def option_id(field: dict[str, Any], name: str) -> str:
    matches = [str(o.get("id")) for o in field.get("options") or [] if o.get("name") == name]
    if len(matches) != 1:
        raise RuntimeError(f"Нет однозначного значения Project: {field.get('name')}={name}")
    return matches[0]


def ensure_item(project_id: str, target: dict[str, Any], index: dict[str, str]) -> str:
    url = str(target["url"])
    if url in index:
        return index[url]
    data = gql(ADD_ITEM, {"input": {"projectId": project_id, "contentId": target["id"]}})
    item_id = str((((data.get("addProjectV2ItemById") or {}).get("item") or {}).get("id") or ""))
    if not item_id:
        raise RuntimeError(f"Не удалось добавить карточку Project: {url}")
    index[url] = item_id
    return item_id


def sync(pr: int, state: str) -> dict[str, Any]:
    if state not in STATE_MAP:
        raise RuntimeError(f"Неподдерживаемое состояние QA: {state}")
    project, targets = base_snapshot(pr)
    fields = select_fields(project)
    missing = sorted(MANAGED_FIELDS - set(fields))
    if missing:
        raise RuntimeError(f"В Project отсутствуют обязательные поля: {', '.join(missing)}")
    projection = STATE_MAP[state]
    index = item_index()
    changed_targets = []
    for target in targets:
        item_id = ensure_item(str(project["id"]), target, index)
        edits = []
        for field_name in sorted(MANAGED_FIELDS):
            value = projection[field_name]
            field = fields[field_name]
            gql(UPDATE_ITEM, {
                "project": project["id"], "item": item_id,
                "field": field["id"], "option": option_id(field, value),
            })
            edits.append({"поле": field_name, "значение": value})
        changed_targets.append({"тип": target["тип"], "номер": target.get("номер"), "изменения": edits})
    return {
        "schema": "KAT9I_QA_PROJECT_SYNC/1",
        "pr": pr,
        "состояние": state,
        "фаза_QA": projection["логическая_фаза"],
        "authority": "DERIVED_PROJECT_PROJECTION",
        "карточки": changed_targets,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Синхронизация QA-состояния с Project KAT9I_OS")
    parser.add_argument("--pr", type=int, required=True)
    parser.add_argument("--state", choices=tuple(STATE_MAP), required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(sync(args.pr, args.state), ensure_ascii=False, separators=(",", ":")))
        return 0
    except Exception as exc:
        print(json.dumps({"schema": "KAT9I_QA_PROJECT_SYNC/1", "вердикт": "ОШИБКА", "ошибка": str(exc)[:800]}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
