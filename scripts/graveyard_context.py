#!/usr/bin/env python3
"""Fail-closed Graveyard -> Context -> Approval -> normal workflow bridge.

Reference implementation only. Graveyard remains DATA; no Issue/ADR/TaskContract
side effects are performed here.
"""

from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from scripts.check_graveyard import validate_graveyard

REPO_ROOT = Path(__file__).resolve().parents[1]
CANON_STATUSES = {"NOT_CHECKED", "COMPATIBLE", "CONFLICT", "SUPERSEDED", "UNKNOWN"}
CANDIDATE_STATES = {
    "CANDIDATE", "AWAITING_OWNER_CONFIRMATION", "BLOCKED_BY_CANON",
    "APPROVED_FOR_NORMAL_WORKFLOW", "REJECTED",
}
TRUSTED_HUMAN_LEVELS = {"AUTHENTICATED", "FULL_LOCAL_TRUST"}
_APPROVAL_SEAL = object()


@dataclass(frozen=True)
class _VerifiedApprovalOutcome:
    candidate: dict[str, Any]
    activation_ticket: dict[str, Any]
    approval_record: dict[str, Any]
    identity: dict[str, Any]
    seal: object


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _fail(message: str) -> None:
    raise ValueError(message)


def _parse_iso(value: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        _fail("Ожидалась непустая ISO 8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"Некорректная ISO 8601 timestamp: {value}") from exc
    if parsed.tzinfo is None:
        _fail("Timestamp обязан содержать timezone")
    return parsed.astimezone(timezone.utc)


def _canonical_json_bytes(value: dict[str, Any]) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _schema(root: Path, name: str) -> dict[str, Any]:
    return json.loads((root / "schemas" / "v1" / name).read_text(encoding="utf-8"))


def _validate_schema(root: Path, name: str, value: dict[str, Any]) -> None:
    errors = sorted(Draft202012Validator(_schema(root, name)).iter_errors(value), key=lambda e: list(e.path))
    if errors:
        _fail(f"{name}: {errors[0].message}")


def load_manifest(root: Path = REPO_ROOT) -> dict[str, Any]:
    validate_graveyard(root)
    return json.loads((root / "graveyard" / "MANIFEST.json").read_text(encoding="utf-8"))


def _find_archive(manifest: dict[str, Any], archive_id: str) -> dict[str, Any]:
    matches = [entry for entry in manifest.get("archives", []) if entry.get("archive_id") == archive_id]
    if len(matches) != 1:
        _fail(f"Archive ID должен разрешаться ровно в одну manifest-запись: {archive_id}")
    return matches[0]


def _looks_like_graveyard_ref(context_ref: dict[str, Any]) -> bool:
    provenance = context_ref.get("provenance") or {}
    return any((
        context_ref.get("source_class") == "graveyard",
        context_ref.get("resolver") == "graveyard_manifest",
        isinstance(context_ref.get("ref_id"), str) and context_ref["ref_id"].startswith("ctx-GY-"),
        isinstance(context_ref.get("uri"), str) and context_ref["uri"].replace("\\", "/").startswith("graveyard/GY-"),
        isinstance(provenance.get("source_uri"), str) and provenance["source_uri"].replace("\\", "/").startswith("graveyard/GY-"),
    ))


def resolve_archive_context(archive_id: str, *, root: Path = REPO_ROOT, retrieved_at: str | None = None) -> dict[str, Any]:
    entry = _find_archive(load_manifest(root), archive_id)
    ref = {
        "ref_id": f"ctx-{archive_id}",
        "uri": entry["path"],
        "source_class": "graveyard",
        "revision": entry["sha256"],
        "scope": "historical_context_only",
        "access": "read",
        "trust_level": "PROVISIONAL",
        "freshness": "ARCHIVED",
        "resolver": "graveyard_manifest",
        "actionable": False,
        "control": False,
        "canonical": False,
        "provenance": {
            "source_uri": entry["path"],
            "source_revision": entry["sha256"],
            "retrieved_at": retrieved_at or _now_iso(),
            "transformation": "none",
        },
    }
    validate_context_ref_policy(ref)
    _validate_schema(root, "ContextRef.json", ref)
    return ref


def validate_context_ref_policy(context_ref: dict[str, Any]) -> None:
    if not _looks_like_graveyard_ref(context_ref):
        return
    expected = {
        "source_class": "graveyard", "actionable": False, "control": False,
        "canonical": False, "freshness": "ARCHIVED", "access": "read",
        "resolver": "graveyard_manifest",
    }
    for field, value in expected.items():
        if context_ref.get(field) != value:
            _fail(f"Graveyard ContextRef: недопустимое {field}={context_ref.get(field)!r}")


def can_seed_planning(context_ref: dict[str, Any]) -> bool:
    if _looks_like_graveyard_ref(context_ref):
        return False
    return context_ref.get("actionable") is True and context_ref.get("control") is True


def _candidate_id(archive_id: str, selector: str, idea_summary: str) -> str:
    return "gyc-" + hashlib.sha256(f"{archive_id}\n{selector}\n{idea_summary}".encode("utf-8")).hexdigest()[:16]


def _validate_candidate_origin(candidate: dict[str, Any], *, root: Path) -> None:
    archive_id = candidate.get("archive_id")
    if not isinstance(archive_id, str) or not archive_id.startswith("GY-"):
        _fail("Некорректный archive_id кандидата")
    _find_archive(load_manifest(root), archive_id)
    selector = candidate.get("selector", "")
    idea_summary = candidate.get("idea_summary")
    if not isinstance(selector, str) or not isinstance(idea_summary, str) or not idea_summary.strip():
        _fail("Кандидат обязан содержать selector и непустой idea_summary")
    if candidate.get("candidate_id") != _candidate_id(archive_id, selector, idea_summary):
        _fail("candidate_id не соответствует Archive ID/selector/idea_summary")
    if candidate.get("resurrected_from") != archive_id:
        _fail("resurrected_from должен совпадать с Archive ID")
    if candidate.get("source_ref") != f"ctx-{archive_id}":
        _fail("source_ref должен соответствовать тому же Archive ID")


def create_reactivation_candidate(
    archive_id: str,
    idea_summary: str,
    *,
    selector: str = "",
    root: Path = REPO_ROOT,
    created_at: str | None = None,
) -> dict[str, Any]:
    if not idea_summary.strip():
        _fail("idea_summary не может быть пустым")
    source_ref = resolve_archive_context(archive_id, root=root, retrieved_at=created_at)
    candidate = {
        "candidate_id": _candidate_id(archive_id, selector, idea_summary),
        "source_ref": source_ref["ref_id"], "archive_id": archive_id,
        "resurrected_from": archive_id, "selector": selector, "idea_summary": idea_summary,
        "canon_check": {"status": "NOT_CHECKED", "checked_revision": None, "evidence_ref": None, "notes": ""},
        "state": "CANDIDATE", "actionable": False, "control": False,
        "requires_owner_confirmation": True, "activation_ref": None,
        "owner_confirmation_ref": None, "created_at": created_at or _now_iso(),
    }
    validate_candidate_policy(candidate, root=root)
    _validate_schema(root, "GraveyardCandidate.json", candidate)
    return candidate


def validate_candidate_policy(candidate: dict[str, Any], *, root: Path = REPO_ROOT) -> None:
    if candidate.get("actionable") is not False or candidate.get("control") is not False:
        _fail("GraveyardCandidate всегда остаётся DATA/non-actionable")
    if candidate.get("requires_owner_confirmation") is not True:
        _fail("GraveyardCandidate требует Human Approval")
    _validate_candidate_origin(candidate, root=root)

    state = candidate.get("state")
    if state not in CANDIDATE_STATES:
        _fail(f"Неизвестное состояние GraveyardCandidate: {state}")
    canon = candidate.get("canon_check") or {}
    status, revision = canon.get("status"), canon.get("checked_revision")
    if status not in CANON_STATUSES:
        _fail(f"Неизвестный canon_check.status: {status}")
    if status == "NOT_CHECKED":
        if revision is not None:
            _fail("NOT_CHECKED требует checked_revision=null")
    elif not isinstance(revision, str) or not revision.strip():
        _fail("Любой завершённый canon-check требует непустую checked_revision")

    if state == "CANDIDATE" and status != "NOT_CHECKED":
        _fail("CANDIDATE обязан иметь NOT_CHECKED")
    if state in {"AWAITING_OWNER_CONFIRMATION", "APPROVED_FOR_NORMAL_WORKFLOW"} and status != "COMPATIBLE":
        _fail(f"{state} требует COMPATIBLE")
    if state == "BLOCKED_BY_CANON" and status not in {"CONFLICT", "SUPERSEDED", "UNKNOWN"}:
        _fail("BLOCKED_BY_CANON требует CONFLICT/SUPERSEDED/UNKNOWN")

    activation_ref, approval_ref = candidate.get("activation_ref"), candidate.get("owner_confirmation_ref")
    if state == "APPROVED_FOR_NORMAL_WORKFLOW":
        if not isinstance(activation_ref, str) or not activation_ref.startswith("gya-"):
            _fail("Approved candidate требует activation_ref")
        if not isinstance(approval_ref, str) or not approval_ref.startswith("appr-"):
            _fail("Approved candidate требует approval_id")
    elif activation_ref is not None or approval_ref is not None:
        _fail("activation/approval refs допустимы только после Approval")


def record_canon_check(
    candidate: dict[str, Any], *, status: str, checked_revision: str,
    evidence_ref: str | None = None, notes: str = "", root: Path = REPO_ROOT,
) -> dict[str, Any]:
    validate_candidate_policy(candidate, root=root)
    if candidate.get("state") not in {"CANDIDATE", "BLOCKED_BY_CANON"}:
        _fail("Canon check разрешён только для нового/заблокированного кандидата")
    if status not in CANON_STATUSES - {"NOT_CHECKED"}:
        _fail(f"Недопустимый canon status: {status}")
    if not isinstance(checked_revision, str) or not checked_revision.strip():
        _fail("checked_revision обязателен")
    updated = copy.deepcopy(candidate)
    updated["canon_check"] = {
        "status": status, "checked_revision": checked_revision,
        "evidence_ref": evidence_ref, "notes": notes,
    }
    updated["state"] = "AWAITING_OWNER_CONFIRMATION" if status == "COMPATIBLE" else "BLOCKED_BY_CANON"
    updated["activation_ref"] = updated["owner_confirmation_ref"] = None
    validate_candidate_policy(updated, root=root)
    _validate_schema(root, "GraveyardCandidate.json", updated)
    return updated


def _activation_id(candidate: dict[str, Any], task_id: str, proposed_work: dict[str, Any], issued_at: str, expires_at: str) -> str:
    payload = {"candidate_id": candidate["candidate_id"], "task_id": task_id, "proposed_work": proposed_work,
               "issued_at": issued_at, "expires_at": expires_at}
    return "gya-" + hashlib.sha256(_canonical_json_bytes(payload)).hexdigest()[:16]


def build_activation_ticket(
    candidate: dict[str, Any], *, task_id: str, proposed_work: dict[str, Any],
    issued_at: str, expires_at: str, root: Path = REPO_ROOT,
) -> dict[str, Any]:
    validate_candidate_policy(candidate, root=root)
    if candidate.get("state") != "AWAITING_OWNER_CONFIRMATION":
        _fail("ActivationTicket разрешён только после COMPATIBLE canon check")
    if _parse_iso(expires_at) <= _parse_iso(issued_at):
        _fail("ActivationTicket expires_at должен быть позже issued_at")
    ticket = {
        "activation_id": _activation_id(candidate, task_id, proposed_work, issued_at, expires_at),
        "command": "EXCAVATE_IDEA", "task_id": task_id, "candidate_id": candidate["candidate_id"],
        "resurrected_from": candidate["archive_id"], "source_ref": candidate["source_ref"],
        "canon_checked_revision": candidate["canon_check"]["checked_revision"],
        "proposed_work": copy.deepcopy(proposed_work), "issued_at": issued_at, "expires_at": expires_at,
        "actionable": False, "control": False, "requires_approval": True,
    }
    _validate_schema(root, "GraveyardActivationTicket.json", ticket)
    return ticket


def activation_action_hash(ticket: dict[str, Any], *, root: Path = REPO_ROOT) -> str:
    _validate_schema(root, "GraveyardActivationTicket.json", ticket)
    return "sha256:" + hashlib.sha256(_canonical_json_bytes(ticket)).hexdigest()


def validate_identity_for_approval(identity: dict[str, Any], approval: dict[str, Any], *, root: Path = REPO_ROOT) -> None:
    _validate_schema(root, "Identity.json", identity)
    _validate_schema(root, "ApprovalRecord.json", approval)
    if identity.get("subject_type") != "HUMAN_USER":
        _fail("Human Approval может исходить только от HUMAN_USER")
    if identity.get("identity_id") != approval.get("approver_identity_id"):
        _fail("approver_identity_id не совпадает с Identity")
    if identity.get("trust_level") not in TRUSTED_HUMAN_LEVELS:
        _fail("Human Approval требует AUTHENTICATED/FULL_LOCAL_TRUST")
    role = approval.get("approver_role")
    if role not in identity.get("roles", []):
        _fail("Approval использует отсутствующую роль")
    binding = identity.get("windows_binding")
    if not isinstance(binding, dict):
        _fail("Human Approval требует Windows binding")
    if role == "LOCAL_ADMIN" and binding.get("is_elevated") is not True:
        _fail("LOCAL_ADMIN Approval требует elevation")


def validate_approval_for_activation(
    ticket: dict[str, Any], approval: dict[str, Any], identity: dict[str, Any], *,
    used_nonces: set[str], now: str, root: Path = REPO_ROOT,
) -> str:
    if used_nonces is None:
        _fail("Replay protection store обязателен")
    _validate_schema(root, "GraveyardActivationTicket.json", ticket)
    _validate_schema(root, "ApprovalRecord.json", approval)
    validate_identity_for_approval(identity, approval, root=root)
    if approval.get("task_id") != ticket.get("task_id"):
        _fail("ApprovalRecord.task_id не совпадает с ticket")
    if approval.get("action_hash") != activation_action_hash(ticket, root=root):
        _fail("ApprovalRecord.action_hash не совпадает с exact ticket")
    ticket_issued, ticket_expires = _parse_iso(ticket["issued_at"]), _parse_iso(ticket["expires_at"])
    approval_issued, approval_expires, current = _parse_iso(approval["issued_at"]), _parse_iso(approval["expires_at"]), _parse_iso(now)
    if approval_issued < ticket_issued:
        _fail("ApprovalRecord выдан раньше ticket")
    if not (ticket_issued <= current < ticket_expires):
        _fail("ActivationTicket ещё не действует или истёк")
    if not (approval_issued <= current < approval_expires):
        _fail("ApprovalRecord ещё не действует или истёк")
    nonce = approval["nonce"]
    if nonce in used_nonces:
        _fail("ApprovalRecord nonce уже использован: replay blocked")
    used_nonces.add(nonce)
    return approval["approval_id"]


def _validate_ticket_matches_candidate(candidate: dict[str, Any], ticket: dict[str, Any]) -> None:
    expected = {
        "candidate_id": candidate["candidate_id"], "resurrected_from": candidate["archive_id"],
        "source_ref": candidate["source_ref"], "canon_checked_revision": candidate["canon_check"]["checked_revision"],
    }
    for field, value in expected.items():
        if ticket.get(field) != value:
            _fail(f"ActivationTicket.{field} не соответствует candidate")


def confirm_for_normal_workflow(
    candidate: dict[str, Any], *, activation_ticket: dict[str, Any], approval_record: dict[str, Any],
    identity: dict[str, Any], used_nonces: set[str], now: str, root: Path = REPO_ROOT,
) -> _VerifiedApprovalOutcome:
    validate_candidate_policy(candidate, root=root)
    if candidate.get("state") != "AWAITING_OWNER_CONFIRMATION":
        _fail("Подтверждать можно только AWAITING_OWNER_CONFIRMATION")
    _validate_schema(root, "GraveyardActivationTicket.json", activation_ticket)
    _validate_ticket_matches_candidate(candidate, activation_ticket)
    approval_id = validate_approval_for_activation(
        activation_ticket, approval_record, identity, used_nonces=used_nonces, now=now, root=root
    )
    updated = copy.deepcopy(candidate)
    updated["state"] = "APPROVED_FOR_NORMAL_WORKFLOW"
    updated["activation_ref"] = activation_ticket["activation_id"]
    updated["owner_confirmation_ref"] = approval_id
    validate_candidate_policy(updated, root=root)
    _validate_schema(root, "GraveyardCandidate.json", updated)
    return _VerifiedApprovalOutcome(
        candidate=updated,
        activation_ticket=copy.deepcopy(activation_ticket),
        approval_record=copy.deepcopy(approval_record),
        identity=copy.deepcopy(identity),
        seal=_APPROVAL_SEAL,
    )


def reject_candidate(candidate: dict[str, Any], *, root: Path = REPO_ROOT) -> dict[str, Any]:
    validate_candidate_policy(candidate, root=root)
    updated = copy.deepcopy(candidate)
    updated["state"] = "REJECTED"
    updated["activation_ref"] = updated["owner_confirmation_ref"] = None
    validate_candidate_policy(updated, root=root)
    _validate_schema(root, "GraveyardCandidate.json", updated)
    return updated


def verified_work_provenance(outcome: _VerifiedApprovalOutcome, *, root: Path = REPO_ROOT) -> dict[str, str]:
    """Build provenance only from an outcome sealed by confirm_for_normal_workflow."""
    if not isinstance(outcome, _VerifiedApprovalOutcome) or outcome.seal is not _APPROVAL_SEAL:
        _fail("Provenance требует внутренний verified Approval outcome")
    candidate, ticket, approval = outcome.candidate, outcome.activation_ticket, outcome.approval_record
    validate_candidate_policy(candidate, root=root)
    _validate_schema(root, "GraveyardActivationTicket.json", ticket)
    _validate_schema(root, "ApprovalRecord.json", approval)
    validate_identity_for_approval(outcome.identity, approval, root=root)
    _validate_ticket_matches_candidate(candidate, ticket)
    if candidate.get("state") != "APPROVED_FOR_NORMAL_WORKFLOW":
        _fail("Verified outcome содержит не-approved candidate")
    if candidate.get("activation_ref") != ticket.get("activation_id"):
        _fail("activation_ref не совпадает с ticket")
    if candidate.get("owner_confirmation_ref") != approval.get("approval_id"):
        _fail("approval ref не совпадает с ApprovalRecord")
    if approval.get("task_id") != ticket.get("task_id") or approval.get("action_hash") != activation_action_hash(ticket, root=root):
        _fail("Verified outcome потерял exact Approval binding")
    return {
        "resurrected_from": candidate["archive_id"],
        "graveyard_candidate_id": candidate["candidate_id"],
        "source_ref": candidate["source_ref"],
        "activation_ticket_id": ticket["activation_id"],
        "approval_id": approval["approval_id"],
        "canon_checked_revision": candidate["canon_check"]["checked_revision"],
    }
