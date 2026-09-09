#!/usr/bin/env python3
"""Fail-closed checks for the non-actionable Graveyard data layer."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

MARKER = "# GRAVEYARD / DATA ONLY / NON-CANONICAL / NON-ACTIONABLE / NO AUTO-PROMOTION"
FALSE_POLICY_FIELDS = ("actionable", "control", "canonical", "auto_promotion", "ssot")
CONTROL_TEXT_SUFFIXES = {
    ".md", ".json", ".yml", ".yaml", ".toml", ".py", ".ps1", ".sh",
    ".cmd", ".bat", ".rs", ".ts", ".tsx", ".js", ".mjs", ".cjs",
    ".html", ".xml", ".ini", ".cfg", ".txt",
}
CONTROL_EXTENSIONLESS_DIRS = {"scripts", "tools", "bin", ".github"}
CONCRETE_GRAVEYARD_REF = re.compile(r"graveyard[\\/]+GY-[A-Za-z0-9._-]+\.md", re.IGNORECASE)
# Этот тест обязан содержать заведомо плохую concrete-reference строку, иначе
# невозможно доказать, что guard её ловит. Это единственное осознанное исключение.
CONTROL_SCAN_ALLOWLIST = {Path("tests/test_graveyard.py"), Path("tests/test_graveyard_codex_regressions.py")}


def _git_blob_sha1(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def _fail(message: str) -> None:
    raise ValueError(message)


def _validate_archive_relative_path(relative: str) -> Path:
    rel = Path(relative)
    if rel.is_absolute() or ".." in rel.parts:
        _fail(f"Путь архива не должен выходить из graveyard/: {relative}")
    if rel.parent != Path("graveyard"):
        _fail(f"Архив должен быть непосредственным файлом graveyard/: {relative}")
    if not rel.name.startswith("GY-") or rel.suffix.lower() != ".md":
        _fail(f"Некорректный путь архива: {relative}")
    return rel


def _iter_control_text_files(root: Path):
    """Сканирует текстовый control/code contour, включая extensionless executables."""
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if ".git" in rel.parts or (rel.parts and rel.parts[0] == "graveyard"):
            continue
        if rel in CONTROL_SCAN_ALLOWLIST:
            continue
        suffix_known = path.suffix.lower() in CONTROL_TEXT_SUFFIXES
        extensionless_control = (
            path.suffix == ""
            and (
                (bool(rel.parts) and rel.parts[0] in CONTROL_EXTENSIONLESS_DIRS)
                or os.access(path, os.X_OK)
            )
        )
        if suffix_known or extensionless_control:
            yield path


def validate_graveyard(root: Path) -> None:
    graveyard = root / "graveyard"
    manifest_path = graveyard / "MANIFEST.json"
    readme_path = graveyard / "README.md"

    if readme_path.is_symlink() or manifest_path.is_symlink():
        _fail("graveyard/README.md и MANIFEST.json должны быть обычными файлами, не symlink")
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

        if not isinstance(relative, str):
            _fail(f"Некорректный путь архива: {relative}")
        rel_path = _validate_archive_relative_path(relative)
        normalized = rel_path.as_posix()
        if normalized in paths:
            _fail(f"Дублирующий путь архива: {normalized}")
        paths.add(normalized)

        for field in ("actionable", "control", "canonical"):
            if entry.get(field) is not False:
                _fail(f"{archive_id}: {field} должен быть false")

        path = root / rel_path
        if path.is_symlink():
            _fail(f"Graveyard archive не может быть symlink: {normalized}")
        if not path.is_file():
            _fail(f"Архив из manifest отсутствует: {normalized}")
        data = path.read_bytes()
        text = data.decode("utf-8")
        if not text.startswith(MARKER + "\n"):
            _fail(f"Архив не начинается с обязательного Graveyard marker: {normalized}")
        if entry.get("byte_size") != len(data):
            _fail(f"Изменился byte_size архива: {normalized}")
        if entry.get("sha256") != hashlib.sha256(data).hexdigest():
            _fail(f"Изменился SHA-256 архива: {normalized}")
        if entry.get("git_blob_sha1") != _git_blob_sha1(data):
            _fail(f"Изменился Git blob SHA-1 архива: {normalized}")

    actual: set[str] = set()
    for path in graveyard.glob("GY-*.md"):
        if path.is_symlink():
            _fail(f"Незарегистрированный или зарегистрированный GY archive не может быть symlink: {path.name}")
        actual.add(path.relative_to(root).as_posix())
    if actual != paths:
        missing = sorted(paths - actual)
        unregistered = sorted(actual - paths)
        _fail(f"Manifest не совпадает с архивами: missing={missing}, unregistered={unregistered}")

    for path in _iter_control_text_files(root):
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        match = CONCRETE_GRAVEYARD_REF.search(text)
        if match:
            _fail(
                "Канонический/исполняемый контур ссылается на конкретный Graveyard archive: "
                f"{path.relative_to(root)} -> {match.group(0)}"
            )


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
    print("Graveyard: DATA/CONTROL, manifest, integrity, symlink, SSoT boundary и append-only проверки пройдены.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
