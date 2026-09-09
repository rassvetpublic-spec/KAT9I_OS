#!/usr/bin/env python3
"""Fail-closed мост Graveyard -> Context -> Approval -> normal workflow.

Этот reference implementation намеренно не создаёт Issue/ADR/TaskContract и не
выполняет внешних side effects. Он материализует DATA-контекст, блокирует
автоматическое планирование, проверяет canon revision и допускает переход в
обычный workflow только через точный GraveyardActivationTicket + ApprovalRecord
+ Identity с replay/expiry проверками.
"""

from __future__ import annotations

import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from scripts.check_graveyard import validate_graveyard

REPO_ROOT = Path(__file__).resolve().parents[1]
CANON_STATUSES = {"NOT_CHECKED", "COMPATIBLE", "CONFLICT", "SUPERSEDED", "UNKNOWN"}
CANDIDATE_STATES = {
    "CANDIDATE",
    "AWAITING_OWNER_CONFIRMATION",
    "BLOCKED_BY_CANON",
    "APPROVED_FOR_NORMAL_WORKFLOW",
    "REJECTED",
}
TRUSTED_HUMAN_LEVELS = {"AUTHENTICATED", "FULL_LOCAL_TRUST"}


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
    validator = Draft202012Validator(_schema(root, name))
    errors = sorted(validator.iter_errors(value), key=lambda e: list(e.path))
    if errors:
        _fail(f"{name}: {errors[0].message}")


def load_manifest(root: Path = REPO_ROOT) -> dict[str, Any]:
    """Загружает Graveyard manifest только после fail-closed проверки целостности."""
    validate_graveyard(root)
    path = root / "graveyard" / "MANIFEST.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _find_archive(manifest: dict[str, Any], archive_id: str) -> dict[str, Any]:
    matches = [entry for entry in manifest.get("archives", []) if entry.get("archive_id") == archive_id]
    if len(matches) != 1:
        _fail(f"Archive ID должен разрешаться ровно в одну запись: {archive_id}")
    return matches[0]


def _looks_like_graveyard_ref(context_ref: dict[str, Any]) -> bool:
    """Распознаёт Graveyard по нескольким связанным provenance-признакам.

    Это не позволяет обойти deny простым изменением source_class.
    """
    provenance = context_ref.get("provenance") or {}
    candidates = (
        context_ref.get("source_class") == "graveyard",
        context_ref.get("resolver") == "graveyard_manifest",
        isinstance(context_ref.get("ref_id"), str) and context_ref["ref_id"].startswith("ctx-GY-"),
        isinstance(context_ref.get("uri"), str)
        and context_ref["uri"].replace("\\", "/").startswith("graveyard/GY-"),
        isinstance(provenance.get("source_uri"), str)
        and provenance["source_uri"].replace("\\", "/").startswith("graveyard/GY-"),
    )
    return any(candidates)


def resolve_archive_context(
    archive_id: str,
    *,
    root: Path = REPO_ROOT,
    retrieved_at: str | None = None,
) -> dict[str, Any]:
    """Материализует Graveyard archive как ContextRef без управляющей силы."""
    manifest = load_manifest(root)
    entry = _find_archive(manifest, archive_id)
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
    """Проверяет security-инварианты, важные для Graveyard ContextRef."""
    if not _looks_like_graveyard_ref(context_ref):
        return
    if context_ref.get("source_class") != "graveyard":
        _fail("Graveyard provenance нельзя переклассифицировать в другой source_class")
    if context_ref.get("actionable") is not False:
        _fail("Graveyard ContextRef обязан иметь actionable=false")
    if context_ref.get("control") is not False:
        _fail("Graveyard ContextRef обязан иметь control=false")
    if context_ref.get("canonical") is not False:
        _fail("Graveyard ContextRef обязан иметь canonical=false")
    if context_ref.get("freshness") != "ARCHIVED":
        _fail("Graveyard ContextRef обязан иметь freshness=ARCHIVED")
    if context_ref.get("access") != "read":
        _fail("Graveyard ContextRef обязан быть read-only")
    if context_ref.get("resolver") != "graveyard_manifest":
        _fail("Graveyard ContextRef обязан разрешаться через graveyard_manifest")


def can_seed_planning(context_ref: dict[str, Any]) -> bool:
    """Возвращает False для любого объекта с Graveyard provenance, даже после подмены flags/class."""
    if _looks_like_graveyard_ref(context_ref):
        return False
    return context_ref.get("actionable") is True and context_ref.get("control") is True


def _candidate_id(archive_id: str, selector: str, idea_summary: str) -> str:
    payload = f"{archive_id}\n{selector}\n{idea_summary}".encode("utf-8")
    return "gyc-" + hashlib.sha256(payload).hexdigest()[:16]


