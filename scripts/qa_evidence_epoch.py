import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


EPOCH_HEADER = "EVIDENCE_EPOCH"
EPOCH_VERSION = "1"
COMMAND_MARKER = "KAT9I-CONTROL/1 | QA-COMMAND"
RESULT_MARKER = "KAT9I-QA-RESULT/1"
ATTEST_MARKER = "KAT9I-CONTROL/1 | QA-ACCEPT"
POLICY_FILES = (
    "QA_PROTOCOL.md",
    "scripts/qa_result_bridge.py",
    "scripts/qa_evidence_epoch.py",
    ".github/workflows/qa-result-bridge.yml",
)
SHA40_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
KEY_RE = re.compile(r"^[a-z][a-z0-9_]*$")
EPOCH_FIELDS = {
    "epoch_version",
    "snapshot_head",
    "review_digest",
    "gate_digest",
    "policy_digest",
    "evidence_digest",
}


class EvidenceEpochError(ValueError):
    pass


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _sha256_obj(value: Any) -> str:
    return _sha256_text(_canonical_json(value))


def _first_line(body: str) -> str:
    lines = (body or "").splitlines()
    return lines[0].strip() if lines else ""


def _parse_machine_field(body: str, key: str) -> str | None:
    lines = (body or "").splitlines()
    for raw in lines[1:]:
        line = raw.strip()
        if not line:
            break
        if "=" not in line:
            continue
        current_key, value = line.split("=", 1)
        if current_key.strip() == key:
            return value.strip()
    return None


def parse_epoch_section(body: str) -> dict[str, str]:
    lines = (body or "").splitlines()
    positions = [index for index, raw in enumerate(lines) if raw.strip() == EPOCH_HEADER]
    if len(positions) != 1:
        raise EvidenceEpochError("MALFORMED_EVIDENCE: exactly one EVIDENCE_EPOCH section is required")

    meta: dict[str, str] = {}
    for raw in lines[positions[0] + 1 :]:
        line = raw.strip()
        if not line:
            break
        if "=" not in line:
            break
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not KEY_RE.fullmatch(key):
            raise EvidenceEpochError(f"MALFORMED_EVIDENCE: invalid epoch key {key}")
        if key not in EPOCH_FIELDS:
            raise EvidenceEpochError(f"MALFORMED_EVIDENCE: unknown epoch key {key}")
        if not value:
            raise EvidenceEpochError(f"MALFORMED_EVIDENCE: empty epoch value {key}")
        if key in meta:
            raise EvidenceEpochError(f"MALFORMED_EVIDENCE: duplicate epoch key {key}")
        meta[key] = value

    missing = sorted(EPOCH_FIELDS - meta.keys())
    if missing:
        raise EvidenceEpochError("MALFORMED_EVIDENCE: missing epoch keys: " + ", ".join(missing))
    if meta["epoch_version"] != EPOCH_VERSION:
        raise EvidenceEpochError("MALFORMED_EVIDENCE: unsupported epoch_version")
    if not SHA40_RE.fullmatch(meta["snapshot_head"]):
        raise EvidenceEpochError("MALFORMED_EVIDENCE: invalid snapshot_head")
    for key in ("review_digest", "gate_digest", "policy_digest", "evidence_digest"):
        if not SHA256_RE.fullmatch(meta[key]):
            raise EvidenceEpochError(f"MALFORMED_EVIDENCE: invalid {key}")

    expected = aggregate_digest(
        snapshot_head=meta["snapshot_head"],
        review_digest=meta["review_digest"],
        gate_digest=meta["gate_digest"],
        policy_digest=meta["policy_digest"],
    )
    if meta["evidence_digest"] != expected:
        raise EvidenceEpochError("MALFORMED_EVIDENCE: evidence_digest does not match components")
    return meta


def aggregate_digest(snapshot_head: str, review_digest: str, gate_digest: str, policy_digest: str) -> str:
    return _sha256_obj(
        {
            "epoch_version": EPOCH_VERSION,
            "snapshot_head": snapshot_head,
            "review_digest": review_digest,
            "gate_digest": gate_digest,
            "policy_digest": policy_digest,
        }
    )


