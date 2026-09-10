#!/usr/bin/env python3
"""Fail-closed checks for the non-actionable Graveyard data layer."""

from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

MARKER = "# GRAVEYARD / DATA ONLY / NON-CANONICAL / NON-ACTIONABLE / NO AUTO-PROMOTION"
FALSE_POLICY_FIELDS = ("actionable", "control", "canonical", "auto_promotion", "ssot")
CONTROL_TEXT_SUFFIXES = {
    ".md", ".json", ".yml", ".yaml", ".toml", ".py", ".pyw", ".ps1", ".psm1", ".psd1", ".sh",
    ".cmd", ".bat", ".rs", ".ts", ".tsx", ".js", ".mjs", ".cjs",
    ".html", ".xml", ".ini", ".cfg", ".txt",
}
PYTHON_CONTROL_SUFFIXES = {".py", ".pyw"}
CONTROL_EXTENSIONLESS_DIRS = {"scripts", "tools", "bin", ".github"}
CONCRETE_GRAVEYARD_REF = re.compile(
    r"graveyard(?:[\\/]+(?:\.)?)*[\\/]+GY-[A-Za-z0-9._-]+\.md",
    re.IGNORECASE,
)
# Эти тесты обязаны содержать заведомо плохие concrete-reference строки, иначе
# невозможно доказать, что guard их ловит. Это единственные осознанные исключения.
CONTROL_SCAN_ALLOWLIST = {
    Path("tests/test_graveyard.py"),
    Path("tests/test_graveyard_codex_regressions.py"),
    Path("tests/test_graveyard_issue99.py"),
}


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


def _is_alias(path: Path) -> bool:
    if path.is_symlink():
        return True
    is_junction = getattr(path, "is_junction", None)
    return bool(callable(is_junction) and is_junction())


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def _validate_repo_aliases(root: Path, graveyard: Path) -> None:
    """Reject repo-wide symlink/junction aliases resolving into Graveyard.

    Static scanning cannot infer a hidden alias from source text. We therefore
    inspect aliases themselves before scanning control files and fail closed if
    any repository alias resolves to the Graveyard directory or a child of it.
    """
    graveyard_real = graveyard.resolve(strict=True)
    for current, dirnames, filenames in os.walk(root, topdown=True, followlinks=False):
        current_path = Path(current)
        try:
            current_rel = current_path.relative_to(root)
        except ValueError:
            _fail(f"Repo walk вышел за root: {current_path}")
        if ".git" in current_rel.parts:
            dirnames[:] = []
            continue

        names = list(dirnames) + list(filenames)
        for name in names:
            candidate = current_path / name
            if candidate == graveyard:
                continue
            if not _is_alias(candidate):
                continue
            try:
                resolved = candidate.resolve(strict=True)
            except (OSError, RuntimeError) as exc:
                _fail(f"Repo alias не удалось безопасно разрешить: {candidate}: {exc}")
            if resolved == graveyard_real or _is_within(resolved, graveyard_real):
                _fail(
                    "Repo-wide alias не может указывать в Graveyard: "
                    f"{candidate.relative_to(root)} -> {resolved}"
                )

        kept_dirs: list[str] = []
        for name in dirnames:
            candidate = current_path / name
            if candidate == graveyard or _is_alias(candidate):
                continue
            kept_dirs.append(name)
        dirnames[:] = kept_dirs


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
        known_control_dir = bool(rel.parts) and rel.parts[0] in CONTROL_EXTENSIONLESS_DIRS
        if "__pycache__" in rel.parts:
            continue
        if suffix_known or extensionless_control or known_control_dir:
            yield path


def _read_control_text(path: Path) -> str:
    """Decode known control text formats; selected control files fail closed if undecodable."""
    data = path.read_bytes()
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        return data.decode("utf-16")
    if data.startswith(b"\xef\xbb\xbf"):
        return data.decode("utf-8-sig")
    if b"\x00" in data:
        even_zeros = data[0::2].count(0)
        odd_zeros = data[1::2].count(0)
        if even_zeros == odd_zeros:
            _fail(f"Неоднозначная кодировка control-файла: {path}")
        encoding = "utf-16-be" if even_zeros > odd_zeros else "utf-16-le"
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            _fail(f"Некорректный UTF-16 control-файл: {path}")
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        if b"\x00" in data:
            for encoding in ("utf-16-le", "utf-16-be"):
                try:
                    text = data.decode(encoding)
                except UnicodeDecodeError:
                    continue
                if text:
                    return text
        _fail(f"Control-файл не удалось безопасно декодировать как текст: {path}")


def _find_concrete_graveyard_ref(text: str) -> str | None:
    match = CONCRETE_GRAVEYARD_REF.search(text)
    if match:
        return match.group(0)
    # Консервативно обнаруживаем split literals / Path joins.
    if re.search(r"['\"]graveyard['\"]", text, re.IGNORECASE):
        archive = re.search(r"['\"]GY-[A-Za-z0-9._-]+\.md['\"]", text, re.IGNORECASE)
        if archive:
            return archive.group(0)
    return None


def _ast_call_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _ast_call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return None


