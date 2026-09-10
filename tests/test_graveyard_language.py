import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from graveyard_capture import capture
from graveyard_language import add_russian_explanations, is_russian_first, normalize_graveyard_text


class GraveyardLanguageTests(unittest.TestCase):
    def test_known_technical_term_gets_russian_explanation(self):
        text, added = add_russian_explanations("ContextRef используется для безопасного контекста.")
        self.assertIn("ContextRef — ссылка на источник контекста", text)
        self.assertIn("ContextRef", added)

    def test_dynamic_term_gets_russian_explanation(self):
        text, added = add_russian_explanations(
            "VectorClock используется для согласования состояния.",
            {"VectorClock": "векторные часы для отслеживания причинного порядка событий"},
        )
        self.assertIn("VectorClock — векторные часы", text)
        self.assertIn("VectorClock", added)

    def test_non_russian_summary_fails_closed(self):
        with self.assertRaises(ValueError):
            normalize_graveyard_text("This is a long English technical summary without Russian explanation.")

    def test_russian_first_detection(self):
        self.assertTrue(is_russian_first("Основной текст написан по-русски, а API используется как технический термин."))

    def test_capture_dry_run_is_data_only_and_russian(self):
        payload = {
            "schema_version": "1.1.0",
            "project": "KAT9I_OS",
            "source_type": "TZ_DISCUSSION",
            "source_label": "Обсуждение архитектуры контекста",
            "captured_at": "2026-09-10T10:00:00Z",
            "canon_revision": "5baea2295937a083669dd7c3f6c613e397158f52",
            "title": "Сохранение знаний из обсуждений KAT9I_OS",
            "summary": "ContextRef используется для сохранения происхождения знания, а Graveyard не становится источником текущих задач.",
            "term_explanations": {},
            "knowledge_items": [
                {
                    "kind": "RATIONALE",
                    "text": "PromotionTicket применяется только при будущем переходе накопленного знания в рабочий контур.",
                    "canon_refs": ["docs/architecture/36_CHANGE_PROMOTION_PROTOCOL.md"],
                }
            ],
            "public_safe": True,
            "raw_chat_included": False,
            "actionable": False,
            "control": False,
            "canonical": False,
            "requires_owner_confirmation": False,
            "promotion_requires_owner_approval": True,
        }
        result = capture(payload, root=REPO_ROOT, dry_run=True)
        self.assertEqual(result["status"], "READY")
        self.assertEqual(result["entry"]["language"], "ru")
        self.assertFalse(result["entry"]["actionable"])
        self.assertFalse(result["entry"]["control"])
        self.assertIn("ContextRef", result["entry"]["auto_explanations"])
        self.assertIn("PromotionTicket", result["entry"]["auto_explanations"])


if __name__ == "__main__":
    unittest.main()