def create_reactivation_candidate(
    archive_id: str,
    idea_summary: str,
    *,
    selector: str = "",
    root: Path = REPO_ROOT,
    created_at: str | None = None,
) -> dict[str, Any]:
    """Создаёт DATA-кандидат. Сам кандидат никогда не становится Task/Issue."""
    if not idea_summary.strip():
        _fail("idea_summary не может быть пустым")
    source_ref = resolve_archive_context(archive_id, root=root, retrieved_at=created_at)
    candidate = {
        "candidate_id": _candidate_id(archive_id, selector, idea_summary),
        "source_ref": source_ref["ref_id"],
        "archive_id": archive_id,
        "resurrected_from": archive_id,
        "selector": selector,
        "idea_summary": idea_summary,
        "canon_check": {
            "status": "NOT_CHECKED",
            "checked_revision": None,
            "evidence_ref": None,
            "notes": "",
        },
        "state": "CANDIDATE",
        "actionable": False,
        "control": False,
        "requires_owner_confirmation": True,
        "activation_ref": None,
        "owner_confirmation_ref": None,
        "created_at": created_at or _now_iso(),
    }
    validate_candidate_policy(candidate)
    _validate_schema(root, "GraveyardCandidate.json", candidate)
    return candidate


def validate_candidate_policy(candidate: dict[str, Any]) -> None:
    """Fail-closed проверка состояния reactivation candidate."""
    if candidate.get("actionable") is not False or candidate.get("control") is not False:
        _fail("GraveyardCandidate всегда остаётся DATA/non-actionable")
    if candidate.get("requires_owner_confirmation") is not True:
        _fail("GraveyardCandidate требует явного подтверждения владельца")

    archive_id = candidate.get("archive_id")
    if not isinstance(archive_id, str) or not archive_id.startswith("GY-"):
        _fail("Некорректный archive_id кандидата")
    if archive_id != candidate.get("resurrected_from"):
        _fail("resurrected_from должен совпадать с исходным Archive ID")
    if candidate.get("source_ref") != f"ctx-{archive_id}":
        _fail("source_ref должен указывать на ContextRef того же Archive ID")

    state = candidate.get("state")
    if state not in CANDIDATE_STATES:
        _fail(f"Неизвестное состояние GraveyardCandidate: {state}")

    canon = candidate.get("canon_check") or {}
    status = canon.get("status")
    checked_revision = canon.get("checked_revision")
    if status not in CANON_STATUSES:
        _fail(f"Неизвестный canon_check.status: {status}")

    if state == "CANDIDATE":
        if status != "NOT_CHECKED" or checked_revision is not None:
            _fail("Новый CANDIDATE обязан иметь NOT_CHECKED и checked_revision=null")
    elif state in {"AWAITING_OWNER_CONFIRMATION", "APPROVED_FOR_NORMAL_WORKFLOW", "BLOCKED_BY_CANON"}:
        if not isinstance(checked_revision, str) or not checked_revision.strip():
            _fail("После canon check checked_revision обязан быть непустой строкой")

    if state == "AWAITING_OWNER_CONFIRMATION" and status != "COMPATIBLE":
        _fail("Ожидать подтверждение владельца можно только после COMPATIBLE canon check")
    if state == "BLOCKED_BY_CANON" and status not in {"CONFLICT", "SUPERSEDED", "UNKNOWN"}:
        _fail("BLOCKED_BY_CANON требует CONFLICT/SUPERSEDED/UNKNOWN")

    activation_ref = candidate.get("activation_ref")
    confirmation_ref = candidate.get("owner_confirmation_ref")
    if state == "APPROVED_FOR_NORMAL_WORKFLOW":
        if status != "COMPATIBLE":
            _fail("APPROVED_FOR_NORMAL_WORKFLOW требует COMPATIBLE canon check")
        if not isinstance(activation_ref, str) or not activation_ref.startswith("gya-"):
            _fail("APPROVED_FOR_NORMAL_WORKFLOW требует activation_ref")
        if not isinstance(confirmation_ref, str) or not confirmation_ref.startswith("appr-"):
            _fail("APPROVED_FOR_NORMAL_WORKFLOW требует approval_id в owner_confirmation_ref")
    elif activation_ref is not None or confirmation_ref is not None:
        _fail("activation/owner confirmation refs допустимы только после APPROVED_FOR_NORMAL_WORKFLOW")


