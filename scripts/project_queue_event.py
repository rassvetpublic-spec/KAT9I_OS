import argparse
import json
import re
from pathlib import Path


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


def _control_parts(body: str) -> tuple[str | None, dict[str, str]]:
    first_line = (body or "").splitlines()[0].strip()
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


def resolve(event_name: str, action: str, event: dict) -> dict | None:
    if event_name == "issue_comment" and action == "created":
        comment = event.get("comment") or {}
        if comment.get("author_association") != "OWNER":
            return None
        state, meta = _control_parts(comment.get("body") or "")
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
        if action in {"opened", "reopened", "ready_for_review", "synchronize"}:
            return {"url": url, "state": "WAITING_FOR_REQUIRED_CHECK"}
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
