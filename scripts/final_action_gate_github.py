from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from final_action_gate import (
    OPERATION_PROMOTE_CHANGE,
    canonical_action_payload,
    compute_action_hash,
    evaluate,
)

POLICY_REF = "policy:final-action-gate"
POLICY_VERSION = "0.1.0"
FAST_QA_RE = re.compile(r"^FAST-QA-PASS\s*\|.*\bhead=([0-9a-f]{40})\b", re.IGNORECASE)
OWNER_MTD_MARKER = "KAT9I-CONTROL/1 | OWNER-MTD"
QUALITY_CHECK = "Базовые проверки качества и целостности"


def _flatten(value: Any) -> List[Dict[str, Any]]:
    if isinstance(value, dict):
        return [value]
    out: List[Dict[str, Any]] = []
    if isinstance(value, list):
        for item in value:
            out.extend(_flatten(item))
    return out


def _first_line(body: Any) -> str:
    lines = str(body or "").splitlines()
    return lines[0].strip() if lines else ""


def _fields(body: Any) -> Dict[str, str]:
    result: Dict[str, str] = {}
    for raw in str(body or "").splitlines()[1:]:
        line = raw.strip()
        if not line or "=" not in line:
            continue
        key, value = line.split("=", 1)
        result[key.strip()] = value.strip()
    return result


def _owner(comment: Dict[str, Any]) -> bool:
    return str(comment.get("author_association") or "").upper() == "OWNER"


def _stable_digest(value: Dict[str, str]) -> str:
    canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def find_qa_pass(comments: Iterable[Dict[str, Any]], head: str) -> Optional[Dict[str, Any]]:
    matches: List[Dict[str, Any]] = []
    for comment in comments:
        if not _owner(comment):
            continue
        match = FAST_QA_RE.match(_first_line(comment.get("body")))
        if match and match.group(1).lower() == head.lower():
            matches.append(comment)
    if not matches:
        return None
    return max(matches, key=lambda c: (str(c.get("created_at") or ""), int(c.get("id") or 0)))


def quality_pass(check_runs_payload: Any, head: str, target_revision: str) -> Dict[str, Any]:
    payload = check_runs_payload if isinstance(check_runs_payload, dict) else {}
    runs = payload.get("check_runs") or []
    matches = [r for r in runs if r.get("name") == QUALITY_CHECK and r.get("conclusion") == "success"]
    if not matches:
        return {
            "verdict": "BLOCKED",
            "subject_revision": head,
            "target_revision": target_revision,
            "evidence_ref": None,
        }
    selected = max(matches, key=lambda r: (str(r.get("completed_at") or ""), int(r.get("id") or 0)))
    return {
        "verdict": "PASS",
        "subject_revision": head,
        "target_revision": target_revision,
        "evidence_ref": f"github-check:{selected.get('id')}",
    }


def evidence_digest(qa: Optional[Dict[str, Any]], integration: Dict[str, Any]) -> str:
    qa_ref = "none"
    if qa is not None:
        body_digest = hashlib.sha256(str(qa.get("body") or "").encode("utf-8")).hexdigest()
        qa_ref = f"github-comment:{qa.get('id')}:{body_digest}"
    return _stable_digest({
        "integration_evidence_ref": str(integration.get("evidence_ref") or "none"),
        "qa_evidence_ref": qa_ref,
    })


def find_owner_mtd(
    comments: Iterable[Dict[str, Any]],
    *,
    pr_number: int,
    head: str,
    target_ref: str,
    target_revision: str,
    action_hash: str,
    evidence_digest_value: str,
) -> Optional[Dict[str, Any]]:
    matches: List[Dict[str, Any]] = []
    for comment in comments:
        if not _owner(comment) or _first_line(comment.get("body")) != OWNER_MTD_MARKER:
            continue
        fields = _fields(comment.get("body"))
        if fields.get("target_pr") != str(pr_number):
            continue
        if fields.get("exact_head", "").lower() != head.lower():
            continue
        if fields.get("target_ref") != target_ref:
            continue
        if fields.get("target_revision", "").lower() != target_revision.lower():
            continue
        if fields.get("evidence_digest") != evidence_digest_value:
            continue
        if fields.get("action_hash") != action_hash:
            continue
        enriched = dict(comment)
        enriched["fields"] = fields
        matches.append(enriched)
    if not matches:
        return None
    return max(matches, key=lambda c: (str(c.get("created_at") or ""), int(c.get("id") or 0)))