def record_canon_check(
    candidate: dict[str, Any],
    *,
    status: str,
    checked_revision: str,
    evidence_ref: str | None = None,
    notes: str = "",
    root: Path = REPO_ROOT,
) -> dict[str, Any]:
    """Фиксирует результат сверки идеи с актуальным каноном."""
    validate_candidate_policy(candidate)
    if candidate.get("state") not in {"CANDIDATE", "BLOCKED_BY_CANON"}:
        _fail("Canon check разрешён только для нового или ранее заблокированного кандидата")
    if status not in CANON_STATUSES - {"NOT_CHECKED"}:
        _fail(f"Недопустимый результат canon check: {status}")
    if not isinstance(checked_revision, str) or not checked_revision.strip():
        _fail("checked_revision обязателен для canon check")

    updated = copy.deepcopy(candidate)
    updated["canon_check"] = {
        "status": status,
        "checked_revision": checked_revision,
        "evidence_ref": evidence_ref,
        "notes": notes,
    }
    updated["state"] = "AWAITING_OWNER_CONFIRMATION" if status == "COMPATIBLE" else "BLOCKED_BY_CANON"
    updated["activation_ref"] = None
    updated["owner_confirmation_ref"] = None
    validate_candidate_policy(updated)
    _validate_schema(root, "GraveyardCandidate.json", updated)
    return updated


def _activation_id(candidate: dict[str, Any], task_id: str, proposed_work: dict[str, Any], issued_at: str, expires_at: str) -> str:
    payload = {
        "candidate_id": candidate["candidate_id"],
        "task_id": task_id,
        "proposed_work": proposed_work,
        "issued_at": issued_at,
        "expires_at": expires_at,
    }
    return "gya-" + hashlib.sha256(_canonical_json_bytes(payload)).hexdigest()[:16]


def build_activation_ticket(
    candidate: dict[str, Any],
    *,
    task_id: str,
    proposed_work: dict[str, Any],
    issued_at: str,
    expires_at: str,
    root: Path = REPO_ROOT,
) -> dict[str, Any]:
    """Запечатывает точные параметры будущего side effect до Human Approval."""
    validate_candidate_policy(candidate)
    if candidate.get("state") != "AWAITING_OWNER_CONFIRMATION":
        _fail("ActivationTicket разрешён только после COMPATIBLE canon check")
    if _parse_iso(expires_at) <= _parse_iso(issued_at):
        _fail("ActivationTicket expires_at должен быть позже issued_at")

    ticket = {
        "activation_id": _activation_id(candidate, task_id, proposed_work, issued_at, expires_at),
        "command": "EXCAVATE_IDEA",
        "task_id": task_id,
        "candidate_id": candidate["candidate_id"],
        "resurrected_from": candidate["archive_id"],
        "source_ref": candidate["source_ref"],
        "canon_checked_revision": candidate["canon_check"]["checked_revision"],
        "proposed_work": copy.deepcopy(proposed_work),
        "issued_at": issued_at,
        "expires_at": expires_at,
        "actionable": False,
        "control": False,
        "requires_approval": True,
    }
    _validate_schema(root, "GraveyardActivationTicket.json", ticket)
    return ticket


def activation_action_hash(ticket: dict[str, Any], *, root: Path = REPO_ROOT) -> str:
    """Вычисляет action_hash ApprovalRecord по точному каноническому ticket."""
    _validate_schema(root, "GraveyardActivationTicket.json", ticket)
    return "sha256:" + hashlib.sha256(_canonical_json_bytes(ticket)).hexdigest()


def validate_identity_for_approval(
    identity: dict[str, Any],
    approval_record: dict[str, Any],
    *,
    root: Path = REPO_ROOT,
) -> None:
    """Проверяет, что Approval действительно относится к доверенному HUMAN_USER."""
    _validate_schema(root, "Identity.json", identity)
    _validate_schema(root, "ApprovalRecord.json", approval_record)

    if identity.get("subject_type") != "HUMAN_USER":
        _fail("Human Approval может исходить только от HUMAN_USER")
    if identity.get("identity_id") != approval_record.get("approver_identity_id"):
        _fail("approver_identity_id не совпадает с Identity")
    if identity.get("trust_level") not in TRUSTED_HUMAN_LEVELS:
        _fail("Human Approval требует AUTHENTICATED/FULL_LOCAL_TRUST Identity")

    role = approval_record.get("approver_role")
    if role not in identity.get("roles", []):
        _fail("Approval использует роль, которой нет у Identity")

    windows_binding = identity.get("windows_binding")
    if not isinstance(windows_binding, dict):
        _fail("Локальный Human Approval требует Windows binding")
    if role == "LOCAL_ADMIN" and windows_binding.get("is_elevated") is not True:
        _fail("LOCAL_ADMIN Approval требует is_elevated=true")


