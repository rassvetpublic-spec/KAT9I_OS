from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

SCHEMA_VERSION = 1
OPERATION_PROMOTE_CHANGE = "PROMOTE_CHANGE"
DECISION_ALLOW = "ALLOW"
DECISION_DENY = "DENY"
DECISION_STALE = "STALE"
ACTION_HASH_PREFIX = "sha256:"


def _parse_time(value: str) -> datetime:
    text = str(value or "").strip()
    if not text:
        raise ValueError("missing timestamp")
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        raise ValueError("timestamp must include timezone")
    return dt.astimezone(timezone.utc)


def canonical_action_payload(
    *,
    operation: str,
    subject_ref: str,
    subject_revision: str,
    target_ref: str,
    target_revision: str,
    policy_ref: str,
    policy_version: str,
    evidence_digest: str,
) -> Dict[str, str]:
    return {
        "operation": operation,
        "policy_ref": policy_ref,
        "policy_version": policy_version,
        "evidence_digest": evidence_digest,
        "subject_ref": subject_ref,
        "subject_revision": subject_revision,
        "target_ref": target_ref,
        "target_revision": target_revision,
    }


def compute_action_hash(payload: Dict[str, Any]) -> str:
    # v1 payload is intentionally narrow: strings only, sorted keys, UTF-8.
    if not isinstance(payload, dict) or not payload:
        raise ValueError("action payload must be a non-empty object")
    for key, value in payload.items():
        if not isinstance(key, str) or not isinstance(value, str) or not value:
            raise ValueError("v1 action payload must contain non-empty string keys and values")
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return ACTION_HASH_PREFIX + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _missing(data: Dict[str, Any], paths: Iterable[Tuple[str, ...]]) -> List[str]:
    result: List[str] = []
    for path in paths:
        current: Any = data
        for part in path:
            if not isinstance(current, dict) or part not in current:
                result.append(".".join(path))
                break
            current = current[part]
        else:
            if current is None or current == "":
                result.append(".".join(path))
    return result