def build_snapshot(pr: Dict[str, Any], comments_payload: Any, check_runs_payload: Any) -> Dict[str, Any]:
    number = int(pr["number"])
    head = str(pr["head"]["sha"])
    target_ref = str(pr["base"]["ref"])
    target_revision = str(pr["base"]["sha"])
    subject_ref = f"pr:{number}"
    comments = _flatten(comments_payload)

    qa = find_qa_pass(comments, head)
    integration = quality_pass(check_runs_payload, head, target_revision)
    evidence_digest_value = evidence_digest(qa, integration)
    payload = canonical_action_payload(
        operation=OPERATION_PROMOTE_CHANGE,
        subject_ref=subject_ref,
        subject_revision=head,
        target_ref=target_ref,
        target_revision=target_revision,
        policy_ref=POLICY_REF,
        policy_version=POLICY_VERSION,
        evidence_digest=evidence_digest_value,
    )
    action_hash = compute_action_hash(payload)
    mtd = find_owner_mtd(
        comments,
        pr_number=number,
        head=head,
        target_ref=target_ref,
        target_revision=target_revision,
        action_hash=action_hash,
        evidence_digest_value=evidence_digest_value,
    )

    authorization = None
    if mtd is not None:
        fields = mtd["fields"]
        issued_at = fields.get("issued_at") or mtd.get("created_at")
        expires_at = fields.get("expires_at")
        if not expires_at and issued_at:
            text = str(issued_at).replace("Z", "+00:00")
            try:
                expires_at = (datetime.fromisoformat(text).astimezone(timezone.utc) + timedelta(hours=12)).isoformat().replace("+00:00", "Z")
            except ValueError:
                expires_at = ""
        authorization = {
            "verdict": "ALLOW",
            "action_hash": action_hash,
            "subject_revision": head,
            "target_ref": target_ref,
            "target_revision": target_revision,
            "issued_at": issued_at,
            "expires_at": expires_at,
            "evidence_ref": f"github-comment:{mtd.get('id')}",
        }

    return {
        "schema": 1,
        "operation": OPERATION_PROMOTE_CHANGE,
        "action_hash": action_hash,
        "evidence_digest": evidence_digest_value,
        "subject": {"ref": subject_ref, "revision": head},
        "target": {"ref": target_ref, "revision": target_revision},
        "live": {"subject_revision": head, "target_revision": target_revision},
        "policy": {"ref": POLICY_REF, "version": POLICY_VERSION},
        "qa": {"verdict": "PASS" if qa else "BLOCKED", "subject_revision": head},
        "integration": integration,
        "authorization": authorization,
        "adapter": {
            "platform": "github",
            "pr_number": number,
            "qa_evidence_ref": f"github-comment:{qa.get('id')}" if qa else None,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="GitHub adapter for Portable Final Action Gate")
    parser.add_argument("--pr", required=True)
    parser.add_argument("--comments", required=True)
    parser.add_argument("--check-runs", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    pr = json.loads(Path(args.pr).read_text(encoding="utf-8"))
    comments = json.loads(Path(args.comments).read_text(encoding="utf-8"))
    checks = json.loads(Path(args.check_runs).read_text(encoding="utf-8"))
    snapshot = build_snapshot(pr, comments, checks)
    decision = evaluate(snapshot)
    result = {"snapshot": snapshot, "gate": decision}
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(decision, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
