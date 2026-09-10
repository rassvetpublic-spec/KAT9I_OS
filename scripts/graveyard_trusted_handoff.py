#!/usr/bin/env python3
"""Trusted production-facing adapter for Graveyard approval handoff.

This module intentionally exposes no caller-controlled clock, replay-store path,
or repository root. It is still a Python adapter, not the future Rust Core
security boundary, but it separates production-facing trust inputs from the
reference/test API in graveyard_excavate.py.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.graveyard_context import REPO_ROOT


def trusted_now_iso() -> str:
    """Read current UTC from the process system clock at the trusted adapter."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def trusted_nonce_state_path() -> Path:
    """Return the one fixed repo-local replay store used by production-facing CLI."""
    return REPO_ROOT / ".kat9i-runtime" / "graveyard-used-nonces.json"


def approve_trusted(
    prepared: dict[str, Any],
    approval_record: dict[str, Any],
    identity: dict[str, Any],
) -> dict[str, Any]:
    """Approve through trusted clock/store inputs without caller injection."""
    # Local import prevents the adapter from becoming a dependency of the
    # reference API during module initialization.
    from scripts.graveyard_excavate import approve_excavate_request_with_nonce_file

    return approve_excavate_request_with_nonce_file(
        prepared,
        approval_record=approval_record,
        identity=identity,
        nonce_state_path=trusted_nonce_state_path(),
        now=trusted_now_iso(),
        root=REPO_ROOT,
    )
