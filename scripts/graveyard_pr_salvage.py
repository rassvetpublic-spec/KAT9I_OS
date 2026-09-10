#!/usr/bin/env python3
"""DATA-only salvage-аудит закрытых несмерженных Pull Request.

Скрипт не создаёт Issue/PR/ADR/TaskContract и не меняет Graveyard. Он только
классифицирует уже собранные GitHub evidence и выпускает неисполняемый отчёт.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "1.0.0"
SALVAGE_MARKER = "<!-- graveyard-pr-salvage-audit -->"
MIN_CHANGED_FILES = 5
MIN_CHANGED_LINES = 250
MIN_COMMITS = 5
TEXT_SUFFIXES = {".md", ".txt", ".json", ".yml", ".yaml", ".toml", ".py", ".rs", ".ts", ".tsx", ".js", ".html"}
SUPERSEDED_MARKERS = (
    "superseded", "obsolete", "устарев", "параллельн", "не перенос", "не использовать",
    "не включать", "duplicate", "дубликат", "заменен", "заменён",
)
REVIEW_FINDING_MARKERS = (
    "p0 badge", "p1 badge", "p2 badge", "contradict", "invalid", "cannot", "must ",
    "fails", "ошиб", "невалид", "должен", "нельзя", "конфликт",
)
SECRET_PATTERNS = (
    re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----.*?-----END [A-Z0-9 ]*PRIVATE KEY-----", re.DOTALL),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
)
MENTION_RE = re.compile(r"(?<![A-Za-z0-9_])@(?=[A-Za-z0-9])")
WORD_RE = re.compile(r"[A-Za-zА-Яа-яЁё0-9_./+-]+")
BULLET_RE = re.compile(r"^\s*(?:[-*+]\s+|\d+[.)]\s+)(.+?)\s*$")


def _redact(text: str) -> str:
    result = text or ""
    for pattern in SECRET_PATTERNS:
        result = pattern.sub("[УДАЛЁН_СЕКРЕТ]", result)
    return result


def _neutralize_mentions(text: str) -> str:
    return MENTION_RE.sub("@\u200b", text)


def _compact(text: str, limit: int = 700) -> str:
    text = re.sub(r"\s+", " ", _neutralize_mentions(_redact(text))).strip()
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def _sanitize_evidence(value: Any) -> Any:
    if isinstance(value, str):
        return _compact(value, 700)
    if isinstance(value, list):
        return [_sanitize_evidence(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _sanitize_evidence(item) for key, item in value.items()}
    return value


def _normalized_words(text: str) -> list[str]:
    words = []
    for token in WORD_RE.findall(text.lower()):
        token = token.strip("./+-_")
        if len(token) < 4 and not any(c.isdigit() for c in token):
            continue
        if token in {"https", "github", "com", "этот", "этого", "который", "также", "через", "после", "будет", "должен"}:
            continue
        words.append(token)
    return words


def _extract_statements(text: str) -> list[str]:
    items: list[str] = []
    for raw in (text or "").splitlines():
        match = BULLET_RE.match(raw)
        if not match:
            continue
        item = _compact(match.group(1), 500)
        item = re.sub(r"^\[[ xX]\]\s*", "", item)
        if len(item) < 20 or item.startswith("http"):
            continue
        if item not in items:
            items.append(item)
    return items[:80]


def _external_issue_comments(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Исключает собственные salvage-комментарии, чтобы повторный запуск не кормил сам себя."""
    result: list[dict[str, Any]] = []
    for comment in payload.get("issue_comments", []):
        body = str(comment.get("body", ""))
        if SALVAGE_MARKER in body:
            continue
        result.append(comment)
    return result


def _load_canon_text(root: Path, filenames: list[str]) -> str:
    chunks: list[str] = []
    total = 0
    for name in filenames:
        path = root / name
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if total + len(text) > 2_000_000:
            text = text[: max(0, 2_000_000 - total)]
        chunks.append(text.lower())
        total += len(text)
        if total >= 2_000_000:
            break
    return "\n".join(chunks)


def _statement_in_canon(statement: str, canon_text: str) -> tuple[bool, float]:
    compact = re.sub(r"\s+", " ", statement.lower()).strip()
    normalized_canon = re.sub(r"\s+", " ", canon_text)
    if len(compact) >= 24 and compact in normalized_canon:
        return True, 1.0
    words = _normalized_words(statement)
    if len(words) < 5:
        return False, 0.0
    unique_words = set(words)
    present = sum(1 for word in unique_words if word in canon_text)
    coverage = present / max(1, len(unique_words))
    return coverage >= 0.78, coverage


