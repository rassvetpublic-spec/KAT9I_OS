import argparse
import json
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from qa_result_bridge import (  # noqa: E402
    BridgeError,
    COMMAND_FIELDS,
    COMMAND_MARKER,
    parse_envelope,
    validate_command,
)


CONTROL_MARKERS = {
    "FAST-READY": "READY",
    "FAST-CLAIM": "ACTIVE",
    "FAST-QA": "QA",
    "FAST-QA-PASS": "QUEUED",
    "FAST-BLOCKED": "BLOCKED",
    "FAST-RELEASE": "DONE",
}
IDENTITY_KEYS = {"worker", "qa"}
HEAD_RE = re.compile(r"^[0-9a-f]{40}$")


def _first_line(body: str) -> str:
    lines = (body or "").splitlines()
    return lines[0].strip() if lines else ""


def _control_parts(body: str) -> tuple[str | None, dict[str, str]]:
    first_line = _first_line(body)
    if not first_line:
        return None, {}
    parts = [part.strip() for part in first_line.split("|")]
    state = CONTROL_MARKERS.get(parts[0])
    if not state:
        return None, {}
    meta: dict[str, str] = {}
    for part in parts[1:]:
        if not part:
            continue
        if "=" not in part:
            lowered = part.lower()
            if lowered in IDENTITY_KEYS or lowered.startswith("worker") or lowered.startswith("qa") or lowered.startswith("head"):
                raise ValueError(f"FAST metadata '{part}' должна иметь форму key=value")
            continue
        key, value = part.split("=", 1)
        key = key.strip().lower()
        value = value.strip()
        if key in IDENTITY_KEYS or key == "head":
            if not value:
                raise ValueError(f"FAST metadata '{key}' не может быть пустой")
            if key in meta:
                raise ValueError(f"FAST metadata '{key}' указана более одного раза")
            if key == "head" and not HEAD_RE.fullmatch(value):
                raise ValueError("FAST metadata 'head' должна быть точным 40-символьным lowercase SHA")
            meta[key] = value
        elif key.startswith("worker") or key.startswith("qa") or key.startswith("head"):
            raise ValueError(f"Неподдерживаемый FAST key '{key}'")
    if state == "QUEUED" and "head" not in meta:
        raise ValueError("FAST-QA-PASS обязан содержать exact head=<40 lowercase SHA>")
    return state, meta


def marker_from_body(body: str) -> str | None:
    state, _ = _control_parts(body)
    return state


def _qa_command_projection(event: dict, body: str) -> dict | None:
    if _first_line(body) != COMMAND_MARKER:
        return None
    issue = event.get("issue") or {}
    if not issue.get("pull_request"):
        raise ValueError("QA-COMMAND разрешена только в обсуждении PR")
    try:
        command = validate_command(parse_envelope(body, COMMAND_MARKER, COMMAND_FIELDS))
    except BridgeError as exc:
        raise ValueError(f"QA-COMMAND отклонена каноническим валидатором: {exc}") from exc
    issue_number = int(issue.get("number") or 0)
    if command["target_pr"] != issue_number:
        raise ValueError("QA-COMMAND target_pr не совпадает с номером PR")
    url = issue.get("html_url")
    if not url:
        raise ValueError("QA-COMMAND не содержит PR html_url в событии")
    return {
        "url": url,
        "state": "QA",
        "qa": command["executor_canonical"],
        "expected_head": command["exact_head"],
    }


def resolve(event_name: str, action: str, event: dict) -> dict | None:
    if event_name == "issue_comment" and action == "created":
        comment = event.get("comment") or {}
        if comment.get("author_association") != "OWNER":
            return None
        body = comment.get("body") or ""
        qa_projection = _qa_command_projection(event, body)
        if qa_projection is not None:
            return qa_projection
        state, meta = _control_parts(body)
        if not state:
            return None
        issue = event.get("issue") or {}
        url = issue.get("html_url")
        if not url:
            raise ValueError("trusted FAST marker не содержит issue/pr html_url")
        result = {"url": url, "state": state}
        if "head" in meta:
            result["expected_head"] = meta.pop("head")
        result.update(meta)
        return result

    if event_name == "issues":
        issue = event.get("issue") or {}
        url = issue.get("html_url")
        if not url:
            raise ValueError("issues event не содержит html_url")
        if action in {"opened", "reopened"}:
            return {"url": url, "state": "INBOX"}
        if action == "closed" and issue.get("state_reason") == "completed":
            return {"url": url, "state": "DONE"}
        return None

    if event_name == "pull_request":
        pr = event.get("pull_request") or {}
        url = pr.get("html_url")
        if not url:
            raise ValueError("pull_request event не содержит html_url")
        if action == "synchronize":
            return {"url": url, "state": "ACTIVE"}
        if action == "closed":
            return {"url": url, "state": "DONE" if pr.get("merged") is True else "BLOCKED"}
        return None

    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Fail-closed resolver событий Project queue KAT9I_OS")
    parser.add_argument("--event-name", required=True)
    parser.add_argument("--action", default="")
    parser.add_argument("--event-path", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    event = json.loads(args.event_path.read_text(encoding="utf-8"))
    result = resolve(args.event_name, args.action, event)
    payload = json.dumps(result or {}, ensure_ascii=False, separators=(",", ":"))
    if args.output:
        args.output.write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
