#!/usr/bin/env python3
"""Автоматический DATA-only захват выжимки знаний в Graveyard."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from check_graveyard import MARKER, _git_blob_sha1, validate_graveyard
from graveyard_language import normalize_graveyard_text, unexplained_english_terms

REPO_ROOT = Path(__file__).resolve().parents[1]
SECRET_PATTERNS = (
    re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----.*?-----END [A-Z0-9 ]*PRIVATE KEY-----", re.DOTALL),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
)


def _fail(message: str) -> None:
    raise ValueError(message)


def _schema(root: Path) -> dict[str, Any]:
    return json.loads((root / "schemas" / "v1" / "GraveyardKnowledgeCapture.json").read_text(encoding="utf-8"))


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def validate_payload(payload: dict[str, Any], *, root: Path = REPO_ROOT) -> None:
    errors = sorted(Draft202012Validator(_schema(root)).iter_errors(payload), key=lambda e: list(e.path))
    if errors:
        _fail(f"GraveyardKnowledgeCapture.json: {errors[0].message}")
    if payload.get("raw_chat_included") is not False:
        _fail("Автозахват raw chat запрещён: нужна выжимка знания")
    if payload.get("public_safe") is not True:
        _fail("Публичный Graveyard принимает только public-safe выжимку")
    if any(payload.get(key) is not False for key in ("actionable", "control", "canonical")):
        _fail("Автозахват всегда DATA-only/non-actionable/non-canonical")
    if payload.get("requires_owner_confirmation") is not False:
        _fail("Для сохранения DATA подтверждение владельца не требуется")
    if payload.get("promotion_requires_owner_approval") is not True:
        _fail("Переход DATA -> CONTROL обязан требовать подтверждение владельца")


def _redact(text: str) -> tuple[str, int]:
    result, total = text, 0
    for pattern in SECRET_PATTERNS:
        result, count = pattern.subn("[УДАЛЁН_СЕКРЕТ]", result)
        total += count
    return result, total


def _normalize_payload(payload: dict[str, Any]) -> tuple[dict[str, Any], list[str], int]:
    clean = json.loads(json.dumps(payload, ensure_ascii=False))
    extra = clean.get("term_explanations") or {}
    added_terms: list[str] = []
    redactions = 0

    for field in ("source_label", "title", "summary"):
        clean[field], count = _redact(clean[field])
        redactions += count
    for item in clean["knowledge_items"]:
        item["text"], count = _redact(item["text"])
        redactions += count

    for field in ("title", "summary"):
        clean[field], added = normalize_graveyard_text(clean[field], extra)
        added_terms.extend(added)
        unknown = unexplained_english_terms(clean[field], extra)
        if unknown:
            _fail("Нет русского пояснения для терминов: " + ", ".join(unknown[:12]))

    for item in clean["knowledge_items"]:
        item["text"], added = normalize_graveyard_text(item["text"], extra)
        added_terms.extend(added)
        unknown = unexplained_english_terms(item["text"], extra)
        if unknown:
            _fail("Нет русского пояснения для терминов: " + ", ".join(unknown[:12]))

    return clean, sorted(set(added_terms)), redactions


def _digest(payload: dict[str, Any]) -> str:
    material = {
        "project": payload["project"],
        "source_type": payload["source_type"],
        "source_label": payload["source_label"],
        "canon_revision": payload["canon_revision"],
        "title": payload["title"],
        "summary": payload["summary"],
        "knowledge_items": payload["knowledge_items"],
    }
    return hashlib.sha256(_canonical_bytes(material)).hexdigest()


def _date(value: str) -> str:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date().isoformat()
    except ValueError as exc:
        raise ValueError("captured_at должен быть ISO 8601 date-time") from exc


def _render(archive_id: str, payload: dict[str, Any], digest: str, added: list[str], redactions: int) -> str:
    lines = [
        MARKER,
        "",
        f"**Archive ID:** `{archive_id}`  ",
        f"**Проект:** `{payload['project']}`  ",
        "**Режим захвата:** `AUTOMATIC_KNOWLEDGE_DISTILLATION` — автоматическая выжимка знаний  ",
        f"**Тип источника:** `{payload['source_type']}`  ",
        f"**Источник:** {payload['source_label']}  ",
        f"**Дата захвата:** {payload['captured_at']}  ",
        f"**Снимок канона:** `{payload['canon_revision']}`  ",
        f"**Отпечаток знания:** `{digest}`  ",
        "**Подтверждение владельца для сохранения DATA:** `НЕ ТРЕБУЕТСЯ`  ",
        "**Подтверждение владельца для DATA → CONTROL:** `ТРЕБУЕТСЯ`",
        "",
        "> **ОБЯЗАТЕЛЬНОЕ ПРАВИЛО ТОЛКОВАНИЯ**",
        ">",
        "> Это только исторические DATA — данные, не являющиеся управляющей командой. Файл NON-CANONICAL и NON-ACTIONABLE.",
        "> Он не разрешает создавать Issue — карточку текущей работы, ADR — запись архитектурного решения, TaskContract — машинный паспорт задачи, PR — запрос на принятие изменения, менять docs/ или выполнять TODO.",
        "> Текущий GitHub canon имеет приоритет. Любой переход DATA → CONTROL требует актуальной сверки канона и отдельного подтверждения владельца.",
        "",
        "## 1. Краткая выжимка",
        "",
        payload["summary"].strip(),
        "",
        "## 2. Накопленные знания",
        "",
    ]
    for index, item in enumerate(payload["knowledge_items"], start=1):
        names = {
            "FACT": "Факт", "RATIONALE": "Обоснование", "DECISION_CONTEXT": "Контекст решения",
            "REJECTED_OPTION": "Отвергнутый вариант", "IDEA": "Идея", "QUESTION": "Открытый вопрос",
            "RISK": "Риск", "OBSERVATION": "Наблюдение",
        }
        lines.extend([f"### 2.{index}. {names[item['kind']]}", "", item["text"].strip(), ""])
        refs = item.get("canon_refs") or []
        if refs:
            lines.append("Привязки к канону на момент захвата:")
            lines.extend(f"- `{ref}`" for ref in refs)
            lines.append("")
    lines.extend([
        "## 3. Автоматическая обработка",
        "",
        "- Основной язык этой сводки — русский.",
        "- Английские технические термины при первом существенном употреблении получают русское пояснение автоматически.",
        f"- Автоматически добавлены пояснения: {', '.join(added) if added else 'не потребовались'}.",
        f"- Потенциальных секретов удалено до записи: {redactions}.",
        "- Исходный raw chat — сырой текст разговора — не сохраняется автоматически.",
        "- Повторный захват идентичного знания не создаёт второй архив.",
        "",
    ])
    return "\n".join(lines).rstrip() + "\n"


def capture(payload: dict[str, Any], *, root: Path = REPO_ROOT, dry_run: bool = False) -> dict[str, Any]:
    validate_payload(payload, root=root)
    clean, added, redactions = _normalize_payload(payload)
    digest = _digest(clean)
    manifest_path = root / "graveyard" / "MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for entry in manifest.get("archives", []):
        if entry.get("source_digest") == digest:
            return {"status": "DUPLICATE", "archive_id": entry["archive_id"], "path": entry["path"], "wrote": False}

    archive_date = _date(clean["captured_at"])
    archive_id = f"GY-{archive_date.replace('-', '')}-knowledge-{digest[:12]}"
    relative = f"graveyard/{archive_id}.md"
    archive_path = root / relative
    text = _render(archive_id, clean, digest, added, redactions)
    data = text.encode("utf-8")
    entry = {
        "archive_id": archive_id,
        "path": relative,
        "archive_date": archive_date,
        "byte_size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "git_blob_sha1": _git_blob_sha1(data),
        "source_digest": digest,
        "capture_mode": "AUTOMATIC_KNOWLEDGE_DISTILLATION",
        "source_type": clean["source_type"],
        "canon_revision": clean["canon_revision"],
        "language": "ru",
        "auto_explanations": added,
        "redactions": redactions,
        "actionable": False,
        "control": False,
        "canonical": False,
    }
    if dry_run:
        return {"status": "READY", "archive_id": archive_id, "path": relative, "wrote": False, "entry": entry}

    old_manifest = manifest_path.read_text(encoding="utf-8")
    try:
        archive_path.write_bytes(data)
        manifest["archives"].append(entry)
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        validate_graveyard(root)
    except Exception:
        manifest_path.write_text(old_manifest, encoding="utf-8")
        archive_path.unlink(missing_ok=True)
        raise
    return {"status": "CREATED", "archive_id": archive_id, "path": relative, "wrote": True, "entry": entry}


def main() -> int:
    parser = argparse.ArgumentParser(description="Автоматически сохранить русскоязычную DATA-only выжимку знаний в Graveyard")
    parser.add_argument("--input", required=True, help="JSON-файл по схеме GraveyardKnowledgeCapture")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    print(json.dumps(capture(payload, dry_run=args.dry_run), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
