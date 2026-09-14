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
QA_FIELD = str(CONFIG["project"]["qa_state_field"])
QA_STATES = list(CONFIG["project"]["states"])

STATE_MAP = {
    "READY": {
        QA_FIELD: "Готов к QA",
        "Статус": "Проверка QA",
        "Исполнение": "В очереди",
        "Проверяющий": "AGY",
        "Доказательство": "Автопроверки пройдены",
    },
    "IN_REVIEW": {
        QA_FIELD: "На проверке QA",
        "Статус": "Проверка QA",
        "Исполнение": "На проверке",
        "Проверяющий": "AGY",
        "Доказательство": "Автопроверки пройдены",
    },
    "PASS": {
        QA_FIELD: "QA пройден",
        "Статус": "Проверка QA",
        "Исполнение": "В очереди",
        "Проверяющий": "AGY",
        "Доказательство": "Проверка качества пройдена",
    },
    "BLOCKED": {
        QA_FIELD: "QA заблокирован",
        "Статус": "Заблокировано",
        "Исполнение": "Заблокировано",
        "Проверяющий": "AGY",
        "Доказательство": "Частично",
    },
    "STALE": {
        QA_FIELD: "QA устарел",
        "Статус": "Проверка QA",
        "Исполнение": "В очереди",
        "Проверяющий": "AGY",
        "Доказательство": "Частично",
    },
}

CREATE_FIELD = """
mutation($input:CreateProjectV2FieldInput!){
  createProjectV2Field(input:$input){
    projectV2Field{... on ProjectV2SingleSelectField{id name options{id name}}}
  }
}
"""
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
  repository(owner:$login,name:$repo){pullRequest(number:$pr){id url}}
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
    proc = subprocess.run(
        ["gh", *args], input=data, text=True, encoding="utf-8",
        capture_output=True, check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"gh failed ({proc.returncode})")
    return json.loads(proc.stdout) if proc.stdout.strip() else None


def gql(query: str, variables: dict[str, Any]) -> Any:
    result = gh_json(["api", "graphql", "--input", "-"], {"query": query, "variables": variables})
    if result.get("errors"):
        raise RuntimeError("GraphQL returned errors")
    return result["data"]


def base_snapshot(pr: int) -> tuple[dict[str, Any], dict[str, Any]]:
    data = gql(BASE_QUERY, {"login": OWNER, "number": PROJECT_NUMBER, "repo": REPOSITORY, "pr": pr})
    project = ((data.get("user") or {}).get("projectV2") or {})
    pull = ((data.get("repository") or {}).get("pullRequest") or {})
    if not project.get("id"):
        raise RuntimeError(f"Project #{PROJECT_NUMBER} not found")
    if (project.get("fields") or {}).get("pageInfo", {}).get("hasNextPage"):
        raise RuntimeError("Project fields exceed 100; refusing partial schema")
    if not pull.get("id") or not pull.get("url"):
        raise RuntimeError(f"PR #{pr} not found")
    return project, pull


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
                raise RuntimeError(f"Ambiguous Project field: {name}")
            result[name] = field
    return result


def ensure_qa_field(project: dict[str, Any]) -> dict[str, Any]:
    fields = select_fields(project)
    existing = fields.get(QA_FIELD)
    if existing:
        actual = [str(o.get("name") or "") for o in existing.get("options") or []]
        if actual != QA_STATES:
            raise RuntimeError(f"{QA_FIELD} options drift: {actual}")
        return existing
    colors = ["GRAY", "BLUE", "PURPLE", "GREEN", "RED", "YELLOW"]
    options = [
        {"name": name, "color": colors[i], "description": f"KAT9I QA state: {name}"}
        for i, name in enumerate(QA_STATES)
    ]
    data = gql(CREATE_FIELD, {"input": {
        "projectId": project["id"],
        "name": QA_FIELD,
        "dataType": "SINGLE_SELECT",
        "singleSelectOptions": options,
    }})
    created = ((data.get("createProjectV2Field") or {}).get("projectV2Field") or {})
    if not created.get("id"):
        raise RuntimeError(f"Failed to create {QA_FIELD}")
    return created


def find_item(project_id: str, url: str) -> str | None:
    after = None
    while True:
        data = gql(ITEMS_QUERY, {"login": OWNER, "number": PROJECT_NUMBER, "after": after})
        page = (((data.get("user") or {}).get("projectV2") or {}).get("items") or {})
        for node in page.get("nodes") or []:
            if str((node.get("content") or {}).get("url") or "") == url:
                return str(node["id"])
        info = page.get("pageInfo") or {}
        if not info.get("hasNextPage"):
            return None
        after = info.get("endCursor")


def option_id(field: dict[str, Any], name: str) -> str:
    matches = [str(o.get("id")) for o in field.get("options") or [] if o.get("name") == name]
    if len(matches) != 1:
        raise RuntimeError(f"Project option missing/ambiguous: {field.get('name')}={name}")
    return matches[0]


def sync(pr: int, state: str) -> dict[str, Any]:
    if state not in STATE_MAP:
        raise RuntimeError(f"Unsupported QA Project state: {state}")
    project, pull = base_snapshot(pr)
    ensure_qa_field(project)
    project, pull = base_snapshot(pr)
    fields = select_fields(project)
    required = {QA_FIELD, "Статус", "Исполнение", "Проверяющий", "Доказательство"}
    missing = sorted(required - set(fields))
    if missing:
        raise RuntimeError(f"Project fields missing: {missing}")
    item_id = find_item(str(project["id"]), str(pull["url"]))
    if not item_id:
        data = gql(ADD_ITEM, {"input": {"projectId": project["id"], "contentId": pull["id"]}})
        item_id = str((((data.get("addProjectV2ItemById") or {}).get("item") or {}).get("id") or ""))
        if not item_id:
            raise RuntimeError("Failed to add PR to Project")
    edits = []
    for field_name, value in STATE_MAP[state].items():
        field = fields[field_name]
        gql(UPDATE_ITEM, {
            "project": project["id"],
            "item": item_id,
            "field": field["id"],
            "option": option_id(field, value),
        })
        edits.append({"field": field_name, "value": value})
    return {
        "schema": "KAT9I_QA_PROJECT_SYNC/1",
        "target_pr": pr,
        "state": state,
        "qa_state": STATE_MAP[state][QA_FIELD],
        "authority": "DERIVED_PROJECT_PROJECTION",
        "edits": edits,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pr", type=int, required=True)
    parser.add_argument("--state", choices=tuple(STATE_MAP), required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(sync(args.pr, args.state), ensure_ascii=False, separators=(",", ":")))
        return 0
    except Exception as exc:
        print(json.dumps({"schema": "KAT9I_QA_PROJECT_SYNC/1", "verdict": "ERROR", "error": str(exc)[:800]}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
