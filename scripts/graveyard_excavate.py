#!/usr/bin/env python3
"""Безопасный reference handler команды «Раскопать идею».

Скрипт не создаёт GitHub Issue, ADR или TaskContract и не выполняет внешних
side effects. Он только валидирует запрос, готовит GraveyardCandidate,
проводит machine state transition после переданного результата canon-check,
запечатывает GraveyardActivationTicket и проверяет Human Approval.

Production Electron/Rust wiring намеренно отсутствует до разблокировки G3.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from scripts.graveyard_context import (
    REPO_ROOT,
    activation_action_hash,
    build_activation_ticket,
    build_work_provenance,
    confirm_for_normal_workflow,
    create_reactivation_candidate,
    record_canon_check,
)


def _fail(message: str) -> None:
    raise ValueError(message)


def _load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        _fail(f"Ожидался JSON object: {path}")
    return data


def _validate_request(request: dict[str, Any], root: Path) -> None:
    schema = _load_json(root / "schemas" / "v1" / "GraveyardExcavateRequest.json")
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(request), key=lambda e: list(e.path))
    if errors:
        _fail(f"GraveyardExcavateRequest: {errors[0].message}")


def prepare_excavate_request(
    request: dict[str, Any],
    *,
    canon_status: str,
    checked_revision: str,
    ticket_expires_at: str,
    evidence_ref: str | None = None,
    notes: str = "",
    root: Path = REPO_ROOT,
) -> dict[str, Any]:
    """Готовит candidate/ticket без side effect и без Human Approval."""
    _validate_request(request, root)

    candidate = create_reactivation_candidate(
        request["archive_id"],
        request["idea_summary"],
        selector=request.get("selector", ""),
        root=root,
        created_at=request["requested_at"],
    )
    checked = record_canon_check(
        candidate,
        status=canon_status,
        checked_revision=checked_revision,
        evidence_ref=evidence_ref,
        notes=notes,
        root=root,
    )

    if checked["state"] == "BLOCKED_BY_CANON":
        return {
            "status": "BLOCKED_BY_CANON",
            "candidate": checked,
            "activation_ticket": None,
            "approval_action_hash": None,
            "side_effect_performed": False,
        }

    ticket = build_activation_ticket(
        checked,
        task_id=request["task_id"],
        proposed_work=request["proposed_work"],
        issued_at=request["requested_at"],
        expires_at=ticket_expires_at,
        root=root,
    )
    return {
        "status": "AWAITING_OWNER_CONFIRMATION",
        "candidate": checked,
        "activation_ticket": ticket,
        "approval_action_hash": activation_action_hash(ticket, root=root),
        "side_effect_performed": False,
    }


def approve_excavate_request(
    prepared: dict[str, Any],
    *,
    approval_record: dict[str, Any],
    identity: dict[str, Any],
    used_nonces: set[str],
    now: str,
    root: Path = REPO_ROOT,
) -> dict[str, Any]:
    """Проверяет exact Human Approval и возвращает только provenance normal workflow."""
    if prepared.get("status") != "AWAITING_OWNER_CONFIRMATION":
        _fail("Approve разрешён только для подготовленного AWAITING_OWNER_CONFIRMATION bundle")
    candidate = prepared.get("candidate")
    ticket = prepared.get("activation_ticket")
    if not isinstance(candidate, dict) or not isinstance(ticket, dict):
        _fail("Prepared bundle не содержит candidate/activation_ticket")

    approved = confirm_for_normal_workflow(
        candidate,
        activation_ticket=ticket,
        approval_record=approval_record,
        identity=identity,
        used_nonces=used_nonces,
        now=now,
        root=root,
    )
    return {
        "status": "APPROVED_FOR_NORMAL_WORKFLOW",
        "candidate": approved,
        "provenance": build_work_provenance(approved),
        "side_effect_performed": False,
    }


def _write_json(value: dict[str, Any], output: Path | None) -> None:
    text = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if output is None:
        print(text, end="")
    else:
        output.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Reference handler команды «Раскопать идею» без side effects")
    sub = parser.add_subparsers(dest="mode", required=True)

    prepare = sub.add_parser("prepare", help="Подготовить candidate и activation ticket")
    prepare.add_argument("--request", type=Path, required=True)
    prepare.add_argument("--canon-status", required=True)
    prepare.add_argument("--checked-revision", required=True)
    prepare.add_argument("--ticket-expires-at", required=True)
    prepare.add_argument("--evidence-ref")
    prepare.add_argument("--notes", default="")
    prepare.add_argument("--output", type=Path)

    approve = sub.add_parser("approve", help="Проверить ApprovalRecord и вернуть provenance")
    approve.add_argument("--prepared", type=Path, required=True)
    approve.add_argument("--approval", type=Path, required=True)
    approve.add_argument("--identity", type=Path, required=True)
    approve.add_argument("--used-nonces", type=Path, required=True)
    approve.add_argument("--now", required=True)
    approve.add_argument("--output", type=Path)

    args = parser.parse_args()

    if args.mode == "prepare":
        result = prepare_excavate_request(
            _load_json(args.request),
            canon_status=args.canon_status,
            checked_revision=args.checked_revision,
            ticket_expires_at=args.ticket_expires_at,
            evidence_ref=args.evidence_ref,
            notes=args.notes,
        )
        _write_json(result, args.output)
        return 0

    prepared = _load_json(args.prepared)
    approval = _load_json(args.approval)
    identity = _load_json(args.identity)
    nonce_state = _load_json(args.used_nonces)
    nonces = nonce_state.get("used_nonces")
    if not isinstance(nonces, list) or not all(isinstance(x, str) for x in nonces):
        _fail("used-nonces JSON должен содержать массив строк used_nonces")
    used = set(nonces)
    result = approve_excavate_request(
        prepared,
        approval_record=approval,
        identity=identity,
        used_nonces=used,
        now=args.now,
    )
    nonce_state["used_nonces"] = sorted(used)
    args.used_nonces.write_text(json.dumps(nonce_state, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_json(result, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
