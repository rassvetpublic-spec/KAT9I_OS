import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


COMMAND_MARKER = "KAT9I-CONTROL/1 | QA-COMMAND"
RESULT_MARKER = "KAT9I-QA-RESULT/1"
BRIDGE_MARKER = "KAT9I-BRIDGE/1"
CONTROLLER = "ChatGPT"
ROLE = "QA_EXECUTOR"
RESULT_SINK = "PR_REVIEW"
QA_MODES = {"FULL", "DELTA", "REUSE"}
VERDICTS = {"QA PASS", "CHANGES REQUESTED", "BLOCKED", "QA ABORTED"}
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
COMMAND_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{5,127}$")
KEY_RE = re.compile(r"^[a-z][a-z0-9_]*$")

COMMAND_REQUIRED = {
    "command_id",
    "target_pr",
    "controller",
    "executor",
    "role",
    "exact_head",
    "qa_mode",
    "result_sink",
    "allow_issue_create",
    "allow_merge",
    "allow_fast_marker",
    "allow_code_mutation",
    "project_lifecycle_mutation",
}
RESULT_REQUIRED = {
    "command_id",
    "target_pr",
    "controller",
    "executor",
    "role",
    "exact_head",
    "qa_mode",
    "result_sink",
    "verdict",
    "blocking_findings",
    "follow_up_candidates",
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
    aliases = {"agy", "antigravity", "antigravity (agy)", "антигравити"}
    if normalized in aliases:
        return "AGY"
    raise BridgeError(f"unsupported QA executor: {value}")


def _bool(value: str, field: str) -> bool:
    if value == "true":
        return True
    if value == "false":
        return False
    raise BridgeError(f"{field} must be true or false")


def _nonnegative_int(value: str, field: str) -> int:
    if not re.fullmatch(r"0|[1-9][0-9]*", value):
        raise BridgeError(f"{field} must be a non-negative integer")
    return int(value)


def parse_envelope(body: str, marker: str, required: set[str]) -> dict[str, str]:
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
        if not value:
            raise BridgeError(f"empty envelope value: {key}")
        if key in meta:
            raise BridgeError(f"duplicate envelope key: {key}")
        meta[key] = value
    missing = sorted(required - meta.keys())
    if missing:
        raise BridgeError(f"missing envelope keys: {', '.join(missing)}")
    return meta


def validate_command(meta: dict[str, str]) -> dict[str, Any]:
    if not COMMAND_ID_RE.fullmatch(meta["command_id"]):
        raise BridgeError("invalid command_id")
    if not meta["target_pr"].isdigit() or int(meta["target_pr"]) <= 0:
        raise BridgeError("target_pr must be a positive integer")
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
    return {
        **meta,
        "target_pr": int(meta["target_pr"]),
        "executor_canonical": executor,
        **capabilities,
    }


def validate_result(meta: dict[str, str]) -> dict[str, Any]:
    if not COMMAND_ID_RE.fullmatch(meta["command_id"]):
        raise BridgeError("invalid command_id")
    if not meta["target_pr"].isdigit() or int(meta["target_pr"]) <= 0:
        raise BridgeError("target_pr must be a positive integer")
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
        "target_pr": int(meta["target_pr"]),
        "executor_canonical": executor,
        "blocking_findings": blocking,
        "follow_up_candidates": follow_ups,
    }


