#!/usr/bin/env python3
"""Детерминированный DATA-only listener независимого QA Worker KAT9I_OS."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.qa_evidence_epoch import EvidenceEpochError, build_snapshot, parse_epoch_section
from scripts.qa_result_bridge import (
    COMMAND_FIELDS,
    COMMAND_MARKER,
    FOLLOW_UP_HEADER,
    RESULT_FIELDS,
    RESULT_MARKER,
    REVIEW_STATES,
    BridgeError,
    _section_lines,
    parse_envelope,
    validate_command as validate_command_envelope,
    validate_result as validate_result_envelope,
)

CONFIG_PATH = ROOT / "config" / "qa_worker.json"
COMMAND_HEADER = COMMAND_MARKER
RESULT_HEADER = RESULT_MARKER


def load_config() -> dict[str, Any]:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def parse_time(value: str | None) -> dt.datetime:
    if not value:
        raise ValueError("Отсутствует timestamp")
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed


def state_path() -> Path:
    override = os.environ.get("KAT9I_QA_STATE_PATH")
    if override:
        return Path(override).expanduser()
    if os.environ.get("LOCALAPPDATA"):
        return Path(os.environ["LOCALAPPDATA"]) / "KAT9I_OS" / "qa_worker_state.json"
    base = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state"))
    return base / "KAT9I_OS" / "qa_worker_state.json"


def empty_state() -> dict[str, Any]:
    return {
        "schema": 1,
        "bootstrapped": False,
        "cursor": None,
        "candidates": {},
        "history": [],
        "last_table_digest": "",
        "priority_source": "COMMAND_FIFO",
    }


def load_state() -> dict[str, Any]:
    path = state_path()
    if not path.is_file():
        return empty_state()
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return empty_state()
    if value.get("schema") != 1 or not isinstance(value.get("candidates"), dict):
        return empty_state()
    value.setdefault("history", [])
    value.setdefault("last_table_digest", "")
    value.setdefault("priority_source", "COMMAND_FIFO")
    return value


def save_state(state: dict[str, Any]) -> None:
    path = state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    tmp.replace(path)


def auth_token() -> str:
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if token:
        return token.strip()
    try:
        proc = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, check=True, timeout=10)
        if proc.stdout.strip():
            return proc.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    raise RuntimeError("Недоступна авторизация GitHub: задайте GH_TOKEN/GITHUB_TOKEN или авторизуйте gh")


class GitHub:
    def __init__(self, repo: str, token: str):
        self.base = f"https://api.github.com/repos/{repo}"
        self.headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "KAT9I-QA-WORKER/1",
        }

    def _request_url(self, method: str, url: str, payload: dict[str, Any] | None = None) -> Any:
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        req = Request(url, data=data, headers=self.headers, method=method)
        try:
            with urlopen(req, timeout=25) as response:
                raw = response.read()
                return json.loads(raw.decode("utf-8")) if raw else None
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:800]
            raise RuntimeError(f"GitHub API {exc.code}: {detail}") from exc

    def request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
        return self._request_url(method, self.base + path, payload)

    def get(self, path: str) -> Any:
        return self.request("GET", path)

    def patch(self, path: str, payload: dict[str, Any]) -> Any:
        return self.request("PATCH", path, payload)

    def graphql(self, query: str, variables: dict[str, Any]) -> Any:
        result = self._request_url("POST", "https://api.github.com/graphql", {"query": query, "variables": variables})
        if not isinstance(result, dict) or result.get("errors"):
            raise RuntimeError("GitHub GraphQL вернул ошибку")
        return result.get("data") or {}

    def paged(self, path: str, limit_pages: int = 20) -> list[Any]:
        sep = "&" if "?" in path else "?"
        out: list[Any] = []
        for page in range(1, limit_pages + 1):
            batch = self.get(f"{path}{sep}per_page=100&page={page}")
            if not isinstance(batch, list):
                raise RuntimeError(f"GitHub API должен вернуть список: {path}")
            out.extend(batch)
            if len(batch) < 100:
                break
        return out


def protocol_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def first_line(body: str) -> str:
    return body.replace("\r\n", "\n").split("\n", 1)[0].strip()


def is_trusted_owner_comment(comment: dict[str, Any], config: dict[str, Any]) -> bool:
    if comment.get("author_association") != "OWNER":
        return False
    login = ((comment.get("user") or {}).get("login") or "").lower()
    return login in {x.lower() for x in config["trusted_controller_logins"]}


def validate_command(comment: dict[str, Any], pr_number: int, config: dict[str, Any]) -> dict[str, Any] | None:
    if not is_trusted_owner_comment(comment, config):
        return None
    body = str(comment.get("body") or "")
    try:
        command = validate_command_envelope(parse_envelope(body, COMMAND_MARKER, COMMAND_FIELDS))
        epoch = parse_epoch_section(body)
    except (BridgeError, EvidenceEpochError):
        return None
    if command["target_pr"] != pr_number:
        return None
    if command["snapshot_head"] if "snapshot_head" in command else False:
        return None
    if epoch["snapshot_head"] != command["exact_head"]:
        return None
    return {**command, "epoch": epoch}


def latest_authoritative_command_from_comments(
    comments: list[dict[str, Any]], pr_number: int, config: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    candidates = [
        c for c in comments
        if is_trusted_owner_comment(c, config) and first_line(c.get("body") or "") == COMMAND_MARKER
    ]
    if not candidates:
        return None
    candidates.sort(key=lambda c: (str(c.get("created_at") or ""), int(c.get("id") or 0)))
    latest = candidates[-1]
    fields = validate_command(latest, pr_number, config)
    if fields is None:
        return None
    command_id = fields["command_id"]
    duplicates = 0
    for candidate in candidates:
        parsed = validate_command(candidate, pr_number, config)
        if parsed and parsed["command_id"] == command_id:
            duplicates += 1
    if duplicates != 1:
        return None
    return latest, fields


def latest_authoritative_command(
    gh: GitHub, pr_number: int, config: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    return latest_authoritative_command_from_comments(gh.paged(f"/issues/{pr_number}/comments"), pr_number, config)


def review_threads_payload(gh: GitHub, pr_number: int) -> dict[str, Any]:
    owner, repo = gh.base.rsplit("/repos/", 1)[-1].split("/", 1)
    query = """
