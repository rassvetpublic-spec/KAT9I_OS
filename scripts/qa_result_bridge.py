import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


COMMAND_MARKER = "KAT9I-CONTROL/1 | QA-COMMAND"
RESULT_MARKER = "KAT9I-QA-RESULT/1"
ATTEST_MARKER = "KAT9I-CONTROL/1 | QA-ACCEPT"
BRIDGE_MARKER = "KAT9I-BRIDGE/1"
CONTROLLER = "ChatGPT"
ROLE = "QA_EXECUTOR"
RESULT_SINK = "PR_REVIEW"
QA_MODES = {"FULL", "DELTA", "REUSE"}
VERDICTS = {"QA PASS", "CHANGES REQUESTED", "BLOCKED", "QA ABORTED"}
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
COMMAND_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{5,127}$")
KEY_RE = re.compile(r"^[a-z][a-z0-9_]*$")

COMMAND_FIELDS = {
    "command_id", "target_pr", "controller", "executor", "role", "exact_head",
    "qa_mode", "result_sink", "allow_issue_create", "allow_merge",
    "allow_fast_marker", "allow_code_mutation", "project_lifecycle_mutation",
}
RESULT_FIELDS = {
    "command_id", "target_pr", "controller", "executor", "role", "exact_head",
    "qa_mode", "result_sink", "verdict", "blocking_findings", "follow_up_candidates",
}
ATTEST_FIELDS = {
    "command_id", "target_pr", "controller", "executor", "role", "review_id",
    "exact_head", "verdict",
}


class BridgeError(ValueError):
    pass


def _parse_time(value: str | None) -> datetime:
    if not value:
        raise BridgeError("missing timestamp")
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise BridgeError(f"invalid timestamp: {value}") from exc
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _canonical_executor(value: str) -> str:
    normalized = re.sub(r"\s+", " ", value.strip()).lower()
    if normalized in {"agy", "antigravity", "antigravity (agy)", "антигравити"}:
        return "AGY"
    raise BridgeError(f"unsupported QA executor: {value}")


def _bool(value: str, field: str) -> bool:
    if value == "true":
        return True
    if value == "false":
        return False
    raise BridgeError(f"{field} must be true or false")


def _positive_int(value: str, field: str) -> int:
    if not re.fullmatch(r"[1-9][0-9]*", value):
        raise BridgeError(f"{field} must be a positive integer")
    return int(value)


def _nonnegative_int(value: str, field: str) -> int:
    if not re.fullmatch(r"0|[1-9][0-9]*", value):
        raise BridgeError(f"{field} must be a non-negative integer")
    return int(value)


def parse_envelope(body: str, marker: str, fields: set[str]) -> dict[str, str]:
    lines = (body or "").splitlines()
    if not lines or lines[0].strip() != marker:
        raise BridgeError(f"first line must be exact marker: {marker}")
    meta: dict[str, str] = {}
    for raw in lines[1:]:
        line = raw.strip()
        if not line:
            break
        if "=" not in line:
            raise BridgeError(f"malformed envelope line: {line}")
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not KEY_RE.fullmatch(key):
            raise BridgeError(f"invalid envelope key: {key}")
        if key not in fields:
            raise BridgeError(f"unknown envelope key: {key}")
        if not value:
            raise BridgeError(f"empty envelope value: {key}")
        if key in meta:
            raise BridgeError(f"duplicate envelope key: {key}")
        meta[key] = value
    missing = sorted(fields - meta.keys())
    if missing:
        raise BridgeError(f"missing envelope keys: {', '.join(missing)}")
    return meta


