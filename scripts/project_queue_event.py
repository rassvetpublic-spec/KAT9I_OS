import argparse
import json
from pathlib import Path


CONTROL_MARKERS = {
    "FAST-CLAIM": "ACTIVE",
    "FAST-QA": "QA",
    "FAST-QA-PASS": "QUEUED",
    "FAST-BLOCKED": "BLOCKED",
    "FAST-RELEASE": "DONE",
}


def marker_from_body(body: str) -> str | None:
    first_line = (body or "").splitlines()[0].strip()
    if not first_line:
        return None
    token = first_line.split("|", 1)[0].strip()
    return CONTROL_MARKERS.get(token)


def resolve(event_name: str, action: str, event: dict) -> dict | None:
    if event_name == "issue_comment" and action == "created":
        comment = event.get("comment") or {}
        if comment.get("author_association") != "OWNER":
            return None
        state = marker_from_body(comment.get("body") or "")
        if not state:
            return None
        issue = event.get("issue") or {}
        url = issue.get("html_url")
        if not url:
            raise ValueError("trusted FAST marker не содержит issue/pr html_url")
        return {"url": url, "state": state}

    if event_name == "issues":
        issue = event.get("issue") or {}
        url = issue.get("html_url")
        if not url:
            raise ValueError("issues event не содержит html_url")
        if action in {"opened", "reopened"}:
            return {"url": url, "state": "READY"}
        if action == "closed":
            return {"url": url, "state": "DONE"}
        return None

    if event_name == "pull_request" and action == "closed":
        pr = event.get("pull_request") or {}
        url = pr.get("html_url")
        if not url:
            raise ValueError("pull_request event не содержит html_url")
        return {"url": url, "state": "DONE" if pr.get("merged") is True else "BLOCKED"}

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