def _review_thread_nodes(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        nodes = payload
    elif isinstance(payload, dict):
        node: Any = payload
        for key in ("data", "repository", "pullRequest", "reviewThreads"):
            if not isinstance(node, dict) or key not in node:
                raise EvidenceEpochError("MALFORMED_EVIDENCE: review threads payload has unexpected shape")
            node = node[key]
        nodes = node.get("nodes") if isinstance(node, dict) else None
    else:
        nodes = None
    if not isinstance(nodes, list):
        raise EvidenceEpochError("MALFORMED_EVIDENCE: review threads nodes must be a list")
    if not all(isinstance(item, dict) for item in nodes):
        raise EvidenceEpochError("MALFORMED_EVIDENCE: review thread must be an object")
    return nodes


def canonical_review_state(threads_payload: Any, reviews_payload: Any) -> dict[str, Any]:
    threads: list[dict[str, Any]] = []
    for thread in _review_thread_nodes(threads_payload):
        thread_id = thread.get("id")
        resolved = thread.get("isResolved")
        comments_node = thread.get("comments") or {}
        comments = comments_node.get("nodes") if isinstance(comments_node, dict) else None
        if not isinstance(thread_id, str) or not thread_id:
            raise EvidenceEpochError("MALFORMED_EVIDENCE: review thread id is missing")
        if not isinstance(resolved, bool):
            raise EvidenceEpochError("MALFORMED_EVIDENCE: review thread isResolved must be boolean")
        if not isinstance(comments, list) or not comments:
            raise EvidenceEpochError("MALFORMED_EVIDENCE: review thread comments are missing")
        canonical_comments: list[dict[str, Any]] = []
        for comment in comments:
            if not isinstance(comment, dict):
                raise EvidenceEpochError("MALFORMED_EVIDENCE: review comment must be an object")
            comment_id = comment.get("id") or comment.get("databaseId")
            if comment_id is None:
                raise EvidenceEpochError("MALFORMED_EVIDENCE: review comment id is missing")
            canonical_comments.append(
                {
                    "id": str(comment_id),
                    "body_sha256": _sha256_text(str(comment.get("body") or "")),
                    "path": str(comment.get("path") or ""),
                    "line": comment.get("line"),
                    "start_line": comment.get("startLine"),
                    "outdated": bool(comment.get("outdated", False)),
                }
            )
        canonical_comments.sort(key=lambda item: item["id"])
        threads.append({"id": thread_id, "resolved": resolved, "comments": canonical_comments})
    threads.sort(key=lambda item: item["id"])

    if isinstance(reviews_payload, dict) and "reviews" in reviews_payload:
        raw_reviews = reviews_payload.get("reviews")
    else:
        raw_reviews = reviews_payload
    if not isinstance(raw_reviews, list):
        raise EvidenceEpochError("MALFORMED_EVIDENCE: reviews payload must be a list")
    reviews: list[dict[str, Any]] = []
    for review in raw_reviews:
        if not isinstance(review, dict):
            raise EvidenceEpochError("MALFORMED_EVIDENCE: review must be an object")
        body = str(review.get("body") or "")
        if _first_line(body) == RESULT_MARKER:
            continue
        review_id = review.get("id")
        if review_id is None:
            raise EvidenceEpochError("MALFORMED_EVIDENCE: review id is missing")
        state = str(review.get("state") or "").upper()
        reviews.append(
            {
                "id": str(review_id),
                "state": state,
                "commit_id": str(review.get("commit_id") or "").lower(),
                "body_sha256": _sha256_text(body),
            }
        )
    reviews.sort(key=lambda item: item["id"])
    return {"threads": threads, "reviews": reviews}


def _latest_by(items: list[dict[str, Any]], key_fn, order_fn) -> list[dict[str, Any]]:
    latest: dict[Any, dict[str, Any]] = {}
    for item in items:
        key = key_fn(item)
        if key is None:
            raise EvidenceEpochError("MALFORMED_EVIDENCE: gate item key is missing")
        old = latest.get(key)
        if old is None or order_fn(item) > order_fn(old):
            latest[key] = item
    return list(latest.values())


def canonical_gate_state(checks_payload: Any, statuses_payload: Any) -> dict[str, Any]:
    if not isinstance(checks_payload, dict) or not isinstance(checks_payload.get("check_runs", []), list):
        raise EvidenceEpochError("MALFORMED_EVIDENCE: check-runs payload has unexpected shape")
    checks_raw = [item for item in checks_payload.get("check_runs", []) if isinstance(item, dict)]
    checks_latest = _latest_by(
        checks_raw,
        lambda item: (str(item.get("name") or ""), str((item.get("app") or {}).get("slug") or "")),
        lambda item: (str(item.get("completed_at") or item.get("started_at") or ""), int(item.get("id") or 0)),
    )
    checks = sorted(
        (
            {
                "name": str(item.get("name") or ""),
                "app": str((item.get("app") or {}).get("slug") or ""),
                "status": str(item.get("status") or "").lower(),
                "conclusion": str(item.get("conclusion") or "").lower(),
            }
            for item in checks_latest
        ),
        key=lambda item: (item["name"], item["app"]),
    )

    if not isinstance(statuses_payload, dict) or not isinstance(statuses_payload.get("statuses", []), list):
        raise EvidenceEpochError("MALFORMED_EVIDENCE: commit-status payload has unexpected shape")
    statuses_raw = [item for item in statuses_payload.get("statuses", []) if isinstance(item, dict)]
    statuses_latest = _latest_by(
        statuses_raw,
        lambda item: str(item.get("context") or ""),
        lambda item: (str(item.get("updated_at") or item.get("created_at") or ""), int(item.get("id") or 0)),
    )
    statuses = sorted(
        (
            {
                "context": str(item.get("context") or ""),
                "state": str(item.get("state") or "").lower(),
            }
            for item in statuses_latest
        ),
        key=lambda item: item["context"],
    )
    return {"checks": checks, "statuses": statuses}


def policy_digest(root: Path) -> str:
    records: list[dict[str, str]] = []
    for relative in POLICY_FILES:
        path = root / relative
        if not path.is_file():
            raise EvidenceEpochError(f"MALFORMED_EVIDENCE: policy file missing: {relative}")
        records.append({"path": relative, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    return _sha256_obj(records)


def build_snapshot(
    head: str,
    threads_payload: Any,
    reviews_payload: Any,
    checks_payload: Any,
    statuses_payload: Any,
    root: Path,
) -> dict[str, str]:
    head = head.lower()
    if not SHA40_RE.fullmatch(head):
        raise EvidenceEpochError("MALFORMED_EVIDENCE: live HEAD must be a 40-char lowercase SHA")
    review_digest = _sha256_obj(canonical_review_state(threads_payload, reviews_payload))
    gate_digest = _sha256_obj(canonical_gate_state(checks_payload, statuses_payload))
    p_digest = policy_digest(root)
    return {
        "epoch_version": EPOCH_VERSION,
        "snapshot_head": head,
        "review_digest": review_digest,
        "gate_digest": gate_digest,
        "policy_digest": p_digest,
        "evidence_digest": aggregate_digest(head, review_digest, gate_digest, p_digest),
    }


def render_epoch_section(snapshot: dict[str, str]) -> str:
    return EPOCH_HEADER + "\n" + "\n".join(f"{key}={snapshot[key]}" for key in (
        "epoch_version", "snapshot_head", "review_digest", "gate_digest", "policy_digest", "evidence_digest"
    ))


def _matching_command_body(comments_payload: Any, command_id: str) -> str:
    if isinstance(comments_payload, dict):
        comments = [comments_payload]
    elif isinstance(comments_payload, list):
        comments = []
        for item in comments_payload:
            if isinstance(item, list):
                comments.extend(item)
            elif isinstance(item, dict):
                comments.append(item)
            else:
                raise EvidenceEpochError("MALFORMED_EVIDENCE: comments payload contains unsupported item")
    else:
        raise EvidenceEpochError("MALFORMED_EVIDENCE: comments payload must be a list")

    matches = []
    for comment in comments:
        if comment.get("author_association") != "OWNER":
            continue
        body = str(comment.get("body") or "")
        if _first_line(body) != COMMAND_MARKER:
            continue
        if _parse_machine_field(body, "command_id") == command_id:
            matches.append(body)
    if len(matches) != 1:
        raise EvidenceEpochError("MALFORMED_EVIDENCE: command_id must resolve to exactly one owner QA-COMMAND")
    return matches[0]


def validate_current_epoch(
    command_id: str,
    comments_payload: Any,
    review_payload: Any,
    event_payload: Any,
    current_head: str,
    threads_payload: Any,
    reviews_payload: Any,
    checks_payload: Any,
    statuses_payload: Any,
    root: Path,
) -> dict[str, str]:
    if not isinstance(review_payload, dict) or not isinstance(event_payload, dict):
        raise EvidenceEpochError("MALFORMED_EVIDENCE: review/event payload must be objects")
    command_body = _matching_command_body(comments_payload, command_id)
    result_body = str(review_payload.get("body") or "")
    attestation_body = str((event_payload.get("comment") or {}).get("body") or "")
    if _first_line(result_body) != RESULT_MARKER or _first_line(attestation_body) != ATTEST_MARKER:
        raise EvidenceEpochError("MALFORMED_EVIDENCE: result/attestation markers do not match QA protocol")

    command_epoch = parse_epoch_section(command_body)
    result_epoch = parse_epoch_section(result_body)
    attest_epoch = parse_epoch_section(attestation_body)
    if command_epoch != result_epoch or command_epoch != attest_epoch:
        raise EvidenceEpochError("MALFORMED_EVIDENCE: command/result/attestation epoch mismatch")

    verdict = _parse_machine_field(result_body, "verdict")
    if verdict != "QA PASS":
        return {**command_epoch, "decision": "BLOCKING_VERDICT_SAFE"}

    current = build_snapshot(
        head=current_head,
        threads_payload=threads_payload,
        reviews_payload=reviews_payload,
        checks_payload=checks_payload,
        statuses_payload=statuses_payload,
        root=root,
    )
    if command_epoch["snapshot_head"] != current["snapshot_head"]:
        raise EvidenceEpochError("HEAD_DRIFT: Evidence Epoch HEAD differs from live PR HEAD")
    if command_epoch["review_digest"] != current["review_digest"]:
        raise EvidenceEpochError("REVIEW_DRIFT: review state changed after QA-COMMAND")
    if command_epoch["gate_digest"] != current["gate_digest"]:
        raise EvidenceEpochError("GATE_DRIFT: qualifying CI/status state changed after QA-COMMAND")
    if command_epoch["policy_digest"] != current["policy_digest"]:
        raise EvidenceEpochError("POLICY_DRIFT: trusted QA protocol changed after QA-COMMAND")
    if command_epoch["evidence_digest"] != current["evidence_digest"]:
        raise EvidenceEpochError("MALFORMED_EVIDENCE: aggregate Evidence Digest mismatch")
    return {**current, "decision": "FRESH"}


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="KAT9I_OS QA Evidence Epoch validator")
    sub = parser.add_subparsers(dest="command", required=True)

    snapshot = sub.add_parser("snapshot")
    snapshot.add_argument("--head", required=True)
    snapshot.add_argument("--review-threads-path", type=Path, required=True)
    snapshot.add_argument("--reviews-path", type=Path, required=True)
    snapshot.add_argument("--check-runs-path", type=Path, required=True)
    snapshot.add_argument("--status-path", type=Path, required=True)
    snapshot.add_argument("--root", type=Path, default=Path("."))
    snapshot.add_argument("--output", type=Path, required=True)
    snapshot.add_argument("--section-output", type=Path)

    validate = sub.add_parser("validate")
    validate.add_argument("--command-id", required=True)
    validate.add_argument("--comments-path", type=Path, required=True)
    validate.add_argument("--review-path", type=Path, required=True)
    validate.add_argument("--event-path", type=Path, required=True)
    validate.add_argument("--head", required=True)
    validate.add_argument("--review-threads-path", type=Path, required=True)
    validate.add_argument("--reviews-path", type=Path, required=True)
    validate.add_argument("--check-runs-path", type=Path, required=True)
    validate.add_argument("--status-path", type=Path, required=True)
    validate.add_argument("--root", type=Path, default=Path("."))
    validate.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    try:
        if args.command == "snapshot":
            result = build_snapshot(
                args.head,
                _load(args.review_threads_path),
                _load(args.reviews_path),
                _load(args.check_runs_path),
                _load(args.status_path),
                args.root,
            )
            _write(args.output, result)
            if args.section_output:
                args.section_output.write_text(render_epoch_section(result) + "\n", encoding="utf-8")
            print(f"KAT9I_EVIDENCE_EPOCH=SNAPSHOT | {result['evidence_digest']}")
            return 0

        result = validate_current_epoch(
            command_id=args.command_id,
            comments_payload=_load(args.comments_path),
            review_payload=_load(args.review_path),
            event_payload=_load(args.event_path),
            current_head=args.head,
            threads_payload=_load(args.review_threads_path),
            reviews_payload=_load(args.reviews_path),
            checks_payload=_load(args.check_runs_path),
            statuses_payload=_load(args.status_path),
            root=args.root,
        )
        _write(args.output, result)
        print(f"KAT9I_EVIDENCE_EPOCH={result['decision']} | {result['evidence_digest']}")
        return 0
    except (EvidenceEpochError, json.JSONDecodeError, OSError) as exc:
        if hasattr(args, "output"):
            _write(args.output, {"decision": "REJECT", "reason": str(exc)})
        print(f"KAT9I_EVIDENCE_EPOCH=REJECT | {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