def validate_command(meta: dict[str, str]) -> dict[str, Any]:
    if not COMMAND_ID_RE.fullmatch(meta["command_id"]):
        raise BridgeError("invalid command_id")
    target_pr = _positive_int(meta["target_pr"], "target_pr")
    if meta["controller"] != CONTROLLER:
        raise BridgeError("controller mismatch")
    executor = _canonical_executor(meta["executor"])
    if meta["role"] != ROLE:
        raise BridgeError("role mismatch")
    if not SHA_RE.fullmatch(meta["exact_head"]):
        raise BridgeError("invalid exact_head")
    if meta["qa_mode"] not in QA_MODES:
        raise BridgeError("unsupported qa_mode")
    if meta["result_sink"] != RESULT_SINK:
        raise BridgeError("result_sink must be PR_REVIEW")
    capabilities = {
        "allow_issue_create": _bool(meta["allow_issue_create"], "allow_issue_create"),
        "allow_merge": _bool(meta["allow_merge"], "allow_merge"),
        "allow_fast_marker": _bool(meta["allow_fast_marker"], "allow_fast_marker"),
        "allow_code_mutation": _bool(meta["allow_code_mutation"], "allow_code_mutation"),
        "project_lifecycle_mutation": _bool(meta["project_lifecycle_mutation"], "project_lifecycle_mutation"),
    }
    for forbidden in ("allow_merge", "allow_fast_marker", "allow_code_mutation", "project_lifecycle_mutation"):
        if capabilities[forbidden]:
            raise BridgeError(f"QA command grants forbidden capability: {forbidden}")
    return {**meta, "target_pr": target_pr, "executor_canonical": executor, **capabilities}


def validate_result(meta: dict[str, str]) -> dict[str, Any]:
    if not COMMAND_ID_RE.fullmatch(meta["command_id"]):
        raise BridgeError("invalid command_id")
    target_pr = _positive_int(meta["target_pr"], "target_pr")
    if meta["controller"] != CONTROLLER:
        raise BridgeError("controller mismatch")
    executor = _canonical_executor(meta["executor"])
    if meta["role"] != ROLE:
        raise BridgeError("role mismatch")
    if not SHA_RE.fullmatch(meta["exact_head"]):
        raise BridgeError("invalid exact_head")
    if meta["qa_mode"] not in QA_MODES:
        raise BridgeError("unsupported qa_mode")
    if meta["result_sink"] != RESULT_SINK:
        raise BridgeError("result_sink must be PR_REVIEW")
    if meta["verdict"] not in VERDICTS:
        raise BridgeError("unsupported verdict")
    blocking = _nonnegative_int(meta["blocking_findings"], "blocking_findings")
    follow_ups = _nonnegative_int(meta["follow_up_candidates"], "follow_up_candidates")
    if meta["verdict"] == "QA PASS" and blocking != 0:
        raise BridgeError("QA PASS cannot contain blocking findings")
    return {
        **meta,
        "target_pr": target_pr,
        "executor_canonical": executor,
        "blocking_findings": blocking,
        "follow_up_candidates": follow_ups,
    }


def validate_attestation(meta: dict[str, str]) -> dict[str, Any]:
    if not COMMAND_ID_RE.fullmatch(meta["command_id"]):
        raise BridgeError("invalid command_id")
    target_pr = _positive_int(meta["target_pr"], "target_pr")
    if meta["controller"] != CONTROLLER:
        raise BridgeError("controller mismatch")
    executor = _canonical_executor(meta["executor"])
    if meta["role"] != ROLE:
        raise BridgeError("role mismatch")
    review_id = _positive_int(meta["review_id"], "review_id")
    if not SHA_RE.fullmatch(meta["exact_head"]):
        raise BridgeError("invalid exact_head")
    if meta["verdict"] not in VERDICTS:
        raise BridgeError("unsupported verdict")
    return {
        **meta,
        "target_pr": target_pr,
        "review_id": review_id,
        "executor_canonical": executor,
    }