query($owner:String!,$repo:String!,$number:Int!){
  repository(owner:$owner,name:$repo){pullRequest(number:$number){
    reviewThreads(first:100){
      nodes{id isResolved comments(first:100){nodes{id body path line startLine outdated} pageInfo{hasNextPage endCursor}}}
      pageInfo{hasNextPage endCursor}
    }
  }}
}
"""
    payload = gh.graphql(query, {"owner": owner, "repo": repo, "number": pr_number})
    threads = (((payload.get("repository") or {}).get("pullRequest") or {}).get("reviewThreads") or {})
    if (threads.get("pageInfo") or {}).get("hasNextPage"):
        raise RuntimeError("Неполный inventory review threads")
    for thread in threads.get("nodes") or []:
        if ((thread.get("comments") or {}).get("pageInfo") or {}).get("hasNextPage"):
            raise RuntimeError("Неполный inventory review comments")
    return {"data": payload}


def live_evidence_snapshot(gh: GitHub, pr_number: int, head: str) -> dict[str, str]:
    reviews = gh.paged(f"/pulls/{pr_number}/reviews")
    checks = gh.get(f"/commits/{head}/check-runs?per_page=100")
    statuses = gh.get(f"/commits/{head}/status?per_page=100")
    threads = review_threads_payload(gh, pr_number)
    if int((checks or {}).get("total_count") or 0) > len((checks or {}).get("check_runs") or []):
        raise RuntimeError("Неполный inventory check-runs")
    status_rows = (statuses or {}).get("statuses") or []
    if int((statuses or {}).get("total_count") or len(status_rows)) > len(status_rows):
        raise RuntimeError("Неполный inventory commit statuses")
    return build_snapshot(head, threads, reviews, checks, statuses, ROOT)


def command_epoch_is_current(
    gh: GitHub,
    pr_number: int,
    command: dict[str, Any],
) -> tuple[bool, str]:
    try:
        current = live_evidence_snapshot(gh, pr_number, command["exact_head"])
    except (RuntimeError, EvidenceEpochError, ValueError) as exc:
        return False, f"EVIDENCE_UNAVAILABLE: {exc}"
    expected = command["epoch"]
    for key in ("snapshot_head", "review_digest", "gate_digest", "policy_digest", "evidence_digest"):
        if expected.get(key) != current.get(key):
            return False, f"EVIDENCE_DRIFT:{key}"
    return True, "FRESH"


def result_for_command(
    gh: GitHub,
    pr_number: int,
    command_comment: dict[str, Any],
    command: dict[str, Any],
    config: dict[str, Any],
) -> dict[str, Any] | None:
    matches: list[tuple[dt.datetime, int, dict[str, Any], dict[str, Any]]] = []
    command_time = parse_time(command_comment.get("created_at"))
    trusted = {x.lower() for x in config["trusted_controller_logins"]}
    for review in gh.paged(f"/pulls/{pr_number}/reviews"):
        body = str(review.get("body") or "")
        if first_line(body) != RESULT_MARKER:
            continue
        if review.get("author_association") != "OWNER":
            continue
        login = ((review.get("user") or {}).get("login") or "").lower()
        if login not in trusted:
            continue
        try:
            result = validate_result_envelope(parse_envelope(body, RESULT_MARKER, RESULT_FIELDS))
            result_epoch = parse_epoch_section(body)
            submitted = parse_time(review.get("submitted_at"))
        except (BridgeError, EvidenceEpochError, ValueError):
            continue
        if submitted <= command_time:
            continue
        if str(review.get("state") or "").upper() not in REVIEW_STATES:
            continue
        if str(review.get("commit_id") or "").lower() != command["exact_head"]:
            continue
        if result["target_pr"] != pr_number or result["command_id"] != command["command_id"]:
            continue
        for field in ("controller", "role", "exact_head", "qa_mode", "result_sink"):
            if result[field] != command[field]:
                break
        else:
            if result["executor_canonical"] != command["executor_canonical"]:
                continue
            if result_epoch != command["epoch"]:
                continue
            follow_up = _section_lines(body, FOLLOW_UP_HEADER)
            if follow_up is None:
                continue
            if result["follow_up_candidates"] > 0 and not follow_up:
                continue
            matches.append((submitted, int(review.get("id") or 0), review, result))
    if not matches:
        return None
    matches.sort(key=lambda item: (item[0], item[1]))
    return {"review": matches[-1][2], "fields": matches[-1][3]}


def status_from_result(result: dict[str, Any]) -> str:
    verdict = str((result.get("fields") or {}).get("verdict") or "")
    return {
        "QA PASS": "PASS",
        "CHANGES REQUESTED": "NONPASS",
        "BLOCKED": "BLOCKED",
        "QA ABORTED": "ABORTED",
    }.get(verdict, "ABORTED")


def project_priority_map(gh: GitHub, config: dict[str, Any]) -> tuple[dict[int, str], str]:
    policy = config["queue_policy"]
    field_name = str(policy["priority_field"])
    project = config["project"]
    query = """
