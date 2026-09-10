#!/usr/bin/env python3
"""Русскоязычная нормализация новых Graveyard-сводок.

Основной язык Graveyard — русский. Известные английские технические термины
при первом существенном употреблении автоматически получают краткое русское
пояснение. Исторические append-only архивы этим модулем не переписываются.
"""

from __future__ import annotations

import re
from collections import OrderedDict

TECHNICAL_TERM_EXPLANATIONS = OrderedDict([
    ("SSoT", "единый источник истины"),
    ("DATA", "данные, не являющиеся управляющей командой"),
    ("CONTROL", "управляющая информация, разрешающая действие"),
    ("ContextRef", "ссылка на источник контекста с provenance и trust-признаками"),
    ("provenance", "происхождение и цепочка источников данных"),
    ("trust", "уровень доверия к источнику или субъекту"),
    ("Graveyard", "слой исторических неисполняемых данных"),
    ("Knowledge Distillation", "выжимка полезного знания из большого исходного контекста"),
    ("ChangeSet", "точный набор изменений"),
    ("Change Evidence", "доказательство проверки самого изменения"),
    ("Integration Evidence", "доказательство совместимости изменения с текущим target"),
    ("Impact Assessment", "оценка влияния изменения на ранее полученные доказательства"),
    ("QA REUSE", "повторное использование применимых доказательств QA"),
    ("DELTA QA", "проверка только изменившейся или затронутой части"),
    ("FULL QA", "полная независимая проверка изменения"),
    ("Promotion", "безопасное продвижение проверенного изменения в целевое состояние"),
    ("PromotionTicket", "запечатанный билет точного разрешённого продвижения"),
    ("ApprovalRecord", "структурированная запись подтверждения человеком"),
    ("Human Approval", "явное подтверждение человеком"),
    ("TaskContract", "машинный паспорт и требования задачи"),
    ("TaskGraph", "граф шагов и зависимостей задачи"),
    ("Issue", "карточка текущей работы в GitHub"),
    ("Pull Request", "запрос на проверку и принятие изменения"),
    ("PR", "запрос на проверку и принятие изменения"),
    ("ADR", "запись принятого архитектурного решения"),
    ("API", "программный интерфейс взаимодействия"),
    ("IPC", "межпроцессное взаимодействие"),
    ("CI", "автоматическая проверка изменений"),
    ("QA", "независимая проверка качества"),
    ("Runtime", "исполняемая среда системы"),
    ("Worker", "исполнитель задачи"),
    ("Planner", "компонент планирования работы"),
    ("Scope", "разрешённая область доступа и изменений"),
    ("fail-closed", "безопасный отказ при неопределённости или нарушении проверки"),
    ("append-only", "режим, в котором историю можно только дополнять"),
    ("replay", "повторное воспроизведение сохранённых событий"),
    ("nonce", "одноразовое значение для защиты от повторного использования подтверждения"),
    ("hash", "криптографический отпечаток содержимого"),
    ("schema", "машинная схема структуры данных"),
    ("JSON Schema", "стандарт машинного описания и проверки JSON-данных"),
    ("SemVer", "семантическое версионирование"),
    ("GitHub Actions", "система автоматических workflow GitHub"),
    ("workflow", "рабочий процесс из связанных шагов"),
    ("target", "целевое состояние или ветка, куда продвигается изменение"),
    ("main", "основная каноническая ветка репозитория"),
])

CYRILLIC_RE = re.compile(r"[А-Яа-яЁё]")
LATIN_WORD_RE = re.compile(r"\b[A-Za-z][A-Za-z0-9_.:/+-]{2,}\b")
IGNORED_LATIN = {
    "KAT9I_OS", "GitHub", "Windows", "Rust", "Python", "Electron", "TypeScript",
    "Markdown", "JSON", "SHA", "UTC", "URL", "URI", "ID", "P0", "P1", "P2", "P3",
}


def is_russian_first(text: str) -> bool:
    """Проверяет, что объясняющий текст преимущественно русскоязычный."""
    cyr = len(CYRILLIC_RE.findall(text))
    latin = len(re.findall(r"[A-Za-z]", text))
    if cyr == 0:
        return False
    return cyr >= max(8, latin // 3)


def _already_explained(text: str, term: str, pos: int) -> bool:
    tail = text[pos + len(term):pos + len(term) + 180]
    return bool(re.match(r"\s*(?:—|-|\()\s*[А-Яа-яЁё]", tail))


def add_russian_explanations(text: str) -> tuple[str, list[str]]:
    """Добавляет русское пояснение при первом существенном употреблении известных терминов."""
    result = text
    added: list[str] = []
    for term, explanation in TECHNICAL_TERM_EXPLANATIONS.items():
        pattern = re.compile(rf"(?<![A-Za-z0-9_]){re.escape(term)}(?![A-Za-z0-9_])")
        match = pattern.search(result)
        if not match or _already_explained(result, term, match.start()):
            continue
        replacement = f"{term} — {explanation}"
        result = result[:match.start()] + replacement + result[match.end():]
        added.append(term)
    return result, added


def unexplained_english_terms(text: str) -> list[str]:
    """Возвращает неизвестные английские термины, которые требуют словаря/пояснения."""
    known = set(TECHNICAL_TERM_EXPLANATIONS) | IGNORED_LATIN
    found: list[str] = []
    for token in LATIN_WORD_RE.findall(text):
        if token in known or token.lower().startswith(("http", "github.com")):
            continue
        if token.isupper() and len(token) <= 2:
            continue
        if token not in found:
            found.append(token)
    return found


def normalize_graveyard_text(text: str) -> tuple[str, list[str]]:
    normalized, added = add_russian_explanations(text)
    if not is_russian_first(normalized):
        raise ValueError("Новая Graveyard-сводка должна быть русскоязычной")
    return normalized, added