def _flatten_comments(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        return [value]
    if not isinstance(value, list):
        raise BridgeError("comments payload must be a list")
    flattened: list[dict[str, Any]] = []
    for item in value:
        if isinstance(item, list):
            flattened.extend(_flatten_comments(item))
        elif isinstance(item, dict):
            flattened.append(item)
        else:
            raise BridgeError("comments payload contains unsupported item")
    return flattened


def _bridge_receipt_command_id(body: str) -> str | None:
    for raw in (body or "").splitlines():
        line = raw.strip()
        if not line.startswith(BRIDGE_MARKER + " |"):
            continue
        parts = [part.strip() for part in line.split("|")]
        meta: dict[str, str] = {}
        for part in parts[1:]:
            if "=" not in part:
                continue
            key, value = part.split("=", 1)
            meta[key.strip()] = value.strip()
        return meta.get("command_id")
    return None


def resolve_bridge(event: dict[str, Any], comments_payload: Any) -> dict[str, Any]:
    action = event.get("action")
    if action != "submitted":
        return {"decision": "IGNORE", "reason": "review action is not submitted"}
    review = event.get("review") or {}
    pr = event.get("pull_request") or {}
    repository = event.get("repository") or {}
    if review.get("author_association") != "OWNER":
        return {"decision": "IGNORE", "reason": "review author is not repository OWNER"}
    body = review.get("body") or ""
    if not body.startswith(RESULT_MARKER):
        return {"decision": "IGNORE", "reason": "review is not a QA result envelope"}

    result = validate_result(parse_envelope(body, RESULT_MARKER, RESULT_REQUIRED))
    pr_number = pr.get("number") or event.get("number")
    if not isinstance(pr_number, int) or pr_number <= 0:
        raise BridgeError("event does not contain a valid PR number")
    if result["target_pr"] != pr_number:
        raise BridgeError("QA result target_pr does not match event PR")
    head_sha = ((pr.get("head") or {}).get("sha") or "").lower()
    if result["exact_head"] != head_sha:
        raise BridgeError("QA result exact_head is stale or does not match current PR HEAD")
    review_id = review.get("id")
    if review_id is None:
        raise BridgeError("review id is missing")
    submitted_at = _parse_time(review.get("submitted_at"))

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
        comment_body = comment.get("body") or ""
        if not comment_body.startswith(COMMAND_MARKER):
            continue
        try:
            command = validate_command(parse_envelope(comment_body, COMMAND_MARKER, COMMAND_REQUIRED))
        except BridgeError:
            continue
        if command["target_pr"] != pr_number:
            continue
        created_at = _parse_time(comment.get("created_at"))
        if created_at >= submitted_at:
            continue
        valid_commands.append((created_at, int(comment.get("id") or 0), command))

    matching = [item for item in valid_commands if item[2]["command_id"] == result["command_id"]]
    if len(matching) != 1:
        raise BridgeError("unknown or ambiguous command_id")
    matching_command = matching[0]
    latest = max(valid_commands, default=None, key=lambda item: (item[0], item[1]))
    if latest is None or latest[2]["command_id"] != result["command_id"]:
        raise BridgeError("QA result references a superseded command")
    command = matching_command[2]

    comparable = ("controller", "role", "exact_head", "qa_mode", "result_sink")
    for field in comparable:
        if command[field] != result[field]:
            raise BridgeError(f"command/result mismatch: {field}")
    if command["executor_canonical"] != result["executor_canonical"]:
        raise BridgeError("command/result mismatch: executor")
    if command["exact_head"] != head_sha:
        raise BridgeError("QA command exact_head is stale")

    lifecycle = "FAST-QA-PASS" if result["verdict"] == "QA PASS" else "FAST-BLOCKED"
    repo_full_name = repository.get("full_name") or ""
    if not repo_full_name:
        raise BridgeError("repository.full_name is missing")
    comment_body = (
        f"{lifecycle} | worker=ChatGPT | qa=AGY\n"
        f"{BRIDGE_MARKER} | command_id={result['command_id']} | review_id={review_id} | "
        f"verdict={result['verdict']} | exact_head={head_sha}\n"
        f"Controller bridge принял структурированный QA-результат. FOLLOW_UP_CANDIDATES={result['follow_up_candidates']}; "
        "содержательные кандидаты остаются в PR review и требуют отдельного dedupe/triage."
    )
    return {
        "decision": "ACCEPT",
        "command_id": result["command_id"],
        "review_id": review_id,
        "pr_number": pr_number,
        "repo_full_name": repo_full_name,
        "exact_head": head_sha,
        "verdict": result["verdict"],
        "lifecycle": lifecycle,
        "follow_up_candidates": result["follow_up_candidates"],
        "comment_body": comment_body,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Fail-closed QA command/result bridge KAT9I_OS")
    parser.add_argument("--event-path", type=Path, required=True)
    parser.add_argument("--comments-path", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--comment-output", type=Path)
    args = parser.parse_args()

    event = json.loads(args.event_path.read_text(encoding="utf-8"))
    comments = json.loads(args.comments_path.read_text(encoding="utf-8"))
    try:
        decision = resolve_bridge(event, comments)
    except BridgeError as exc:
        decision = {"decision": "REJECT", "reason": str(exc)}
        args.output.write_text(json.dumps(decision, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"KAT9I_QA_BRIDGE=REJECT | {exc}")
        return 2

    args.output.write_text(json.dumps(decision, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.comment_output and decision.get("decision") == "ACCEPT":
        args.comment_output.write_text(decision["comment_body"] + "\n", encoding="utf-8")
    print(f"KAT9I_QA_BRIDGE={decision.get('decision')} | {decision.get('reason', decision.get('command_id', ''))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