query($login:String!,$number:Int!,$after:String){
  user(login:$login){projectV2(number:$number){items(first:100,after:$after){
    nodes{
      content{... on PullRequest{number repository{nameWithOwner}}}
      fieldValues(first:50){nodes{
        ... on ProjectV2ItemFieldSingleSelectValue{name field{... on ProjectV2SingleSelectField{name}}}
      }}
    }
    pageInfo{hasNextPage endCursor}
  }}}
}
"""
    result: dict[int, str] = {}
    after: str | None = None
    try:
        while True:
            data = gh.graphql(query, {"login": project["owner"], "number": int(project["number"]), "after": after})
            page = (((data.get("user") or {}).get("projectV2") or {}).get("items") or {})
            for node in page.get("nodes") or []:
                content = node.get("content") or {}
                number = content.get("number")
                repo = ((content.get("repository") or {}).get("nameWithOwner") or "")
                if not number or repo.lower() != str(config["repository"]).lower():
                    continue
                values = [
                    str(value["name"])
                    for value in ((node.get("fieldValues") or {}).get("nodes") or [])
                    if ((value.get("field") or {}).get("name") or "") == field_name and value.get("name")
                ]
                if len(values) > 1:
                    raise RuntimeError(f"Неоднозначный приоритет Project для PR #{number}")
                if values:
                    result[int(number)] = values[0]
            info = page.get("pageInfo") or {}
            if not info.get("hasNextPage"):
                break
            after = info.get("endCursor")
        return result, "PROJECT_V2"
    except Exception:
        return {}, "COMMAND_FIFO"


def priority_rank(priority: str | None, config: dict[str, Any]) -> int:
    order = list(config["queue_policy"]["priority_order"])
    try:
        return order.index(priority)
    except ValueError:
        return len(order)


def candidate_key(pr_number: int, command_id: str, exact_head: str) -> str:
    return f"{pr_number}:{command_id}:{exact_head}"


def candidate_sort_key(candidate: dict[str, Any], config: dict[str, Any]) -> tuple[Any, ...]:
    return (
        priority_rank(candidate.get("priority"), config),
        str(candidate.get("command_created_at") or "9999-12-31T23:59:59Z"),
        int(candidate.get("command_comment_id") or 0),
        int(candidate["target_pr"]),
    )


def add_history(state: dict[str, Any], record: dict[str, Any], config: dict[str, Any]) -> None:
    record = dict(record)
    record["updated_at"] = utc_now()
    key = candidate_key(int(record["target_pr"]), str(record["command_id"]), str(record["exact_head"]))
    history = [x for x in state.get("history", []) if x.get("key") != key]
    record["key"] = key
    history.insert(0, record)
    state["history"] = history[: int(config["recent_qa_output"]["history_limit"])]


def candidate_for_pr(
    gh: GitHub,
    pr: dict[str, Any],
    config: dict[str, Any],
    profile: str,
    priorities: dict[int, str],
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    pr_number = int(pr["number"])
    if pr.get("state") != "open":
        return None, None
    latest = latest_authoritative_command(gh, pr_number, config)
    if latest is None:
        return None, None
    comment, command = latest
    live_head = (((pr.get("head") or {}).get("sha")) or "").lower()
    base = {
        "target_pr": pr_number,
        "command_id": command["command_id"],
        "exact_head": command["exact_head"],
        "qa_mode": command["qa_mode"],
        "priority": priorities.get(pr_number),
        "command_created_at": comment.get("created_at"),
        "command_comment_id": int(comment.get("id") or 0),
        "authoritative_comment_url": comment.get("html_url"),
        "worker_profile": profile,
        "updated_at": utc_now(),
    }
    if live_head != command["exact_head"]:
        return None, dict(base, status="STALE", review_id=None, reason="HEAD_DRIFT")
    result = result_for_command(gh, pr_number, comment, command, config)
    if result:
        return None, dict(
            base,
            status=status_from_result(result),
            review_id=(result.get("review") or {}).get("id"),
            reason="VALID_QA_RESULT",
        )
    return dict(
        base,
        status="READY",
        review_id=None,
        review_mode=config["profiles"][profile]["review_mode"],
        epoch=command["epoch"],
    ), None


def bootstrap(gh: GitHub, config: dict[str, Any], profile: str, state: dict[str, Any]) -> None:
    scan_cursor = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(seconds=5)).isoformat().replace("+00:00", "Z")
    limit = int(config.get("bootstrap_open_pr_limit", 1000))
    pages = max(1, math.ceil(limit / 100))
    pulls = gh.paged("/pulls?state=open&sort=created&direction=asc", limit_pages=pages)[:limit]
    priorities, source = project_priority_map(gh, config)
    new_candidates: dict[str, Any] = {}
    for pr in pulls:
        candidate, terminal = candidate_for_pr(gh, pr, config, profile, priorities)
        if terminal:
            add_history(state, terminal, config)
        if candidate:
            key = candidate_key(candidate["target_pr"], candidate["command_id"], candidate["exact_head"])
            candidate["status"] = "READY"
            new_candidates[key] = candidate
    state["candidates"] = new_candidates
    state["bootstrapped"] = True
    state["cursor"] = scan_cursor
    state["priority_source"] = source
    save_state(state)


def refresh_priorities(gh: GitHub, config: dict[str, Any], state: dict[str, Any]) -> None:
    priorities, source = project_priority_map(gh, config)
    state["priority_source"] = source
    for candidate in (state.get("candidates") or {}).values():
        candidate["priority"] = priorities.get(int(candidate["target_pr"])) if source == "PROJECT_V2" else None
    save_state(state)


def refresh_candidate(
    gh: GitHub, config: dict[str, Any], profile: str, state: dict[str, Any], key: str
) -> dict[str, Any] | None:
    current = (state.get("candidates") or {}).get(key)
    if not current:
        return None
    pr_number = int(current["target_pr"])
    pr = gh.get(f"/pulls/{pr_number}")
    priorities = {pr_number: current.get("priority")} if current.get("priority") else {}
    candidate, terminal = candidate_for_pr(gh, pr, config, profile, priorities)
    state["candidates"].pop(key, None)
    if terminal:
        add_history(state, terminal, config)
        save_state(state)
        return None
    if candidate:
        new_key = candidate_key(candidate["target_pr"], candidate["command_id"], candidate["exact_head"])
        candidate["status"] = current.get("status", "READY") if new_key == key else "READY"
        state["candidates"][new_key] = candidate
        save_state(state)
        return candidate
    save_state(state)
    return None


def sorted_candidates(state: dict[str, Any], config: dict[str, Any]) -> list[dict[str, Any]]:
    return sorted((state.get("candidates") or {}).values(), key=lambda item: candidate_sort_key(item, config))


def recent_rows(state: dict[str, Any], config: dict[str, Any], limit: int) -> list[dict[str, Any]]:
    rows = list((state.get("candidates") or {}).values()) + list(state.get("history") or [])
    rows.sort(key=lambda item: str(item.get("updated_at") or ""), reverse=True)
    return rows[:limit]


def table_text(state: dict[str, Any], config: dict[str, Any], limit: int | None = None) -> str:
    output = config["recent_qa_output"]
    limit = int(limit or output["default_limit"])
    limit = max(1, min(limit, int(output["max_limit"])))
    labels = output["status_labels"]
    rows = recent_rows(state, config, limit)
    lines = [
        "Последние QA:",
        "| PR | Приоритет | Режим | HEAD | Статус | Ревью |",
        "|---:|:---:|:---:|:---:|---|:---:|",
    ]
    if rows:
        for item in rows:
            review = f"#{item['review_id']}" if item.get("review_id") else "—"
            lines.append(
                f"| #{item['target_pr']} | {item.get('priority') or '—'} | {item.get('qa_mode') or '—'} | "
                f"{str(item.get('exact_head') or '')[:7]} | {labels.get(item.get('status'), item.get('status') or '—')} | {review} |"
            )
    else:
        lines.append("| — | — | — | — | Нет заданий | — |")
    pending = sum(1 for item in (state.get("candidates") or {}).values() if item.get("status") in {"READY", "RUNNING"})
    lines.append(output["footer_template"].format(pending=pending))
    return "\n".join(lines)


def render_table(state: dict[str, Any], config: dict[str, Any], *, force: bool = False, stream: Any = sys.stderr) -> None:
    text = table_text(state, config)
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    if not force and config["recent_qa_output"].get("print_only_on_change") and state.get("last_table_digest") == digest:
        return
    print(text, file=stream)
    state["last_table_digest"] = digest
    save_state(state)


def packet_for_candidate(candidate: dict[str, Any], config: dict[str, Any], pending: int) -> dict[str, Any]:
    profile = candidate["worker_profile"]
    return {
        "schema": 4,
        "event": "KAT9I-QA-WAKE/1",
        "authority": "DATA_ONLY",
        "target_pr": candidate["target_pr"],
        "command_id": candidate["command_id"],
        "exact_head": candidate["exact_head"],
        "qa_mode": candidate["qa_mode"],
        "priority": candidate.get("priority"),
        "queue_policy": config["queue_policy"]["mode"],
        "queue_position": 1,
        "queue_pending": pending,
        "worker_profile": profile,
        "review_mode": config["profiles"][profile]["review_mode"],
        "reuse_same_context": bool(config["review_policy"]["reuse_same_context"]),
        "authoritative_comment_id": candidate["command_comment_id"],
        "authoritative_comment_url": candidate["authoritative_comment_url"],
        "protocol_entry": config["protocol_entry"],
        "control_protocol": config["control_protocol"],
        "budget": config["token_budget"],
        "rule": "Получать только целевое Evidence; историю Issue целиком не перечитывать",
    }


def claim_next(gh: GitHub, config: dict[str, Any], profile: str, state: dict[str, Any]) -> dict[str, Any] | None:
    refresh_priorities(gh, config, state)
    running = [x for x in sorted_candidates(state, config) if x.get("status") == "RUNNING"]
    if running:
        key = candidate_key(running[0]["target_pr"], running[0]["command_id"], running[0]["exact_head"])
        refresh_candidate(gh, config, profile, state, key)
        running = [x for x in sorted_candidates(state, config) if x.get("status") == "RUNNING"]
        if running:
            return None
    ready = [x for x in sorted_candidates(state, config) if x.get("status") == "READY"]
    while ready:
        chosen = ready[0]
        key = candidate_key(chosen["target_pr"], chosen["command_id"], chosen["exact_head"])
        refreshed = refresh_candidate(gh, config, profile, state, key)
        if refreshed is None:
            ready = [x for x in sorted_candidates(state, config) if x.get("status") == "READY"]
            continue
        pr_number = int(refreshed["target_pr"])
        pr = gh.get(f"/pulls/{pr_number}")
        latest = latest_authoritative_command(gh, pr_number, config)
        if latest is None:
            state["candidates"].pop(key, None)
            save_state(state)
            ready = [x for x in sorted_candidates(state, config) if x.get("status") == "READY"]
            continue
        comment, command = latest
        if command["command_id"] != refreshed["command_id"] or command["exact_head"] != refreshed["exact_head"]:
            state["candidates"].pop(key, None)
            save_state(state)
            ready = [x for x in sorted_candidates(state, config) if x.get("status") == "READY"]
            continue
        if str(((pr.get("head") or {}).get("sha") or "")).lower() != command["exact_head"]:
            state["candidates"].pop(key, None)
            add_history(state, dict(refreshed, status="STALE", reason="HEAD_DRIFT"), config)
            save_state(state)
            render_table(state, config)
            ready = [x for x in sorted_candidates(state, config) if x.get("status") == "READY"]
            continue
        fresh, reason = command_epoch_is_current(gh, pr_number, command)
        if not fresh:
            state["candidates"].pop(key, None)
            add_history(state, dict(refreshed, status="STALE", reason=reason), config)
            save_state(state)
            render_table(state, config)
            ready = [x for x in sorted_candidates(state, config) if x.get("status") == "READY"]
            continue
        result = result_for_command(gh, pr_number, comment, command, config)
        if result:
            state["candidates"].pop(key, None)
            add_history(state, dict(
                refreshed,
                status=status_from_result(result),
                review_id=(result.get("review") or {}).get("id"),
                reason="VALID_QA_RESULT",
            ), config)
            save_state(state)
            render_table(state, config)
            ready = [x for x in sorted_candidates(state, config) if x.get("status") == "READY"]
            continue
        key = candidate_key(refreshed["target_pr"], refreshed["command_id"], refreshed["exact_head"])
        state["candidates"][key]["status"] = "RUNNING"
        state["candidates"][key]["updated_at"] = utc_now()
        save_state(state)
        render_table(state, config)
        pending = sum(1 for x in state["candidates"].values() if x.get("status") in {"READY", "RUNNING"})
        return packet_for_candidate(state["candidates"][key], config, pending)
    return None


def comment_events(gh: GitHub, since: str, config: dict[str, Any]) -> list[int]:
    query = urlencode({"sort": "created", "direction": "asc", "since": since})
    comments = gh.paged(f"/issues/comments?{query}")
    events: list[int] = []
    for comment in comments:
        if not is_trusted_owner_comment(comment, config):
            continue
        line = first_line(comment.get("body") or "")
        if line != COMMAND_MARKER and not line.startswith("FAST-QA-PASS") and not line.startswith("FAST-BLOCKED"):
            continue
        try:
            pr_number = int((comment.get("issue_url") or "").rstrip("/").split("/")[-1])
        except ValueError:
            continue
        if pr_number not in events:
            events.append(pr_number)
    return events


def ingest_pr_event(gh: GitHub, config: dict[str, Any], profile: str, state: dict[str, Any], pr_number: int) -> None:
    pr = gh.get(f"/pulls/{pr_number}")
    priorities, source = project_priority_map(gh, config)
    state["priority_source"] = source
    candidate, terminal = candidate_for_pr(gh, pr, config, profile, priorities)
    for key, old in list(state["candidates"].items()):
        if int(old.get("target_pr") or -1) == pr_number:
            state["candidates"].pop(key, None)
    if terminal:
        add_history(state, terminal, config)
    if candidate:
        key = candidate_key(candidate["target_pr"], candidate["command_id"], candidate["exact_head"])
        state["candidates"][key] = candidate
    save_state(state)
    render_table(state, config)


def update_presence(gh: GitHub, config: dict[str, Any], state_name: str, profile: str) -> None:
    entry = ROOT / config["protocol_entry"]
    control = ROOT / config["control_protocol"]
    budget = config["token_budget"]
    body = "\n".join([
        "KAT9I-QA-WORKER/1 | PRESENCE",
        "worker=AGY",
        "role=QA_EXECUTOR",
        f"state={state_name}",
        "mode=AUTO_LISTEN" if state_name == "CONNECTED" else "mode=OFFLINE",
        f"profile={profile}",
        f"review_mode={config['profiles'][profile]['review_mode']}",
        "protocol_ack=ACK" if state_name == "CONNECTED" else "protocol_ack=NONE",
        f"protocol_sha256={protocol_hash(entry)}",
        f"control_protocol_sha256={protocol_hash(control)}",
        f"poll_seconds={config['poll_seconds']}",
        f"queue_policy={config['queue_policy']['mode']}",
        f"soft_input_tokens={budget['soft_input_tokens']}",
        f"max_input_tokens={budget['max_input_tokens']}",
        f"hard_total_model_tokens={budget['hard_total_model_tokens']}",
        "idle_poll_llm_tokens=0",
        "authority=PRESENCE_ONLY",
        "",
        "Слот обновляется на месте. Это не inbox и не источник полномочий QA/FAST/merge/Project.",
    ])
    gh.patch(f"/issues/comments/{int(config['presence_comment_id'])}", {"body": body})


def wait_for_task(gh: GitHub, config: dict[str, Any], profile: str, state: dict[str, Any], once: bool = False) -> int:
    if not state.get("bootstrapped"):
        bootstrap(gh, config, profile, state)
    packet = claim_next(gh, config, profile, state)
    if packet:
        print(json.dumps(packet, ensure_ascii=False, separators=(",", ":")))
        return 0
    if once:
        render_table(state, config)
        return 10
    poll = max(10, int(config.get("poll_seconds", 10)))
    cursor = state.get("cursor") or (dt.datetime.now(dt.timezone.utc) - dt.timedelta(seconds=5)).isoformat().replace("+00:00", "Z")
    while True:
        time.sleep(poll)
        next_cursor = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(seconds=2)).isoformat().replace("+00:00", "Z")
        for pr_number in comment_events(gh, cursor, config):
            ingest_pr_event(gh, config, profile, state, pr_number)
        state["cursor"] = next_cursor
        save_state(state)
        packet = claim_next(gh, config, profile, state)
        if packet:
            print(json.dumps(packet, ensure_ascii=False, separators=(",", ":")))
            return 0
        cursor = next_cursor


def main() -> int:
    config = load_config()
    parser = argparse.ArgumentParser(description="Автономный listener QA Worker KAT9I_OS")
    parser.add_argument("command", choices=("connect", "wait", "once", "status", "disconnect"))
    parser.add_argument("--profile", choices=tuple(config["profiles"]), default=config["default_profile"])
    parser.add_argument("--limit", type=int, default=int(config["recent_qa_output"]["default_limit"]))
    args = parser.parse_args()

    for path_key in ("protocol_entry", "control_protocol"):
        path = ROOT / config[path_key]
        if not path.is_file():
            raise RuntimeError(f"Не найден обязательный файл протокола: {path}")

    state = load_state()
    if args.command == "status":
        print(table_text(state, config, args.limit))
        return 0

    gh = GitHub(config["repository"], auth_token())
    if args.command == "connect":
        update_presence(gh, config, "CONNECTED", args.profile)
        bootstrap(gh, config, args.profile, state)
        render_table(state, config, force=True)
        print(json.dumps({
            "event": "KAT9I-QA-CONNECTED/1",
            "mode": "AUTO_LISTEN",
            "profile": args.profile,
            "review_mode": config["profiles"][args.profile]["review_mode"],
            "queue_policy": config["queue_policy"]["mode"],
            "priority_source": state.get("priority_source"),
            "poll_seconds": config["poll_seconds"],
            "idle_poll_llm_tokens": 0,
        }, ensure_ascii=False, separators=(",", ":")))
        return 0
    if args.command == "disconnect":
        update_presence(gh, config, "DISCONNECTED", args.profile)
        return 0
    return wait_for_task(gh, config, args.profile, state, once=args.command == "once")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
    except Exception as exc:
        print(json.dumps({"event": "KAT9I-QA-LISTENER-ERROR/1", "ошибка": str(exc)[:1000]}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(2)
