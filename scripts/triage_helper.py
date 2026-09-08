# -*- coding: utf-8 -*-
"""
Детектор классификации обращений для triage KAT9I_OS (Issue #17, #39).
Анализирует текст обращения, предлагает Domain, модуль, приоритет-кандидат,
необходимость решения USER/ADMIN и уровень уверенности.
"""

import re
from typing import Dict, Any, List

def classify_issue_text(title: str, body: str) -> Dict[str, Any]:
    text = f"{title}\n{body}".lower()

    # 1. Тип обращения
    issue_type = "Вопрос / Обсуждение"
    labels = []
    if "сообщить об ошибке" in text or "баг" in text or "ошибка" in text or "crash" in text or "fail" in text:
        issue_type = "Ошибка (Bug)"
        labels.append("bug")
    elif "предложить идею" in text or "фича" in text or "feature" in text or "добавить" in text:
        issue_type = "Улучшение (Enhancement)"
        labels.append("enhancement")
    elif "документация непонятна" in text or "документ" in text or "тз" in text or "словарь" in text:
        issue_type = "Документация"
        labels.append("documentation")
    else:
        labels.append("question")

    # 2. Определение модуля и Domain
    domain = "Общий / Не определен"
    module = "Core / Не определен"
    confidence = "LOW"
    requires_manual_review = True

    if any(k in text for k in ["security", "безопасн", "secret", "секрет", "парол", "токен", "grant", "права доступа", "уязвимост"]):
        domain = "Security & Governance"
        module = "Security / Secret Store"
        confidence = "HIGH"
        requires_manual_review = False
    elif any(k in text for k in ["electron", "ui", "интерфейс", "кнопк", "html", "отображени", "виджет", "css"]):
        domain = "User Experience & Visualization"
        module = "Desktop Shell (Electron) / Visualization"
        confidence = "HIGH"
        requires_manual_review = False
    elif any(k in text for k in ["worker", "коворкер", "исполнител", "lease", "claim", "heartbeat", "задач"]):
        domain = "Task Execution & Workers"
        module = "Coworker / Execution"
        confidence = "HIGH"
        requires_manual_review = False
    elif any(k in text for k in ["контекст", "context", "база знаний", "knowledge", "ресурс", "resource"]):
        domain = "Information & Context"
        module = "Context / Knowledge Base / Resources"
        confidence = "HIGH"
        requires_manual_review = False
    elif any(k in text for k in ["ci", "github actions", "workflow", "triage", "quality", "линтер", "тест"]):
        domain = "Engineering & Infrastructure"
        module = "QA / CI Infrastructure"
        confidence = "HIGH"
        requires_manual_review = False
    elif any(k in text for k in ["документ", "тз", "архитектур", "словарь", "раздел"]):
        domain = "Architecture & Documentation"
        module = "Documentation / Specifications"
        confidence = "HIGH"
        requires_manual_review = False

    # 3. Приоритет-кандидат
    priority = "P2 (Обычный)"
    if "security" in module.lower() or "уязвимост" in text or "аварийная остановка" in text or "секрет" in text:
        priority = "P0 (Критический кандидат)"
    elif "ошибка" in text or "сломал" in text or "crash" in text or "не работает" in text:
        priority = "P1 (Важный кандидат)"
    elif issue_type == "Документация" or "вопрос" in text:
        priority = "P2 (Стандартный кандидат)"

    # 4. Необходимость USER / ADMIN Approval
    decision_level = "Не требуется (стандартная работа)"
    if "security" in module.lower() or "admin" in text or "администратор" in text or "секрет" in text or "доступ" in text:
        decision_level = "Требуется ADMIN Approval"
    elif "выбор" in text or "согласован" in text or "пользовател" in text or "user" in text:
        decision_level = "Требуется USER Decision"

    return {
        "issue_type": issue_type,
        "labels": labels,
        "domain_candidate": domain,
        "module_candidate": module,
        "priority_candidate": priority,
        "decision_level": decision_level,
        "confidence": confidence,
        "requires_manual_review": requires_manual_review
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
        f"- [GitHub для коворкеров](https://github.com/{owner}/{repo}/blob/main/docs/guides/GITHUB_FOR_COWORKERS.md)"
    ]
    return "\n".join(lines)