def _superseded_evidence(payload: dict[str, Any]) -> bool:
    pr = payload["pr"]
    labels = " ".join(str(x) for x in pr.get("labels", []))
    comments = "\n".join(str(x.get("body", "")) for x in _external_issue_comments(payload))
    text = "\n".join((str(pr.get("title", "")), str(pr.get("body", "")), labels, comments)).lower()
    return any(marker in text for marker in SUPERSEDED_MARKERS)


def _eligibility(payload: dict[str, Any]) -> tuple[bool, str]:
    pr = payload["pr"]
    if pr.get("merged"):
        return False, "MERGED_INTO_CANON"
    if pr.get("state") != "closed":
        return False, "PR_NOT_CLOSED"
    changed_lines = int(pr.get("additions", 0)) + int(pr.get("deletions", 0))
    large = (
        int(pr.get("changed_files", 0)) >= MIN_CHANGED_FILES
        or changed_lines >= MIN_CHANGED_LINES
        or int(pr.get("commits", 0)) >= MIN_COMMITS
    )
    if large:
        return True, "CLOSED_UNMERGED_LARGE"
    if _superseded_evidence(payload):
        return True, "CLOSED_UNMERGED_EXPLICITLY_SUPERSEDED"
    return False, "CLOSED_UNMERGED_SMALL"


def _item(category: str, text: str, *, confidence: str, evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "category": category,
        "text": _compact(text),
        "confidence": confidence,
        "evidence": _sanitize_evidence(evidence or {}),
    }


