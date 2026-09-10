#!/usr/bin/env python3
"""Безопасный reference handler команды «Раскопать идею».

No GitHub Issue/ADR/TaskContract side effects. Production Electron/Rust wiring is
still gated by G3. Production-facing CLI approval crosses a dedicated trusted
boundary: caller cannot inject current time or replay-store path; system UTC,
fixed replay state, cross-process locking and atomic persistence are used.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

_REPO_ROOT_FOR_IMPORT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT_FOR_IMPORT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT_FOR_IMPORT))

from scripts.graveyard_context import (
    REPO_ROOT,
    activation_action_hash,
    build_activation_ticket,
    confirm_for_normal_workflow,
    create_reactivation_candidate,
    record_canon_check,
    verified_work_provenance,
)


def _fail(message: str) -> None:
    raise ValueError(message)


def _trusted_now_iso() -> str:
    """Trusted CLI boundary: current time comes only from system UTC clock."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _trusted_nonce_state_path(root: Path = REPO_ROOT) -> Path:
    """Trusted CLI boundary uses one fixed replay store; CLI cannot redirect it."""
    return root / ".kat9i-runtime" / "graveyard-used-nonces.json"


def _load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        _fail(f"Ожидался JSON object: {path}")
    return data


def _validate_request(request: dict[str, Any], root: Path) -> None:
    schema = _load_json(root / "schemas" / "v1" / "GraveyardExcavateRequest.json")
    errors = sorted(Draft202012Validator(schema).iter_errors(request), key=lambda e: list(e.path))
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
    """Reference/test helper. Production-facing callers must use the CLI boundary."""
    if prepared.get("status") != "AWAITING_OWNER_CONFIRMATION":
        _fail("Approve разрешён только для AWAITING_OWNER_CONFIRMATION bundle")
    candidate = prepared.get("candidate")
    ticket = prepared.get("activation_ticket")
    if not isinstance(candidate, dict) or not isinstance(ticket, dict):
        _fail("Prepared bundle не содержит candidate/activation_ticket")

    outcome = confirm_for_normal_workflow(
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
        "candidate": outcome.candidate,
        "provenance": verified_work_provenance(outcome, used_nonces=used_nonces, now=now, root=root),
        "side_effect_performed": False,
    }


def _nonce_state_to_set(state: dict[str, Any]) -> set[str]:
    nonces = state.get("used_nonces")
    if not isinstance(nonces, list) or not all(isinstance(x, str) for x in nonces):
        _fail("used-nonces JSON должен содержать массив строк used_nonces")
    return set(nonces)


def _acquire_lock(lock_path: Path, *, attempts: int = 200, delay: float = 0.01) -> int:
    """Acquire fail-closed cross-process lock using atomic O_EXCL creation."""
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    for _ in range(attempts):
        try:
            fd = os.open(lock_path, flags, 0o600)
            os.write(fd, str(os.getpid()).encode("ascii"))
            return fd
        except FileExistsError:
            time.sleep(delay)
    _fail(f"Не удалось получить replay lock: {lock_path}")


def _atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    text = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    try:
        with tmp.open("w", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


def approve_excavate_request_with_nonce_file(
    prepared: dict[str, Any],
    *,
    approval_record: dict[str, Any],
    identity: dict[str, Any],
    nonce_state_path: Path,
    now: str,
    root: Path = REPO_ROOT,
) -> dict[str, Any]:
    """Reference/test helper that serializes replay check+consume+persist."""
    parent = nonce_state_path.parent
    parent.mkdir(parents=True, exist_ok=True)
    if parent.is_symlink() or nonce_state_path.is_symlink():
        _fail("Replay store не может быть symlink")
    lock_path = nonce_state_path.with_name(nonce_state_path.name + ".lock")
    lock_fd = _acquire_lock(lock_path)
    try:
        if nonce_state_path.exists():
            state = _load_json(nonce_state_path)
        else:
            state = {"used_nonces": []}
        used = _nonce_state_to_set(state)
        result = approve_excavate_request(
            prepared,
            approval_record=approval_record,
            identity=identity,
            used_nonces=used,
            now=now,
            root=root,
        )
        state["used_nonces"] = sorted(used)
        _atomic_write_json(nonce_state_path, state)
        return result
    finally:
        os.close(lock_fd)
        try:
            lock_path.unlink()
        except FileNotFoundError:
            pass


def _approve_via_trusted_cli_boundary(
    prepared: dict[str, Any],
    approval_record: dict[str, Any],
    identity: dict[str, Any],
) -> dict[str, Any]:
    """Production-facing handoff: no caller-supplied clock or replay-store path."""
    return approve_excavate_request_with_nonce_file(
        prepared,
        approval_record=approval_record,
        identity=identity,
        nonce_state_path=_trusted_nonce_state_path(),
        now=_trusted_now_iso(),
        root=REPO_ROOT,
    )


def _write_json(value: dict[str, Any], output: Path | None) -> None:
    text = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if output is None:
        print(text, end="")
    else:
        output.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Reference handler «Раскопать идею» без side effects")
    sub = parser.add_subparsers(dest="mode", required=True)

    prepare = sub.add_parser("prepare", help="Подготовить candidate и exact activation ticket")
    prepare.add_argument("--request", type=Path, required=True)
    prepare.add_argument("--canon-status", required=True)
    prepare.add_argument("--checked-revision", required=True)
    prepare.add_argument("--ticket-expires-at", required=True)
    prepare.add_argument("--evidence-ref")
    prepare.add_argument("--notes", default="")
    prepare.add_argument("--output", type=Path)

    approve = sub.add_parser("approve", help="Проверить ApprovalRecord и атомарно потребить nonce")
    approve.add_argument("--prepared", type=Path, required=True)
    approve.add_argument("--approval", type=Path, required=True)
    approve.add_argument("--identity", type=Path, required=True)
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

    result = _approve_via_trusted_cli_boundary(
        _load_json(args.prepared),
        _load_json(args.approval),
        _load_json(args.identity),
    )
    _write_json(result, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
