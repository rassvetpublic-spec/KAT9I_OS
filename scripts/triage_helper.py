# -*- coding: utf-8 -*-
"""
Детектор классификации обращений для triage KAT9I_OS (Issue #17, #39).

Этот модуль является единственной реализацией правил классификации:
GitHub Actions вызывает его напрямую, а tests/test_triage_helper.py
проверяет те же правила, которые выполняются в production workflow.
"""

from typing import Dict, Any


BOILERPLATE_MARKERS = (
    "не публикуйте токены",
    "не публикуйте секреты",
    "я не добавляю в issue токены",
    "я проверил границы задачи и не добавляю секреты",
    "я не добавил в обращение пароль, api-ключ, токен доступа или другой секрет",
)

FORM_PREFIXES = (
    "[ошибка]",
    "[функция]",
    "[улучшение]",
    "[техзадача]",
)


def _filtered_body(body: str) -> str:
    return "\n".join(
        line
        for line in (body or "").splitlines()
        if not any(marker in line.lower() for marker in BOILERPLATE_MARKERS)
    )


def _title_without_form_prefix(title: str) -> str:
    value = (title or "").strip()
    lowered = value.lower()
    for prefix in FORM_PREFIXES:
        if lowered.startswith(prefix):
            return value[len(prefix):].lstrip()
    return value


def classify_issue_text(title: str, body: str) -> Dict[str, Any]:
    normalized_title = (title or "").strip().lower()
    semantic_title = _title_without_form_prefix(title)
    filtered_body = _filtered_body(body)
    text = f"{semantic_title}\n{filtered_body}".lower()

    # 1. Тип обращения. Явно выбранная Issue Form имеет приоритет.
    issue_type = "Вопрос / Обсуждение"
    labels = []

    if normalized_title.startswith("[ошибка]"):
        issue_type = "Ошибка (Bug)"
        labels.append("bug")
    elif normalized_title.startswith("[функция]") or normalized_title.startswith("[улучшение]"):
        issue_type = "Улучшение (Enhancement)"
        labels.append("enhancement")
    elif normalized_title.startswith("[техзадача]"):
        issue_type = "Техническая задача"
    elif any(k in text for k in ("сообщить об ошибке", "баг", "ошибка", "crash", "fail")):
        issue_type = "Ошибка (Bug)"
        labels.append("bug")
    elif any(k in text for k in ("предложить идею", "фича", "feature", "добавить", "функция", "улучшение")):
        issue_type = "Улучшение (Enhancement)"
        labels.append("enhancement")
    elif any(k in text for k in ("документация непонятна", "документ", "тз", "словарь")):
        issue_type = "Документация"
        labels.append("documentation")
    else:
        labels.append("question")

    # 2. Предполагаемая область и модуль.
    # Слишком общий маркер "задач" намеренно не используется:
    # он встречается в самом названии формы "[Техзадача]".
    domain = "Общий / Не определен"
    module = "Core / Не определен"
    confidence = "LOW"
    requires_manual_review = True

    sec_keys = ("security", "безопасн", "secret", "секрет", "парол", "токен", "grant", "права доступа", "уязвимост")
    ui_keys = ("electron", "ui", "интерфейс", "кнопк", "html", "отображени", "виджет", "css")
    worker_keys = ("worker", "коворкер", "исполнител", "lease", "claim", "heartbeat")
    ctx_keys = ("контекст", "context", "база знаний", "knowledge", "ресурс", "resource")
    infra_keys = ("ci", "github actions", "workflow", "triage", "quality", "линтер", "тест")
    docs_keys = ("документ", "тз", "архитектур", "словарь", "раздел")

    if any(k in text for k in sec_keys):
        domain = "Security & Governance"
        module = "Security / Secret Store"
        confidence = "HIGH"
        requires_manual_review = False
    elif any(k in text for k in ui_keys):
        domain = "User Experience & Visualization"
        module = "Desktop Shell (Electron) / Visualization"
        confidence = "HIGH"
        requires_manual_review = False
    elif any(k in text for k in worker_keys):
        domain = "Task Execution & Workers"
        module = "Coworker / Execution"
        confidence = "HIGH"
        requires_manual_review = False
    elif any(k in text for k in ctx_keys):
        domain = "Information & Context"
        module = "Context / Knowledge Base / Resources"
        confidence = "HIGH"
        requires_manual_review = False
    elif any(k in text for k in infra_keys):
        domain = "Engineering & Infrastructure"
        module = "QA / CI Infrastructure"
        confidence = "HIGH"
        requires_manual_review = False
    elif any(k in text for k in docs_keys):
        domain = "Architecture & Documentation"
        module = "Documentation / Specifications"
        confidence = "HIGH"
        requires_manual_review = False

    # 3. Приоритет-кандидат.
    priority = "P2 (Стандартный кандидат)"
    if domain == "Security & Governance" or "секрет" in text or "уязвимост" in text:
        priority = "P0 (Критический кандидат)"
    elif any(k in text for k in ("ошибка", "сломал", "crash", "не работает")):
        priority = "P1 (Важный кандидат)"

    # 4. Необходимость USER / ADMIN Approval.
    decision_level = "Не требуется (стандартная работа)"
    if domain == "Security & Governance" or any(k in text for k in ("admin", "администратор", "секрет", "доступ")):
        decision_level = "Требуется ADMIN Approval"
    elif any(k in text for k in ("выбор", "согласован", "пользовател", "user")):
        decision_level = "Требуется USER Decision"

    return {
        "issue_type": issue_type,
        "labels": labels,
        "domain_candidate": domain,
        "module_candidate": module,
        "priority_candidate": priority,
        "decision_level": decision_level,
        "confidence": confidence,
        "requires_manual_review": requires_manual_review,
    }


def format_triage_comment(classification: Dict[str, Any], owner: str, repo: str) -> str:
    review_notice = (
        "⚠️ **Внимание:** уровень уверенности автоматического классификатора **LOW**. Требуется ручной разбор координатором проекта."
        if classification["requires_manual_review"]
        else "✅ Предварительная классификация выполнена автоматически с высокой уверенностью (**HIGH**)."
    )

    lines = [
        "Приветствуем! Спасибо за обращение в KAT9I_OS.",
        "",
        "Это обращение зарегистрировано и обработано системой первичного автоматического разбора (**triage**):",
        "",
        f"- **Тип обращения:** {classification['issue_type']}",
        f"- **Предполагаемый Domain (кандидат):** {classification['domain_candidate']}",
        f"- **Предполагаемый модуль (кандидат):** {classification['module_candidate']}",
        f"- **Рекомендуемый приоритет:** {classification['priority_candidate']}",
        f"- **Уровень решения:** {classification['decision_level']}",
        "",
        review_notice,
        "",
        "> [!NOTE]",
        "> Данные оценки являются предварительными рекомендациями робота-помощника (DATA) и не наделяют процессами CONTROL или автоматическими правами.",
        "",
        "**Полезные материалы для старта:**",
        f"- [Режим «Я здесь впервые»](https://github.com/{owner}/{repo}/blob/main/docs/guides/FIRST_TIME_GUIDE.md)",
        f"- [Словарь терминов KAT9I_OS](https://github.com/{owner}/{repo}/blob/main/docs/GLOSSARY.md)",
        f"- [GitHub для коворкеров](https://github.com/{owner}/{repo}/blob/main/docs/guides/GITHUB_FOR_COWORKERS.md)",
    ]
    return "\n".join(lines)
