#!/usr/bin/env python3
"""Deterministic, DATA-only discovery loop for KAT9I_OS QA workers."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "qa_worker.json"
PROJECT_SYNC = ROOT / "scripts" / "qa_project_sync.py"
COMMAND_HEADER = "KAT9I-CONTROL/1 | QA-COMMAND"
RESULT_HEADER = "KAT9I-QA-RESULT/1"
SHA40 = re.compile(r"^[0-9a-f]{40}$")
FAST_HEAD = re.compile(r"\bhead=([0-9a-f]{40})\b")


def load_config() -> dict[str, Any]:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


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
    raise RuntimeError("GitHub auth unavailable: set GH_TOKEN/GITHUB_TOKEN or authenticate gh")


class GitHub:
    def __init__(self, repo: str, token: str):
        self.base = f"https://api.github.com/repos/{repo}"
        self.headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "KAT9I-QA-WORKER/1",
        }

    def request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        req = Request(self.base + path, data=data, headers=self.headers, method=method)
        try:
            with urlopen(req, timeout=25) as response:
                raw = response.read()
                return json.loads(raw.decode("utf-8")) if raw else None
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:800]
            raise RuntimeError(f"GitHub API {exc.code} {method} {path}: {detail}") from exc

    def get(self, path: str) -> Any:
        return self.request("GET", path)

    def patch(self, path: str, payload: dict[str, Any]) -> Any:
        return self.request("PATCH", path, payload)

    def paged(self, path: str, limit_pages: int = 20) -> list[Any]:
        sep = "&" if "?" in path else "?"
        out: list[Any] = []
        for page in range(1, limit_pages + 1):
            batch = self.get(f"{path}{sep}per_page=100&page={page}")
            if not isinstance(batch, list):
                raise RuntimeError(f"Expected list from {path}")
            out.extend(batch)
            if len(batch) < 100:
                break
        return out


def parse_fields(body: str, header: str) -> dict[str, str] | None:
    lines = body.replace("\r\n", "\n").split("\n")
    if not lines or lines[0].strip() != header:
        return None
    fields: dict[str, str] = {}
    for line in lines[1:]:
        line = line.strip()
        if not line or line == "EVIDENCE_EPOCH" or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key and key not in fields:
            fields[key] = value.strip()
    return fields


def protocol_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def first_line(body: str) -> str:
    return body.replace("\r\n", "\n").split("\n", 1)[0].strip()


def is_trusted_owner_comment(comment: dict[str, Any], config: dict[str, Any]) -> bool:
    if comment.get("author_association") != "OWNER":
        return False
    login = ((comment.get("user") or {}).get("login") or "").lower()
    return login in {x.lower() for x in config["trusted_controller_logins"]}


def validate_command(comment: dict[str, Any], pr_number: int, config: dict[str, Any]) -> dict[str, str] | None:
    if not is_trusted_owner_comment(comment, config):
        return None
    fields = parse_fields(comment.get("body") or "", COMMAND_HEADER)
    if fields is None:
        return None
    required = {
        "command_id", "target_pr", "controller", "executor", "role", "exact_head",
        "qa_mode", "result_sink", "allow_issue_create", "allow_merge", "allow_fast_marker",
        "allow_code_mutation", "project_lifecycle_mutation", "epoch_version",
        "snapshot_head", "review_digest", "gate_digest", "policy_digest", "evidence_digest",
    }
    if not required.issubset(fields):
        return None
    if fields["target_pr"] != str(pr_number):
        return None
    if fields["controller"] != "ChatGPT" or fields["executor"] != "AGY":
        return None
    if fields["role"] != "QA_EXECUTOR" or fields["result_sink"] != "PR_REVIEW":
        return None
    if not SHA40.fullmatch(fields["exact_head"]) or fields["snapshot_head"] != fields["exact_head"]:
        return None
    if fields["qa_mode"] not in {"FULL", "DELTA", "REUSE"}:
        return None
    if fields["allow_issue_create"].lower() not in {"true", "false"}:
        return None
    for key in ("allow_merge", "allow_fast_marker", "allow_code_mutation", "project_lifecycle_mutation"):
        if fields[key].lower() != "false":
            return None
    return fields


def latest_authoritative_command_from_comments(comments: list[dict[str, Any]], pr_number: int, config: dict[str, Any]) -> tuple[dict[str, Any], dict[str, str]] | None:
    candidates = [
        c for c in comments
        if is_trusted_owner_comment(c, config) and first_line(c.get("body") or "") == COMMAND_HEADER
    ]
    if not candidates:
        return None
    candidates.sort(key=lambda c: int(c.get("id") or 0))
    latest = candidates[-1]
    fields = validate_command(latest, pr_number, config)
    if fields is None:
        return None
    return latest, fields


def latest_authoritative_command(gh: GitHub, pr_number: int, config: dict[str, Any]) -> tuple[dict[str, Any], dict[str, str]] | None:
    return latest_authoritative_command_from_comments(gh.paged(f"/issues/{pr_number}/comments"), pr_number, config)


def result_for_command(gh: GitHub, pr_number: int, fields: dict[str, str]) -> dict[str, Any] | None:
    matches = []
    for review in gh.paged(f"/pulls/{pr_number}/reviews"):
        result = parse_fields(review.get("body") or "", RESULT_HEADER)
        if result is None:
            continue
        if result.get("command_id") != fields["command_id"] or result.get("exact_head") != fields["exact_head"]:
            continue
        if (review.get("commit_id") or "").lower() != fields["exact_head"]:
            continue
        matches.append((int(review.get("id") or 0), review, result))
    if not matches:
        return None
    matches.sort(key=lambda x: x[0])
    return {"review": matches[-1][1], "fields": matches[-1][2]}


def sync_project(pr_number: int, state: str) -> dict[str, Any]:
    if not PROJECT_SYNC.is_file():
        return {"verdict": "DEGRADED", "reason": "qa_project_sync.py missing"}
    proc = subprocess.run(
        [sys.executable, str(PROJECT_SYNC), "--pr", str(pr_number), "--state", state],
        cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", check=False,
    )
    if proc.returncode != 0:
        return {"verdict": "DEGRADED", "reason": (proc.stderr or proc.stdout).strip()[:500]}
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {"verdict": "DEGRADED", "reason": "project sync returned non-JSON"}


def derive_project_state(gh: GitHub, pr_number: int, config: dict[str, Any]) -> str | None:
    pr = gh.get(f"/pulls/{pr_number}")
    if pr.get("state") != "open":
        return None
    comments = gh.paged(f"/issues/{pr_number}/comments")
    latest = latest_authoritative_command_from_comments(comments, pr_number, config)
    if latest is None:
        return None
    command_comment, fields = latest
    live_head = (((pr.get("head") or {}).get("sha")) or "").lower()
    if live_head != fields["exact_head"]:
        return "STALE"
    after_command = [
        c for c in comments
        if is_trusted_owner_comment(c, config) and int(c.get("id") or 0) > int(command_comment.get("id") or 0)
    ]
    after_command.sort(key=lambda c: int(c.get("id") or 0))
    for comment in reversed(after_command):
        line = first_line(comment.get("body") or "")
        if line.startswith("FAST-QA-PASS"):
            match = FAST_HEAD.search(line)
            if match and match.group(1) == fields["exact_head"]:
                return "PASS"
        if line.startswith("FAST-BLOCKED"):
            match = FAST_HEAD.search(line)
            if not match or match.group(1) == fields["exact_head"]:
                return "BLOCKED"
    if result_for_command(gh, pr_number, fields):
        return "IN_REVIEW"
    return "READY"


def reconcile_project(gh: GitHub, pr_number: int, config: dict[str, Any]) -> dict[str, Any]:
    state = derive_project_state(gh, pr_number, config)
    if not state:
        return {"verdict": "SKIP", "reason": "no active authoritative QA command"}
    return sync_project(pr_number, state)


def task_for_pr(gh: GitHub, pr_number: int, config: dict[str, Any], profile: str) -> dict[str, Any] | None:
    pr = gh.get(f"/pulls/{pr_number}")
    if pr.get("state") != "open":
        return None
    latest = latest_authoritative_command(gh, pr_number, config)
    if latest is None:
        return None
    comment, fields = latest
    live_head = (((pr.get("head") or {}).get("sha")) or "").lower()
    if live_head != fields["exact_head"]:
        sync_project(pr_number, "STALE")
        return None
    if result_for_command(gh, pr_number, fields):
        reconcile_project(gh, pr_number, config)
        return None
    project_ready = sync_project(pr_number, "READY")
    profile_policy = config["profiles"][profile]
    return {
        "schema": 2,
        "event": "KAT9I-QA-WAKE/1",
        "authority": "DATA_ONLY",
        "target_pr": pr_number,
        "command_id": fields["command_id"],
        "exact_head": fields["exact_head"],
        "qa_mode": fields["qa_mode"],
        "worker_profile": profile,
        "review_mode": profile_policy["review_mode"],
        "reuse_same_context": bool(profile_policy.get("reuse_same_context", True)),
        "authoritative_comment_id": comment.get("id"),
        "authoritative_comment_url": comment.get("html_url"),
        "protocol_entry": config["protocol_entry"],
        "control_protocol": config["control_protocol"],
        "budget": config["token_budget"],
        "project_ready": project_ready,
        "rule": "fetch targeted evidence only; do not reread issue history",
    }


def bootstrap_open_prs(gh: GitHub, config: dict[str, Any], profile: str) -> dict[str, Any] | None:
    limit = int(config.get("bootstrap_open_pr_limit", 100))
    pulls = gh.get(f"/pulls?state=open&sort=updated&direction=desc&per_page={min(limit, 100)}")
    first_packet = None
    for pr in pulls[:limit]:
        pr_number = int(pr["number"])
        reconcile_project(gh, pr_number, config)
        if first_packet is None:
            first_packet = task_for_pr(gh, pr_number, config, profile)
    if first_packet:
        first_packet["project_claim"] = sync_project(int(first_packet["target_pr"]), "IN_REVIEW")
    return first_packet


def comment_events(gh: GitHub, since: str, config: dict[str, Any]) -> list[tuple[int, str]]:
    query = urlencode({"sort": "created", "direction": "asc", "since": since})
    comments = gh.paged(f"/issues/comments?{query}")
    events: list[tuple[int, str]] = []
    for comment in comments:
        if not is_trusted_owner_comment(comment, config):
            continue
        line = first_line(comment.get("body") or "")
        if line != COMMAND_HEADER and not line.startswith("FAST-QA-PASS") and not line.startswith("FAST-BLOCKED"):
            continue
        try:
            pr_number = int((comment.get("issue_url") or "").rstrip("/").split("/")[-1])
        except ValueError:
            continue
        events.append((pr_number, line))
    return events


def update_presence(gh: GitHub, config: dict[str, Any], state: str, profile: str) -> None:
    entry = ROOT / config["protocol_entry"]
    control = ROOT / config["control_protocol"]
    budget = config["token_budget"]
    body = "\n".join([
        "KAT9I-QA-WORKER/1 | PRESENCE",
        "worker=AGY",
        "role=QA_EXECUTOR",
        f"state={state}",
        "mode=AUTO_LISTEN" if state == "CONNECTED" else "mode=OFFLINE",
        f"profile={profile}",
        f"review_mode={config['profiles'][profile]['review_mode']}",
        "protocol_ack=ACK" if state == "CONNECTED" else "protocol_ack=NONE",
        f"protocol_sha256={protocol_hash(entry)}",
        f"control_protocol_sha256={protocol_hash(control)}",
        f"poll_seconds={config['poll_seconds']}",
        f"soft_input_tokens={budget['soft_input_tokens']}",
        f"max_input_tokens={budget['max_input_tokens']}",
        f"hard_total_model_tokens={budget['hard_total_model_tokens']}",
        "idle_poll_llm_tokens=0",
        "authority=PRESENCE_ONLY",
        "",
        "Updated in place. This slot is not an inbox and grants no QA/FAST/merge/Project authority.",
    ])
    gh.patch(f"/issues/comments/{int(config['presence_comment_id'])}", {"body": body})


def wait_for_task(gh: GitHub, config: dict[str, Any], profile: str, once: bool = False) -> int:
    packet = bootstrap_open_prs(gh, config, profile)
    if packet:
        print(json.dumps(packet, ensure_ascii=False, separators=(",", ":")))
        return 0
    if once:
        return 10
    poll = max(10, int(config.get("poll_seconds", 10)))
    cursor = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(seconds=5)).isoformat().replace("+00:00", "Z")
    while True:
        time.sleep(poll)
        next_cursor = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(seconds=2)).isoformat().replace("+00:00", "Z")
        seen: set[int] = set()
        for pr_number, _ in comment_events(gh, cursor, config):
            if pr_number in seen:
                continue
            seen.add(pr_number)
            reconcile_project(gh, pr_number, config)
            packet = task_for_pr(gh, pr_number, config, profile)
            if packet:
                packet["project_claim"] = sync_project(pr_number, "IN_REVIEW")
                print(json.dumps(packet, ensure_ascii=False, separators=(",", ":")))
                return 0
        cursor = next_cursor


def main() -> int:
    config = load_config()
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("connect", "wait", "once", "disconnect"))
    parser.add_argument("--profile", choices=tuple(config["profiles"]), default=config["default_profile"])
    args = parser.parse_args()
    for path_key in ("protocol_entry", "control_protocol"):
        path = ROOT / config[path_key]
        if not path.is_file():
            raise RuntimeError(f"Required protocol file missing: {path}")
    gh = GitHub(config["repository"], auth_token())
    if args.command == "connect":
        update_presence(gh, config, "CONNECTED", args.profile)
        print(json.dumps({
            "event": "KAT9I-QA-CONNECTED/1",
            "mode": "AUTO_LISTEN",
            "profile": args.profile,
            "review_mode": config["profiles"][args.profile]["review_mode"],
            "poll_seconds": config["poll_seconds"],
            "idle_poll_llm_tokens": 0,
        }, separators=(",", ":")))
        return 0
    if args.command == "disconnect":
        update_presence(gh, config, "DISCONNECTED", args.profile)
        return 0
    return wait_for_task(gh, config, args.profile, once=args.command == "once")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
    except Exception as exc:
        print(json.dumps({"event": "KAT9I-QA-LISTENER-ERROR/1", "error": str(exc)[:1000]}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(2)