def _flatten_comments(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        return [value]
    if not isinstance(value, list):
        raise BridgeError("comments payload must be a list")
    result: list[dict[str, Any]] = []
    for item in value:
        if isinstance(item, list):
            result.extend(_flatten_comments(item))
        elif isinstance(item, dict):
            result.append(item)
        else:
            raise BridgeError("comments payload contains unsupported item")
    return result


def _first_line(body: str) -> str:
    lines = (body or "").splitlines()
    return lines[0].strip() if lines else ""


def _bridge_receipt_command_id(body: str) -> str | None:
    for raw in (body or "").splitlines():
        line = raw.strip()
        if not line.startswith(BRIDGE_MARKER + " |"):
            continue
        parts = [part.strip() for part in line.split("|")]
        meta: dict[str, str] = {}
        for part in parts[1:]:
            if "=" in part:
                key, value = part.split("=", 1)
                meta[key.strip()] = value.strip()
        return meta.get("command_id")
    return None


def extract_attestation(event: dict[str, Any]) -> dict[str, Any] | None:
    if event.get("action") != "created":
        return None
    comment = event.get("comment") or {}
    if comment.get("author_association") != "OWNER":
        return None
    body = comment.get("body") or ""
    if _first_line(body) != ATTEST_MARKER:
        return None
    return validate_attestation(parse_envelope(body, ATTEST_MARKER, ATTEST_FIELDS))


def resolve_bridge(
    event: dict[str, Any],
    comments_payload: Any,
    review_payload: dict[str, Any],
    current_pr: dict[str, Any],
) -> dict[str, Any]:
    attestation = extract_attestation(event)
    if attestation is None:
        return {"decision": "IGNORE", "reason": "event is not a trusted Controller QA-ACCEPT"}

    issue = event.get("issue") or {}
    pr_number = issue.get("number") or event.get("number")
    if not isinstance(pr_number, int) or pr_number <= 0:
        raise BridgeError("event does not contain a valid PR number")
    if attestation["target_pr"] != pr_number:
        raise BridgeError("QA-ACCEPT target_pr does not match event PR")
    if not issue.get("pull_request"):
        raise BridgeError("QA-ACCEPT is allowed only on a pull request conversation")

    if current_pr.get("state") != "open":
        raise BridgeError("current PR is not open")
    live_head = ((current_pr.get("head") or {}).get("sha") or "").lower()
    if attestation["exact_head"] != live_head:
        raise BridgeError("QA-ACCEPT exact_head is stale against live PR HEAD")

    review_id = review_payload.get("id")
    if review_id != attestation["review_id"]:
        raise BridgeError("QA-ACCEPT review_id does not match fetched review")
    if review_payload.get("author_association") != "OWNER":
        raise BridgeError("referenced QA review is not owner-associated evidence")
    result = validate_result(parse_envelope(review_payload.get("body") or "", RESULT_MARKER, RESULT_FIELDS))
    if result["target_pr"] != pr_number:
        raise BridgeError("QA result target_pr does not match PR")
    if result["exact_head"] != live_head:
        raise BridgeError("QA result exact_head is stale against live PR HEAD")
    submitted_at = _parse_time(review_payload.get("submitted_at"))
    attested_at = _parse_time((event.get("comment") or {}).get("created_at"))
    if attested_at <= submitted_at:
        raise BridgeError("Controller QA-ACCEPT must be created after the QA review")

    for field in ("command_id", "controller", "role", "exact_head", "verdict"):
        if str(attestation[field]) != str(result[field]):
            raise BridgeError(f"QA-ACCEPT/result mismatch: {field}")
    if attestation["executor_canonical"] != result["executor_canonical"]:
        raise BridgeError("QA-ACCEPT/result mismatch: executor")

    comments = _flatten_comments(comments_payload)
    processed_ids = {
        cid
        for comment in comments
        if comment.get("author_association") == "OWNER"
        for cid in [_bridge_receipt_command_id(comment.get("body") or "")]
        if cid
    }
    if result["command_id"] in processed_ids:
        return {
            "decision": "REPLAY",
            "reason": "command_id already has a bridge receipt",
            "command_id": result["command_id"],
        }

    valid_commands: list[tuple[datetime, int, dict[str, Any]]] = []
    for comment in comments:
        if comment.get("author_association") != "OWNER":
            continue
        body = comment.get("body") or ""
        if _first_line(body) != COMMAND_MARKER:
            continue
        created_at = _parse_time(comment.get("created_at"))
        if created_at >= attested_at:
            continue
        try:
            command = validate_command(parse_envelope(body, COMMAND_MARKER, COMMAND_FIELDS))
        except BridgeError as exc:
            raise BridgeError(f"malformed owner QA-COMMAND before attestation: {exc}") from exc
        if command["target_pr"] != pr_number:
            raise BridgeError("owner QA-COMMAND is posted in the wrong PR conversation")
        valid_commands.append((created_at, int(comment.get("id") or 0), command))

    matching = [item for item in valid_commands if item[2]["command_id"] == result["command_id"]]
    if len(matching) != 1:
        raise BridgeError("unknown or ambiguous command_id")
    latest = max(valid_commands, default=None, key=lambda item: (item[0], item[1]))
    if latest is None or latest[2]["command_id"] != result["command_id"]:
        raise BridgeError("QA result references a superseded command")
    command_created_at, _, command = matching[0]
    if command_created_at >= submitted_at:
        raise BridgeError("QA-COMMAND must exist before the QA review")

    for field in ("controller", "role", "exact_head", "qa_mode", "result_sink"):
        if command[field] != result[field]:
            raise BridgeError(f"command/result mismatch: {field}")
    if command["executor_canonical"] != result["executor_canonical"]:
        raise BridgeError("command/result mismatch: executor")
    if command["exact_head"] != live_head:
        raise BridgeError("QA-COMMAND exact_head is stale against live PR HEAD")

    lifecycle = "FAST-QA-PASS" if result["verdict"] == "QA PASS" else "FAST-BLOCKED"
    repository = event.get("repository") or {}
    repo_full_name = repository.get("full_name") or ""
    if not repo_full_name:
        raise BridgeError("repository.full_name is missing")
    comment_body = (
        f"{lifecycle} | worker=ChatGPT | qa=AGY | head={live_head}\n"
        f"{BRIDGE_MARKER} | command_id={result['command_id']} | review_id={review_id} | "
        f"verdict={result['verdict']} | exact_head={live_head}\n"
        "Controller отдельно аттестовал независимый QA review; review сам по себе не имеет lifecycle-власти. "
        f"FOLLOW_UP_CANDIDATES={result['follow_up_candidates']}; кандидаты требуют dedupe/triage."
    )
    return {
        "decision": "ACCEPT",
        "command_id": result["command_id"],
        "review_id": review_id,
        "pr_number": pr_number,
        "repo_full_name": repo_full_name,
        "exact_head": live_head,
        "verdict": result["verdict"],
        "lifecycle": lifecycle,
        "follow_up_candidates": result["follow_up_candidates"],
        "comment_body": comment_body,
    }


def _write_output(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Fail-closed Controller attestation bridge KAT9I_OS")
    sub = parser.add_subparsers(dest="command", required=True)

    extract = sub.add_parser("extract-review-id")
    extract.add_argument("--event-path", type=Path, required=True)

    resolve = sub.add_parser("resolve")
    resolve.add_argument("--event-path", type=Path, required=True)
    resolve.add_argument("--comments-path", type=Path, required=True)
    resolve.add_argument("--review-path", type=Path, required=True)
    resolve.add_argument("--current-pr-path", type=Path, required=True)
    resolve.add_argument("--output", type=Path, required=True)
    resolve.add_argument("--comment-output", type=Path)
    args = parser.parse_args()

    event = json.loads(args.event_path.read_text(encoding="utf-8"))
    try:
        if args.command == "extract-review-id":
            attestation = extract_attestation(event)
            if attestation is None:
                return 3
            print(attestation["review_id"])
            return 0

        comments = json.loads(args.comments_path.read_text(encoding="utf-8"))
        review = json.loads(args.review_path.read_text(encoding="utf-8"))
        current_pr = json.loads(args.current_pr_path.read_text(encoding="utf-8"))
        decision = resolve_bridge(event, comments, review, current_pr)
    except BridgeError as exc:
        if args.command == "resolve":
            _write_output(args.output, {"decision": "REJECT", "reason": str(exc)})
        print(f"KAT9I_QA_BRIDGE=REJECT | {exc}")
        return 2

    _write_output(args.output, decision)
    if args.comment_output and decision.get("decision") == "ACCEPT":
        args.comment_output.write_text(decision["comment_body"] + "\n", encoding="utf-8")
    print(f"KAT9I_QA_BRIDGE={decision.get('decision')} | {decision.get('reason', decision.get('command_id', ''))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