def _dedupe(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in items:
        key = hashlib.sha256((item["category"] + "\0" + item["text"].lower()).encode("utf-8")).hexdigest()
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result[:200]


def build_audit(payload: dict[str, Any], *, root: Path) -> dict[str, Any]:
    if not isinstance(payload.get("pr"), dict):
        raise ValueError("Отсутствует объект pr")
    repository = str(payload.get("repository", ""))
    canon_revision = str(payload.get("canon_revision", ""))
    if not re.fullmatch(r"[a-f0-9]{40}", canon_revision):
        raise ValueError("canon_revision должен быть полным Git SHA-1")

    eligible, reason = _eligibility(payload)
    pr = payload["pr"]
    files = payload.get("files", [])
    changed_names = [str(f.get("filename", "")) for f in files if f.get("filename")]
    canon_text = _load_canon_text(root, changed_names)
    items: list[dict[str, Any]] = []

    if eligible:
        for file_info in files:
            name = str(file_info.get("filename", ""))
            status = str(file_info.get("status", ""))
            head_sha = file_info.get("sha")
            main_sha = file_info.get("main_blob_sha")
            if status == "removed" and not main_sha:
                items.append(_item(
                    "ALREADY_IN_MAIN",
                    f"Удаление файла {name} уже отражено в текущем main.",
                    confidence="HIGH",
                    evidence={"path": name, "match": "ABSENT_IN_MAIN"},
                ))
            elif head_sha and main_sha and head_sha == main_sha:
                items.append(_item(
                    "ALREADY_IN_MAIN",
                    f"Файл {name} в head закрытого PR побайтно совпадает с текущим main.",
                    confidence="HIGH",
                    evidence={"path": name, "blob_sha": head_sha},
                ))
            else:
                items.append(_item(
                    "NEEDS_SEMANTIC_REVIEW",
                    f"Файл {name} отличается от текущего main; автоматического совпадения недостаточно для решения о переносе идеи.",
                    confidence="HIGH",
                    evidence={"path": name, "status": status, "head_blob_sha": head_sha, "main_blob_sha": main_sha},
                ))

        for statement in _extract_statements(str(pr.get("body", ""))):
            matched, score = _statement_in_canon(statement, canon_text)
            if matched:
                items.append(_item(
                    "ALREADY_IN_MAIN",
                    statement,
                    confidence="MEDIUM" if score < 1.0 else "HIGH",
                    evidence={"source": "PR_BODY", "token_coverage": round(score, 3)},
                ))
            else:
                items.append(_item(
                    "UNIQUE_IDEA_CANDIDATE",
                    statement,
                    confidence="LOW",
                    evidence={"source": "PR_BODY", "token_coverage": round(score, 3)},
                ))

        for comment in _external_issue_comments(payload):
            body = str(comment.get("body", ""))
            if not any(marker in body.lower() for marker in SUPERSEDED_MARKERS):
                continue
            statements = _extract_statements(body)
            if not statements:
                statements = [_compact(body, 500)] if body.strip() else []
            for statement in statements[:20]:
                items.append(_item(
                    "REJECTED_OPTION_CANDIDATE",
                    statement,
                    confidence="MEDIUM",
                    evidence={"source": "PR_CONVERSATION", "url": comment.get("url")},
                ))

        for comment in payload.get("review_comments", []):
            body = str(comment.get("body", ""))
            if not any(marker in body.lower() for marker in REVIEW_FINDING_MARKERS):
                continue
            heading = next((line.strip(" #*_`") for line in body.splitlines() if line.strip()), body)
            items.append(_item(
                "NEGATIVE_TEST_CANDIDATE",
                heading,
                confidence="MEDIUM",
                evidence={
                    "source": "REVIEW_COMMENT",
                    "path": comment.get("path"),
                    "line": comment.get("line"),
                    "url": comment.get("url"),
                },
            ))

    items = _dedupe(items)
    counts: dict[str, int] = {}
    for item in items:
        counts[item["category"]] = counts.get(item["category"], 0) + 1

    return {
        "schema_version": SCHEMA_VERSION,
        "repository": _compact(repository, 200),
        "pr_number": int(pr.get("number", 0)),
        "title": _compact(str(pr.get("title", "")), 240),
        "source_head_sha": str(pr.get("head_sha", "")),
        "canon_revision": canon_revision,
        "audit_required": eligible,
        "audit_reason": reason,
        "source_is_superseded_candidate": _superseded_evidence(payload),
        "metrics": {
            "changed_files": int(pr.get("changed_files", 0)),
            "additions": int(pr.get("additions", 0)),
            "deletions": int(pr.get("deletions", 0)),
            "commits": int(pr.get("commits", 0)),
            "review_comments": len(payload.get("review_comments", [])),
        },
        "classification_counts": counts,
        "items": items,
        "actionable": False,
        "control": False,
        "canonical": False,
        "auto_promotion": False,
        "requires_canon_check_before_capture": True,
        "promotion_requires_owner_approval": True,
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Graveyard salvage-аудит PR",
        "",
        "> DATA ONLY / NON-CANONICAL / NON-ACTIONABLE. Этот отчёт не создаёт работу и не разрешает перенос изменений.",
        "",
        f"- PR: #{report['pr_number']} — {report['title']}",
        f"- Canon revision: `{report['canon_revision']}`",
        f"- Audit required: `{str(report['audit_required']).lower()}`",
        f"- Причина: `{report['audit_reason']}`",
        "",
        "## Классификация",
        "",
    ]
    if not report["items"]:
        lines.append("Автоматический salvage не требуется или доказательств для классификации нет.")
    else:
        names = {
            "ALREADY_IN_MAIN": "Уже в main",
            "UNIQUE_IDEA_CANDIDATE": "Кандидат уникальной идеи",
            "REJECTED_OPTION_CANDIDATE": "Кандидат отвергнутого/устаревшего варианта",
            "NEGATIVE_TEST_CANDIDATE": "Кандидат негативного теста",
            "NEEDS_SEMANTIC_REVIEW": "Нужна семантическая сверка",
        }
        for item in report["items"]:
            lines.append(f"- **{names.get(item['category'], item['category'])}** [{item['confidence']}]: {item['text']}")
    lines.extend([
        "",
        "## Граница безопасности",
        "",
        "Отчёт является только DATA. Он не записывается в `graveyard/` автоматически, не создаёт Issue/ADR/TaskContract/PR и не меняет `docs/`. Для сохранения в Graveyard требуется отдельный capture с актуальной проверкой канона; DATA → CONTROL по-прежнему требует Human Approval.",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Сформировать DATA-only salvage-аудит закрытого PR")
    parser.add_argument("--input", required=True, help="JSON evidence, собранный trusted GitHub workflow")
    parser.add_argument("--output-dir", default="salvage-audit")
    parser.add_argument("--repo-root", default=".")
    args = parser.parse_args()
    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    report = build_audit(payload, root=Path(args.repo_root).resolve())
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out / "report.md").write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps({"audit_required": report["audit_required"], "audit_reason": report["audit_reason"], "counts": report["classification_counts"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