def _ast_static_string(node: ast.AST, env: dict[str, str]) -> str | None:
    """Safely fold only deterministic string/path expressions; never execute code."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Name):
        return env.get(node.id)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = _ast_static_string(node.left, env)
        right = _ast_static_string(node.right, env)
        if left is not None and right is not None:
            return left + right
        return None
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        left = _ast_static_string(node.left, env)
        right = _ast_static_string(node.right, env)
        if left is not None and right is not None:
            return left.rstrip("/\\") + "/" + right.lstrip("/\\")
        return None
    if isinstance(node, ast.JoinedStr):
        parts: list[str] = []
        for value in node.values:
            if not isinstance(value, ast.Constant) or not isinstance(value.value, str):
                return None
            parts.append(value.value)
        return "".join(parts)
    if isinstance(node, ast.Call):
        name = (_ast_call_name(node.func) or "").casefold()
        if name in {"path", "pathlib.path", "purepath", "pathlib.purepath", "posixpath", "windowspath"}:
            if len(node.args) == 1:
                return _ast_static_string(node.args[0], env)
            return None
        if name in {"os.path.join", "posixpath.join", "ntpath.join"}:
            parts = [_ast_static_string(arg, env) for arg in node.args]
            if parts and all(part is not None for part in parts):
                return "/".join(str(part).strip("/\\") for part in parts)
            return None
        if isinstance(node.func, ast.Attribute) and node.func.attr == "joinpath":
            base = _ast_static_string(node.func.value, env)
            parts = [_ast_static_string(arg, env) for arg in node.args]
            if base is not None and all(part is not None for part in parts):
                return "/".join([base.rstrip("/\\")] + [str(part).strip("/\\") for part in parts])
    return None


def _find_python_ast_graveyard_ref(text: str) -> str | None:
    """Detect compile-time Python path construction that resolves to a GY archive."""
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        _fail(f"Python control-файл не удалось разобрать AST: line={exc.lineno}: {exc.msg}")

    def scan_block(statements: list[ast.stmt], inherited: dict[str, str]) -> str | None:
        env = dict(inherited)
        for statement in statements:
            if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                found = scan_block(statement.body, env)
                if found:
                    return found
                continue
            nested_blocks: list[list[ast.stmt]] = []
            if isinstance(statement, ast.If):
                nested_blocks.extend([statement.body, statement.orelse])
            elif isinstance(statement, (ast.For, ast.AsyncFor, ast.While)):
                nested_blocks.extend([statement.body, statement.orelse])
            elif isinstance(statement, ast.Try):
                nested_blocks.extend([statement.body, statement.orelse, statement.finalbody])
                nested_blocks.extend(handler.body for handler in statement.handlers)
            elif isinstance(statement, (ast.With, ast.AsyncWith)):
                nested_blocks.append(statement.body)

            value_node: ast.AST | None = None
            targets: list[ast.AST] = []
            if isinstance(statement, ast.Assign):
                value_node = statement.value
                targets = list(statement.targets)
            elif isinstance(statement, ast.AnnAssign) and statement.value is not None:
                value_node = statement.value
                targets = [statement.target]
            if value_node is not None:
                value = _ast_static_string(value_node, env)
                if value and _find_concrete_graveyard_ref(value):
                    return value
                if value is not None:
                    for target in targets:
                        if isinstance(target, ast.Name):
                            env[target.id] = value

            for node in ast.walk(statement):
                value = _ast_static_string(node, env)
                if value and _find_concrete_graveyard_ref(value):
                    return value
            for block in nested_blocks:
                found = scan_block(block, env)
                if found:
                    return found
        return None

    return scan_block(tree.body, {})


def validate_graveyard(root: Path) -> None:
    graveyard = root / "graveyard"
    manifest_path = graveyard / "MANIFEST.json"
    readme_path = graveyard / "README.md"

    if _is_alias(graveyard):
        _fail("Graveyard directory не может быть alias")
    for child in graveyard.iterdir():
        if _is_alias(child) or child.is_dir() or not child.is_file():
            _fail(f"Graveyard содержит alias/каталог вместо обычного файла: {child.name}")

    if _is_alias(readme_path) or _is_alias(manifest_path):
        _fail("graveyard/README.md и MANIFEST.json должны быть обычными файлами, не alias")
    if not readme_path.is_file():
        _fail("Отсутствует graveyard/README.md")
    if not manifest_path.is_file():
        _fail("Отсутствует graveyard/MANIFEST.json")

    _validate_repo_aliases(root, graveyard)

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
        if _is_alias(path):
            _fail(f"Graveyard archive не может быть alias: {normalized}")
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
        if _is_alias(path):
            _fail(f"Незарегистрированный или зарегистрированный GY archive не может быть alias: {path.name}")
        actual.add(path.relative_to(root).as_posix())
    if actual != paths:
        missing = sorted(paths - actual)
        unregistered = sorted(actual - paths)
        _fail(f"Manifest не совпадает с архивами: missing={missing}, unregistered={unregistered}")

    for path in _iter_control_text_files(root):
        text = _read_control_text(path)
        concrete_ref = _find_concrete_graveyard_ref(text)
        if concrete_ref is None and path.suffix.lower() in PYTHON_CONTROL_SUFFIXES:
            concrete_ref = _find_python_ast_graveyard_ref(text)
        if concrete_ref:
            _fail(
                "Канонический/исполняемый контур ссылается на конкретный Graveyard archive: "
                f"{path.relative_to(root)} -> {concrete_ref}"
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
    print("Graveyard: DATA/CONTROL, manifest, integrity, repo aliases, AST SSoT boundary и append-only проверки пройдены.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
