#!/usr/bin/env python3
"""Минимальный fail-closed мост Graveyard -> Context -> normal workflow.

Модуль намеренно НЕ создаёт Issue/TaskContract и не повышает Graveyard DATA до CONTROL.
Он только:
- материализует структурированный ContextRef;
- не допускает использование Graveyard как seed для планирования;
- создаёт неисполняемый GraveyardCandidate;
- фиксирует сверку с текущим каноном;
- после явного подтверждения владельца выдаёт только provenance для обычного workflow.
"""

from __future__ import annotations

import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.check_graveyard import validate_graveyard

REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPO_ROOT / "graveyard" / "MANIFEST.json"
CANON_STATUSES = {"NOT_CHECKED", "COMPATIBLE", "CONFLICT", "SUPERSEDED", "UNKNOWN"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _fail(message: str) -> None:
    raise ValueError(message)


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
    return ref


def validate_context_ref_policy(context_ref: dict[str, Any]) -> None:
    """Проверяет security-инварианты, важные для Graveyard ContextRef."""
    if context_ref.get("source_class") == "graveyard":
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


def can_seed_planning(context_ref: dict[str, Any]) -> bool:
    """Можно ли использовать источник как основание для автоматического создания работы.

    Graveyard всегда возвращает False, даже если входные DATA пытаются подделать флаги.
    """
    if context_ref.get("source_class") == "graveyard":
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
        "owner_confirmation_ref": None,
        "created_at": created_at or _now_iso(),
    }
    validate_candidate_policy(candidate)
    return candidate


def validate_candidate_policy(candidate: dict[str, Any]) -> None:
    """Fail-closed проверка состояния reactivation candidate."""
    if candidate.get("actionable") is not False or candidate.get("control") is not False:
        _fail("GraveyardCandidate всегда остаётся DATA/non-actionable")
    if candidate.get("requires_owner_confirmation") is not True:
        _fail("GraveyardCandidate требует явного подтверждения владельца")
    if candidate.get("archive_id") != candidate.get("resurrected_from"):
        _fail("resurrected_from должен совпадать с исходным Archive ID")

    state = candidate.get("state")
    canon = candidate.get("canon_check") or {}
    status = canon.get("status")
    if status not in CANON_STATUSES:
        _fail(f"Неизвестный canon_check.status: {status}")

    if state == "AWAITING_OWNER_CONFIRMATION" and status != "COMPATIBLE":
        _fail("Ожидать подтверждение владельца можно только после COMPATIBLE canon check")
    if state == "APPROVED_FOR_NORMAL_WORKFLOW":
        if status != "COMPATIBLE":
            _fail("APPROVED_FOR_NORMAL_WORKFLOW требует COMPATIBLE canon check")
        if not candidate.get("owner_confirmation_ref"):
            _fail("APPROVED_FOR_NORMAL_WORKFLOW требует owner_confirmation_ref")
    if state == "BLOCKED_BY_CANON" and status not in {"CONFLICT", "SUPERSEDED", "UNKNOWN"}:
        _fail("BLOCKED_BY_CANON требует CONFLICT/SUPERSEDED/UNKNOWN")


def record_canon_check(
    candidate: dict[str, Any],
    *,
    status: str,
    checked_revision: str,
    evidence_ref: str | None = None,
    notes: str = "",
) -> dict[str, Any]:
    """Фиксирует результат сверки идеи с актуальным каноном."""
    validate_candidate_policy(candidate)
    if candidate.get("state") not in {"CANDIDATE", "BLOCKED_BY_CANON"}:
        _fail("Canon check разрешён только для нового или ранее заблокированного кандидата")
    if status not in CANON_STATUSES - {"NOT_CHECKED"}:
        _fail(f"Недопустимый результат canon check: {status}")
    if not checked_revision.strip():
        _fail("checked_revision обязателен для canon check")

    updated = copy.deepcopy(candidate)
    updated["canon_check"] = {
        "status": status,
        "checked_revision": checked_revision,
        "evidence_ref": evidence_ref,
        "notes": notes,
    }
    updated["state"] = "AWAITING_OWNER_CONFIRMATION" if status == "COMPATIBLE" else "BLOCKED_BY_CANON"
    updated["owner_confirmation_ref"] = None
    validate_candidate_policy(updated)
    return updated


def confirm_for_normal_workflow(candidate: dict[str, Any], *, confirmation_ref: str) -> dict[str, Any]:
    """Фиксирует явное подтверждение владельца, но НЕ создаёт Task/Issue автоматически."""
    validate_candidate_policy(candidate)
    if candidate.get("state") != "AWAITING_OWNER_CONFIRMATION":
        _fail("Подтверждать можно только кандидата после COMPATIBLE canon check")
    if not confirmation_ref.strip():
        _fail("confirmation_ref обязателен")

    updated = copy.deepcopy(candidate)
    updated["state"] = "APPROVED_FOR_NORMAL_WORKFLOW"
    updated["owner_confirmation_ref"] = confirmation_ref
    validate_candidate_policy(updated)
    return updated


def reject_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    """Явно отклоняет кандидат без изменения Graveyard-оригинала."""
    validate_candidate_policy(candidate)
    updated = copy.deepcopy(candidate)
    updated["state"] = "REJECTED"
    updated["owner_confirmation_ref"] = None
    validate_candidate_policy(updated)
    return updated


def build_work_provenance(candidate: dict[str, Any]) -> dict[str, str]:
    """Возвращает provenance для будущей обычной задачи после всех Gate.

    Эта функция не создаёт TaskContract/Issue. Она только формирует ссылку происхождения.
    """
    validate_candidate_policy(candidate)
    if candidate.get("state") != "APPROVED_FOR_NORMAL_WORKFLOW":
        _fail("Provenance для новой работы можно выдавать только после явного подтверждения владельца")
    return {
        "resurrected_from": candidate["archive_id"],
        "graveyard_candidate_id": candidate["candidate_id"],
        "source_ref": candidate["source_ref"],
        "owner_confirmation_ref": candidate["owner_confirmation_ref"],
        "canon_checked_revision": candidate["canon_check"]["checked_revision"],
    }