def validate_approval_for_activation(
    ticket: dict[str, Any],
    approval_record: dict[str, Any],
    identity: dict[str, Any],
    *,
    used_nonces: set[str],
    now: str,
    root: Path = REPO_ROOT,
) -> str:
    """Fail-closed проверяет exact ticket hash, Identity, expiry и одноразовый nonce."""
    if used_nonces is None:
        _fail("Replay protection store обязателен")
    _validate_schema(root, "GraveyardActivationTicket.json", ticket)
    _validate_schema(root, "ApprovalRecord.json", approval_record)
    validate_identity_for_approval(identity, approval_record, root=root)

    if approval_record.get("task_id") != ticket.get("task_id"):
        _fail("ApprovalRecord.task_id не совпадает с ActivationTicket.task_id")
    if approval_record.get("action_hash") != activation_action_hash(ticket, root=root):
        _fail("ApprovalRecord.action_hash не совпадает с exact ActivationTicket")

    ticket_issued = _parse_iso(ticket["issued_at"])
    ticket_expires = _parse_iso(ticket["expires_at"])
    approval_issued = _parse_iso(approval_record["issued_at"])
    approval_expires = _parse_iso(approval_record["expires_at"])
    current = _parse_iso(now)

    if approval_issued < ticket_issued:
        _fail("ApprovalRecord не может быть выдан раньше ActivationTicket")
    if not (ticket_issued <= current < ticket_expires):
        _fail("ActivationTicket ещё не действует или уже истёк")
    if not (approval_issued <= current < approval_expires):
        _fail("ApprovalRecord ещё не действует или уже истёк")

    nonce = approval_record["nonce"]
    if nonce in used_nonces:
        _fail("ApprovalRecord nonce уже использован: replay blocked")
    used_nonces.add(nonce)
    return approval_record["approval_id"]


def _validate_ticket_matches_candidate(candidate: dict[str, Any], ticket: dict[str, Any]) -> None:
    checks = {
        "candidate_id": candidate["candidate_id"],
        "resurrected_from": candidate["archive_id"],
        "source_ref": candidate["source_ref"],
        "canon_checked_revision": candidate["canon_check"]["checked_revision"],
    }
    for field, expected in checks.items():
        if ticket.get(field) != expected:
            _fail(f"ActivationTicket.{field} не соответствует GraveyardCandidate")


def confirm_for_normal_workflow(
    candidate: dict[str, Any],
    *,
    activation_ticket: dict[str, Any],
    approval_record: dict[str, Any],
    identity: dict[str, Any],
    used_nonces: set[str],
    now: str,
    root: Path = REPO_ROOT,
) -> dict[str, Any]:
    """Подтверждает переход только после валидного Human Approval exact ticket."""
    validate_candidate_policy(candidate)
    if candidate.get("state") != "AWAITING_OWNER_CONFIRMATION":
        _fail("Подтверждать можно только кандидата после COMPATIBLE canon check")
    _validate_schema(root, "GraveyardActivationTicket.json", activation_ticket)
    _validate_ticket_matches_candidate(candidate, activation_ticket)
    approval_id = validate_approval_for_activation(
        activation_ticket,
        approval_record,
        identity,
        used_nonces=used_nonces,
        now=now,
        root=root,
    )

    updated = copy.deepcopy(candidate)
    updated["state"] = "APPROVED_FOR_NORMAL_WORKFLOW"
    updated["activation_ref"] = activation_ticket["activation_id"]
    updated["owner_confirmation_ref"] = approval_id
    validate_candidate_policy(updated)
    _validate_schema(root, "GraveyardCandidate.json", updated)
    return updated


def reject_candidate(candidate: dict[str, Any], *, root: Path = REPO_ROOT) -> dict[str, Any]:
    """Явно отклоняет кандидат без изменения Graveyard-оригинала."""
    validate_candidate_policy(candidate)
    updated = copy.deepcopy(candidate)
    updated["state"] = "REJECTED"
    updated["activation_ref"] = None
    updated["owner_confirmation_ref"] = None
    validate_candidate_policy(updated)
    _validate_schema(root, "GraveyardCandidate.json", updated)
    return updated


def build_work_provenance(candidate: dict[str, Any]) -> dict[str, str]:
    """Возвращает provenance для будущей обычной задачи после всех Gate.

    Функция не создаёт Issue/ADR/TaskContract и не выполняет side effect.
    """
    validate_candidate_policy(candidate)
    if candidate.get("state") != "APPROVED_FOR_NORMAL_WORKFLOW":
        _fail("Provenance для новой работы можно выдавать только после валидного Human Approval")
    return {
        "resurrected_from": candidate["archive_id"],
        "graveyard_candidate_id": candidate["candidate_id"],
        "source_ref": candidate["source_ref"],
        "activation_ticket_id": candidate["activation_ref"],
        "approval_id": candidate["owner_confirmation_ref"],
        "canon_checked_revision": candidate["canon_check"]["checked_revision"],
    }