def evaluate(snapshot: Dict[str, Any], *, now: datetime | None = None) -> Dict[str, Any]:
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    required = [
        ("schema",),
        ("operation",),
        ("action_hash",),
        ("subject", "ref"),
        ("subject", "revision"),
        ("target", "ref"),
        ("target", "revision"),
        ("live", "subject_revision"),
        ("live", "target_revision"),
        ("policy", "ref"),
        ("policy", "version"),
        ("evidence_digest",),
        ("qa", "verdict"),
        ("qa", "subject_revision"),
        ("integration", "verdict"),
        ("integration", "subject_revision"),
        ("integration", "target_revision"),
    ]
    missing = _missing(snapshot, required)
    if missing:
        return {
            "schema": SCHEMA_VERSION,
            "decision": DECISION_DENY,
            "reason_codes": ["MALFORMED_INPUT"],
            "details": {"missing": missing},
        }

    if snapshot.get("schema") != SCHEMA_VERSION:
        return {"schema": SCHEMA_VERSION, "decision": DECISION_DENY, "reason_codes": ["UNSUPPORTED_SCHEMA"]}
    if snapshot.get("operation") != OPERATION_PROMOTE_CHANGE:
        return {"schema": SCHEMA_VERSION, "decision": DECISION_DENY, "reason_codes": ["UNSUPPORTED_OPERATION"]}

    payload = canonical_action_payload(
        operation=snapshot["operation"],
        subject_ref=snapshot["subject"]["ref"],
        subject_revision=snapshot["subject"]["revision"],
        target_ref=snapshot["target"]["ref"],
        target_revision=snapshot["target"]["revision"],
        policy_ref=snapshot["policy"]["ref"],
        policy_version=snapshot["policy"]["version"],
        evidence_digest=snapshot["evidence_digest"],
    )
    try:
        expected_hash = compute_action_hash(payload)
    except ValueError:
        return {"schema": SCHEMA_VERSION, "decision": DECISION_DENY, "reason_codes": ["MALFORMED_ACTION"]}

    if snapshot.get("action_hash") != expected_hash:
        return {
            "schema": SCHEMA_VERSION,
            "decision": DECISION_DENY,
            "reason_codes": ["ACTION_HASH_MISMATCH"],
            "action_hash": expected_hash,
        }

    stale: List[str] = []
    if snapshot["live"]["subject_revision"] != snapshot["subject"]["revision"]:
        stale.append("SUBJECT_DRIFT")
    if snapshot["live"]["target_revision"] != snapshot["target"]["revision"]:
        stale.append("TARGET_DRIFT")
    if stale:
        return {"schema": SCHEMA_VERSION, "decision": DECISION_STALE, "reason_codes": stale, "action_hash": expected_hash}

    reasons: List[str] = []
    if snapshot["qa"].get("verdict") != "PASS":
        reasons.append("QA_NOT_PASS")
    if snapshot["qa"].get("subject_revision") != snapshot["subject"]["revision"]:
        reasons.append("QA_SUBJECT_MISMATCH")

    if snapshot["integration"].get("verdict") != "PASS":
        reasons.append("INTEGRATION_NOT_PASS")
    if snapshot["integration"].get("subject_revision") != snapshot["subject"]["revision"]:
        reasons.append("INTEGRATION_SUBJECT_MISMATCH")
    if snapshot["integration"].get("target_revision") != snapshot["target"]["revision"]:
        reasons.append("INTEGRATION_TARGET_MISMATCH")

    authorization = snapshot.get("authorization")
    if not isinstance(authorization, dict):
        reasons.append("AUTHORIZATION_MISSING")
    else:
        if authorization.get("verdict") != "ALLOW":
            reasons.append("AUTHORIZATION_NOT_ALLOW")
        if authorization.get("action_hash") != expected_hash:
            reasons.append("AUTHORIZATION_ACTION_MISMATCH")
        if authorization.get("subject_revision") != snapshot["subject"]["revision"]:
            reasons.append("AUTHORIZATION_SUBJECT_MISMATCH")
        if authorization.get("target_revision") != snapshot["target"]["revision"]:
            reasons.append("AUTHORIZATION_TARGET_MISMATCH")
        if authorization.get("target_ref") != snapshot["target"]["ref"]:
            reasons.append("AUTHORIZATION_TARGET_REF_MISMATCH")
        try:
            issued = _parse_time(authorization.get("issued_at"))
            expires = _parse_time(authorization.get("expires_at"))
            if issued > now:
                reasons.append("AUTHORIZATION_NOT_YET_VALID")
            if expires <= now:
                reasons.append("AUTHORIZATION_EXPIRED")
            if expires <= issued:
                reasons.append("AUTHORIZATION_INVALID_WINDOW")
        except (TypeError, ValueError):
            reasons.append("AUTHORIZATION_TIME_INVALID")

    if reasons:
        return {"schema": SCHEMA_VERSION, "decision": DECISION_DENY, "reason_codes": reasons, "action_hash": expected_hash}

    return {
        "schema": SCHEMA_VERSION,
        "decision": DECISION_ALLOW,
        "reason_codes": [],
        "action_hash": expected_hash,
        "subject_revision": snapshot["subject"]["revision"],
        "target_revision": snapshot["target"]["revision"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Portable Final Action Gate evaluator")
    sub = parser.add_subparsers(dest="command", required=True)

    p_hash = sub.add_parser("hash", help="compute v1 action hash")
    p_hash.add_argument("--input", required=True)

    p_eval = sub.add_parser("evaluate", help="evaluate normalized final action snapshot")
    p_eval.add_argument("--input", required=True)
    p_eval.add_argument("--output")

    args = parser.parse_args()
    data = json.loads(Path(args.input).read_text(encoding="utf-8"))

    if args.command == "hash":
        print(compute_action_hash(data))
        return 0

    result = evaluate(data)
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0 if result["decision"] == DECISION_ALLOW else 2


if __name__ == "__main__":
    raise SystemExit(main())
