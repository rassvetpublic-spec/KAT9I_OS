# -*- coding: utf-8 -*-
"""Тесты фактически исполняемого классификатора triage KAT9I_OS."""

import unittest

from scripts.triage_helper import classify_issue_text, format_triage_comment


class TestTriageHelper(unittest.TestCase):

    def test_security_issue_classification(self):
        res = classify_issue_text(
            "Обнаружена утечка Secret token в логах",
            "При работе модуля произошла ошибка и токен попал в телеметрию.",
        )
        self.assertEqual(res["domain_candidate"], "Security & Governance")
        self.assertEqual(res["priority_candidate"], "P0 (Критический кандидат)")
        self.assertEqual(res["decision_level"], "Требуется ADMIN Approval")
        self.assertEqual(res["confidence"], "HIGH")
        self.assertFalse(res["requires_manual_review"])

    def test_ui_enhancement_classification(self):
        res = classify_issue_text(
            "Добавить кнопку переключения темы в интерфейс Electron",
            "Предложить идею: темная тема для десктопного окна.",
        )
        self.assertEqual(res["domain_candidate"], "User Experience & Visualization")
        self.assertEqual(res["issue_type"], "Улучшение (Enhancement)")
        self.assertIn("enhancement", res["labels"])

    def test_documentation_classification(self):
        res = classify_issue_text(
            "Непонятный термин в разделе ТЗ",
            "Сказать, что документация непонятна в части словаря.",
        )
        self.assertEqual(res["domain_candidate"], "Architecture & Documentation")
        self.assertEqual(res["issue_type"], "Документация")
        self.assertIn("documentation", res["labels"])

    def test_low_confidence_requires_manual_review(self):
        res = classify_issue_text(
            "Что-то странное произошло вчера",
            "Привет всем, не знаю как объяснить.",
        )
        self.assertEqual(res["confidence"], "LOW")
        self.assertTrue(res["requires_manual_review"])

    def test_feature_form_prefix_is_enhancement(self):
        res = classify_issue_text("[Функция] экспорт CSV", "Нужно сохранить список.")
        self.assertEqual(res["issue_type"], "Улучшение (Enhancement)")
        self.assertIn("enhancement", res["labels"])

    def test_improvement_form_prefix_is_enhancement(self):
        res = classify_issue_text("[Улучшение] ускорить старт", "Обычная оптимизация.")
        self.assertEqual(res["issue_type"], "Улучшение (Enhancement)")
        self.assertIn("enhancement", res["labels"])

    def test_neutral_technical_task_does_not_become_worker_domain(self):
        res = classify_issue_text("[Техзадача] обновить настройки", "Нейтральная служебная работа.")
        self.assertEqual(res["issue_type"], "Техническая задача")
        self.assertEqual(res["domain_candidate"], "Общий / Не определен")
        self.assertEqual(res["confidence"], "LOW")
        self.assertTrue(res["requires_manual_review"])

    def test_technical_task_ci_is_infrastructure(self):
        res = classify_issue_text("[Техзадача] обновить CI", "Исправить workflow проверки.")
        self.assertEqual(res["domain_candidate"], "Engineering & Infrastructure")
        self.assertEqual(res["confidence"], "HIGH")

    def test_issue_form_boilerplate_does_not_trigger_security(self):
        body = (
            "Обычная задача по документации.\n"
            "- [x] Я не добавляю в Issue токены или секреты.\n"
            "- [x] Я проверил границы задачи и не добавляю секреты."
        )
        res = classify_issue_text("[Улучшение] поправить текст", body)
        self.assertNotEqual(res["domain_candidate"], "Security & Governance")
        self.assertNotEqual(res["priority_candidate"], "P0 (Критический кандидат)")

    def test_format_comment(self):
        res = classify_issue_text("Утечка секрета", "Нужно срочно закрыть доступ")
        comment = format_triage_comment(res, "rassvetpublic-spec", "KAT9I_OS")
        self.assertIn("Security & Governance", comment)
        self.assertIn("Требуется ADMIN Approval", comment)


if __name__ == "__main__":
    unittest.main()
