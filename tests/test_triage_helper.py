# -*- coding: utf-8 -*-
"""
Тесты для автоматического классификатора обращений triage_helper.py (Issue #17, #39).
"""

import unittest
from scripts.triage_helper import classify_issue_text, format_triage_comment

class TestTriageHelper(unittest.TestCase):

    def test_security_issue_classification(self):
        title = "Обнаружена утечка Secret token в логах"
        body = "При работе модуля произошла ошибка и токен попал в телеметрию."
        res = classify_issue_text(title, body)
        self.assertEqual(res["domain_candidate"], "Security & Governance")
        self.assertEqual(res["priority_candidate"], "P0 (Критический кандидат)")
        self.assertEqual(res["decision_level"], "Требуется ADMIN Approval")
        self.assertEqual(res["confidence"], "HIGH")
        self.assertFalse(res["requires_manual_review"])

    def test_ui_enhancement_classification(self):
        title = "Добавить кнопку переключения темы в интерфейс Electron"
        body = "Предложить идею: темная тема для десктопного окна."
        res = classify_issue_text(title, body)
        self.assertEqual(res["domain_candidate"], "User Experience & Visualization")
        self.assertEqual(res["issue_type"], "Улучшение (Enhancement)")
        self.assertIn("enhancement", res["labels"])
        self.assertEqual(res["confidence"], "HIGH")

    def test_documentation_classification(self):
        title = "Непонятный термин в разделе ТЗ"
        body = "Сказать, что документация непонятна в части словаря."
        res = classify_issue_text(title, body)
        self.assertEqual(res["domain_candidate"], "Architecture & Documentation")
        self.assertEqual(res["issue_type"], "Документация")
        self.assertIn("documentation", res["labels"])

    def test_low_confidence_requires_manual_review(self):
        title = "Что-то странное произошло вчера"
        body = "Привет всем, не знаю как объяснить."
        res = classify_issue_text(title, body)
        self.assertEqual(res["confidence"], "LOW")
        self.assertTrue(res["requires_manual_review"])

    def test_format_comment(self):
        res = classify_issue_text("Утечка секрета", "Нужно срочно закрыть доступ")
        comment = format_triage_comment(res, "rassvetpublic-spec", "KAT9I_OS")
        self.assertIn("Security & Governance", comment)
        self.assertIn("Требуется ADMIN Approval", comment)

if __name__ == "__main__":
    unittest.main()