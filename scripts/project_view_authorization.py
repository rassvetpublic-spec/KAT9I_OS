"""Проверка команды владельца перед миграцией Project #150."""
import json
import os
import re
from pathlib import Path

REPOSITORY = "rassvetpublic-spec/KAT9I_OS"
OWNER = "rassvetpublic-spec"
MARKER = "KAT9I-CONTROL/1 | PROJECT-VIEWS-APPLY"


def authorize(event_name, event, actor, sha, ref):
    if (event.get("repository") or {}).get("full_name") != REPOSITORY:
        raise ValueError("Неверный репозиторий")
    if actor != OWNER or not re.fullmatch(r"[0-9a-f]{40}", sha or ""):
        raise ValueError("Нужны владелец и точная revision")
    if ref != "refs/heads/main":
        raise ValueError("Разрешён только main")
    if event_name == "workflow_dispatch":
        expected = (event.get("inputs") or {}).get("expected_head")
    elif event_name == "issue_comment":
        comment = event.get("comment") or {}
        if event.get("action") != "created" or (event.get("issue") or {}).get("number") != 150:
            raise ValueError("Нужен новый комментарий в #150")
        if comment.get("author_association") != "OWNER" or (comment.get("user") or {}).get("login") != OWNER:
            raise ValueError("Команда должна принадлежать владельцу")
        lines = comment.get("body", "").splitlines()
        if len(lines) != 2 or lines[0] != MARKER or not lines[1].startswith("expected_head="):
            raise ValueError("Ожидаются ровно marker и expected_head")
        expected = lines[1].removeprefix("expected_head=")
    else:
        raise ValueError("Неподдерживаемое событие")
    if expected != sha:
        raise ValueError("Команда не соответствует exact HEAD main")
    return sha


if __name__ == "__main__":
    authorize(os.environ["GITHUB_EVENT_NAME"], json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text()), os.environ["GITHUB_ACTOR"], os.environ["GITHUB_SHA"], os.environ["GITHUB_REF"])
    print("PASS: команда владельца привязана к exact main")
