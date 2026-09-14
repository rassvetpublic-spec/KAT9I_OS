#!/usr/bin/env python3
"""Проверка машинного контракта Antigravity ONE.

Это CI-оракул для version/hash-bound manifest и байтовых сигнатур.
Windows runtime остаётся в PowerShell.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "bootstrap" / "antigravity-one" / "_System" / "patch-signatures.json"


class ContractError(ValueError):
    pass


def parse_pattern(pattern: str) -> list[int | None]:
    out: list[int | None] = []
    for token in pattern.split():
        if token == "??":
            out.append(None)
            continue
        if len(token) != 2:
            raise ContractError(f"bad hex token: {token!r}")
        try:
            out.append(int(token, 16))
        except ValueError as exc:
            raise ContractError(f"bad hex token: {token!r}") from exc
    if not out:
        raise ContractError("empty pattern")
    return out


def find_offsets(data: bytes, pattern: str) -> list[int]:
    tokens = parse_pattern(pattern)
    if len(tokens) > len(data):
        return []
    result: list[int] = []
    for start in range(0, len(data) - len(tokens) + 1):
        ok = True
        for index, expected in enumerate(tokens):
            if expected is not None and data[start + index] != expected:
                ok = False
                break
        if ok:
            result.append(start)
    return result


def find_unique_across_patterns(data: bytes, patterns: Iterable[str]) -> tuple[str, int] | None:
    hits: list[tuple[str, int]] = []
    for pattern in patterns:
        for offset in find_offsets(data, pattern):
            hits.append((pattern, offset))
    # Deduplicate same offset matched by alternative pattern shapes.
    unique_by_offset: dict[int, str] = {}
    for pattern, offset in hits:
        unique_by_offset.setdefault(offset, pattern)
    if not unique_by_offset:
        return None
    if len(unique_by_offset) != 1:
        raise ContractError(f"signature is ambiguous: offsets={sorted(unique_by_offset)}")
    offset = next(iter(unique_by_offset))
    return unique_by_offset[offset], offset


def classify(data: bytes, signature: dict) -> tuple[str, int | None]:
    patched = find_unique_across_patterns(data, signature["patched_patterns"])
    original = find_unique_across_patterns(data, signature["original_patterns"])
    if patched and original:
        raise ContractError(b"both original and patched signatures found".decode())
    if patched:
        return "PATCHED", patched[1]
    if original:
        return "ORIGINAL", original[1]
    return "UNKNOWN", None


def hex_bytes(value: str) -> bytes:
    try:
        return bytes.fromhex(value)
    except ValueError as exc:
        raise ContractError(f"bad fix_hex: {value!r}") from exc


def apply_patch(data: bytes, signature: dict) -> bytes:
    state, base = classify(data, signature)
    if state != "ORIGINAL" or base is None:
        raise ContractError(f"cannot patch state={state}")
    fix = hex_bytes(signature["fix_hex"])
    offset = base + int(signature.get("write_offset", 0))
    end = offset + len(fix)
    if offset < 0 or end > len(data):
        raise ContractError("patch range outside binary")
    out = bytearray(data)
    out[offset:end] = fix
    verify_state, _ = classify(bytes(out), signature)
    if verify_state != "PATCHED":
        raise ContractError("post-write signature verification failed")
    return bytes(out)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_manifest(path: Path = DEFAULT_MANIFEST) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    validate_manifest(data)
    return data


def validate_manifest(data: dict) -> None:
    if data.get("schema") != 1:
        raise ContractError("manifest schema must be 1")
    signatures = data.get("signatures")
    if not isinstance(signatures, list) or not signatures:
        raise ContractError("manifest must contain signatures")
    seen_ids: set[str] = set()
    for sig in signatures:
        sid = str(sig.get("id", ""))
        if not sid or sid in seen_ids:
            raise ContractError(f"duplicate/empty signature id: {sid!r}")
        seen_ids.add(sid)
        if sig.get("architecture") not in {"x64", "arm64"}:
            raise ContractError(f"unsupported architecture in {sid}")
        for key in ("original_patterns", "patched_patterns"):
            values = sig.get(key)
            if not isinstance(values, list) or not values:
                raise ContractError(f"{sid}.{key} must be non-empty")
            for value in values:
                parse_pattern(value)
        if not hex_bytes(str(sig.get("fix_hex", ""))):
            raise ContractError(f"{sid}.fix_hex empty")

    compatibility = data.get("compatibility")
    if not isinstance(compatibility, list):
        raise ContractError("compatibility must be a list")
    seen_compat: set[tuple[str, str, str]] = set()
    for item in compatibility:
        version = str(item.get("product_version", "")).strip()
        arch = str(item.get("architecture", "")).strip()
        digest = str(item.get("source_sha256", "")).lower().strip()
        sid = str(item.get("signature_id", "")).strip()
        if not version or arch not in {"x64", "arm64"}:
            raise ContractError("compatibility requires product_version + architecture")
        if sid not in seen_ids:
            raise ContractError(f"compatibility references unknown signature_id={sid!r}")
        if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise ContractError(f"bad source_sha256 for {version}/{arch}")
        key = (version, arch, digest)
        if key in seen_compat:
            raise ContractError(f"duplicate compatibility row: {key}")
        seen_compat.add(key)
        patched = str(item.get("patched_sha256", "")).lower().strip()
        if patched and (len(patched) != 64 or any(c not in "0123456789abcdef" for c in patched)):
            raise ContractError(f"bad patched_sha256 for {version}/{arch}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    manifest = load_manifest(args.manifest)
    if args.check:
        print(
            f"OK schema={manifest['schema']} signatures={len(manifest['signatures'])} "
            f"compatibility={len(manifest['compatibility'])}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
