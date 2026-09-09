#!/usr/bin/env python3
"""Fail-closed checks for the non-actionable Graveyard data layer."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path

MARKER = "# GRAVEYARD / DATA ONLY / NON-CANONICAL / NON-ACTIONABLE / NO AUTO-PROMOTION"
FALSE_POLICY_FIELDS = ("actionable", "control", "canonical", "auto_promotion", "ssot")
CANONICAL_SUFFIXES = {".md", ".json", ".yml", ".yaml", ".toml"}


def _git_blob_sha1(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def _fail(message: str) -> None:
    raise ValueError(message)


def validate_graveyard(root: Path) -> None:
    graveyard = root / "graveyard"
    manifest_path = graveyard / "MANIFEST.json"
    readme_path = graveyard / "README.md"

    if not readme_path.is_file():
        _fail("Отсутствует graveyard/README.md")
    if not manifest_path.is_file():
        _fail("Отсутствует graveyard/MANIFEST.json")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != "1.0":
        _fail("Неизвестная schema_version Graveyard manifest")
    if manifest.get("source_class") != "graveyard":
        _fail("source_class Graveyard должен быть graveyard")

    for field in FALSE_POLICY_FIELDS:
        if manifest.get(field) is not False:
            _fail(f"Поле {field} должно быть false")
    if manifest.get("owner_reactivation_required") is not True:
        _fail("owner_reactivation_required должен быть true")

    archive_policy = manifest.get("archive_policy") or {}
    for field in ("immutable_history", "prefer_new_version_over_in_place_edit", "current_canon_wins_on_conflict"):
        if archive_policy.get(field) is not True:
            _fail(f"archive_policy.{field} должен быть true")

    entries = manifest.get("archives")
    if not isinstance(entries, list):
        _fail("archives должен быть массивом")

    ids: set[str] = set()
    paths: set[str] = set()
    for entry in entries:
        archive_id = entry.get("archive_id")
        relative = entry.get("path")
        if not isinstance(archive_id, str) or not archive_id.startswith("GY-"):
            _fail("Некорректный archive_id")
        if archive_id in ids:
            _fail(f"Дублирующий archive_id: {archive_id}")
        ids.add(archive_id)

        if not isinstance(relative, str) or not relative.startswith("graveyard/GY-") or not relative.endswith(".md"):
            _fail(f"Некорректный путь архива: {relative}")
        if relative in paths:
            _fail(f"Дублирующий путь архива: {relative}")
        paths.add(relative)

        for field in ("actionable", "control", "canonical"):
            if entry.get(field) is not False:
                _fail(f"{archive_id}: {field} должен быть false")

        path = root / relative
        if not path.is_file():
            _fail(f"Архив из manifest отсутствует: {relative}")
        data = path.read_bytes()
        text = data.decode("utf-8")
        if not text.startswith(MARKER + "\n"):
            _fail(f"Архив не начинается с обязательного Graveyard marker: {relative}")
        if entry.get("byte_size") != len(data):
            _fail(f"Изменился byte_size архива: {relative}")
        if entry.get("sha256") != hashlib.sha256(data).hexdigest():
            _fail(f"Изменился SHA-256 архива: {relative}")
        if entry.get("git_blob_sha1") != _git_blob_sha1(data):
            _fail(f"Изменился Git blob SHA-1 архива: {relative}")

    actual = {p.relative_to(root).as_posix() for p in graveyard.glob("GY-*.md")}
    if actual != paths:
        missing = sorted(paths - actual)
        unregistered = sorted(actual - paths)
        _fail(f"Manifest не совпадает с архивами: missing={missing}, unregistered={unregistered}")

    canonical_files: list[Path] = []
    for path in root.iterdir():
        if path.is_file() and path.suffix.lower() in CANONICAL_SUFFIXES:
            canonical_files.append(path)
    for base_name in ("docs", "schemas", "config", ".github"):
        base = root / base_name
        if base.is_dir():
            canonical_files.extend(p for p in base.rglob("*") if p.is_file() and p.suffix.lower() in CANONICAL_SUFFIXES)

    for path in canonical_files:
        text = path.read_text(encoding="utf-8")
        if "graveyard/GY-" in text or "graveyard\\GY-" in text:
            _fail(f"Канонический/управляющий контур ссылается на конкретный Graveyard archive: {path.relative_to(root)}")


def validate_append_only(root: Path, base_sha: str | None) -> None:
    if not base_sha:
        return
    proc = subprocess.run(
        ["git", "diff", "--name-status", base_sha, "HEAD", "--", "graveyard/"],
        cwd=root,
        check=True,
        text=True,
        capture_output=True,
    )
    for line in proc.stdout.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        status = parts[0]
        affected = [p for p in parts[1:] if p.startswith("graveyard/GY-") and p.endswith(".md")]
        if affected and not status.startswith("A"):
            _fail(f"Graveyard append-only: существующий архив нельзя менять/удалять/переименовывать: {line}")


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    validate_graveyard(root)
    validate_append_only(root, os.environ.get("GRAVEYARD_BASE_SHA"))
    print("Graveyard: DATA/CONTROL, manifest, integrity, SSoT boundary и append-only проверки пройдены.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
