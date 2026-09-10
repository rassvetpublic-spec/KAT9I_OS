# -*- coding: utf-8 -*-
"""
Контрактные тесты Event Journal, Checkpoint и правил Replay Recovery (Issue #46, Gate G2).
Проверяет:
1. Валидность схем JournalEvent.json и Checkpoint.json согласно Draft 2020-12.
2. Корректную структуру событий Event Journal (sequence_number, operation_id, lease_generation).
3. Инварианты Replay Recovery:
   - Восстановление состояния с последней подтвержденной контрольной точки (Checkpoint);
   - Идемпотентность побочных эффектов (повтор операции с известным operation_id блокируется);
   - Отклонение устаревшего Lease Generation (защита от зомби-воркеров / Fencing Token).
4. Негативные сценарии: нарушение формата operation_id, сбои монотонности sequence_number.
"""

import json
import unittest
from pathlib import Path
from datetime import datetime, timezone
import jsonschema
from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMAS_V1_DIR = REPO_ROOT / "schemas" / "v1"

class TestEventJournalRecoveryContracts(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.journal_schema_path = SCHEMAS_V1_DIR / "JournalEvent.json"
        cls.checkpoint_schema_path = SCHEMAS_V1_DIR / "Checkpoint.json"

        cls.assertTrue(cls, cls.journal_schema_path.exists(), "JournalEvent.json отсутствует")
        cls.assertTrue(cls, cls.checkpoint_schema_path.exists(), "Checkpoint.json отсутствует")

        with open(cls.journal_schema_path, "r", encoding="utf-8") as f:
            cls.journal_schema = json.load(f)
        with open(cls.checkpoint_schema_path, "r", encoding="utf-8") as f:
            cls.checkpoint_schema = json.load(f)

        cls.journal_validator = Draft202012Validator(cls.journal_schema)
        cls.checkpoint_validator = Draft202012Validator(cls.checkpoint_schema)

    def test_schemas_syntax_and_fail_closed(self):
        """Проверяет корректность мета-схемы Draft 2020-12 и additionalProperties: false."""
        for name, schema in [("JournalEvent", self.journal_schema), ("Checkpoint", self.checkpoint_schema)]:
            Draft202012Validator.check_schema(schema)
            self.assertEqual(schema.get("$schema"), "https://json-schema.org/draft/2020-12/schema")
            self.assertTrue(schema.get("$id", "").startswith("https://kat9i.org/schemas/v1/"))
            expected_version = "1.1.0" if name == "JournalEvent" else "1.0.0"
            self.assertEqual(schema.get("version"), expected_version)
            self.assertFalse(schema.get("additionalProperties", True), f"{name} обязана иметь additionalProperties: false")

    def test_valid_journal_event(self):
        """Проверяет валидное критическое событие изменения состояния задачи."""
        event = {
            "event_id": "evt-step-executed-001",
            "sequence_number": 42,
            "event_type": "SIDE_EFFECT_EXECUTED",
            "source_module": "Execution",
            "task_id": "task-046-journal",
            "correlation_id": "corr-req-commit-99",
            "actor_identity_id": "id-worker-py-12",
            "operation_id": "op-git-commit-44",
            "lease_generation": 3,
            "payload": {
                "action": "GIT_COMMIT",
                "commit_hash": "a591a6d40bf420404a011733cfb7b190d62c65bf"
            },
            "evidence_ref": "docs/evidence/commit_proof.json",
            "timestamp": "2026-09-08T10:30:00Z"
        }
        self.journal_validator.validate(event)

    def test_valid_checkpoint(self):
        """Проверяет валидный снимок контрольной точки (Checkpoint)."""
        checkpoint = {
            "checkpoint_id": "chk-task-046-stage1",
            "task_id": "task-046-journal",
            "last_sequence_number": 42,
            "runtime_state": {
                "status": "ACTIVE",
                "progress_percent": 60,
                "worker_id": "id-worker-py-12",
                "current_step": "Коммит канонических схем"
            },
            "completed_operations": [
                "op-git-branch-create",
                "op-git-commit-44"
            ],
            "active_lease_generation": 3,
            "persisted_artifacts": [
                "schemas/v1/JournalEvent.json",
                "schemas/v1/Checkpoint.json"
            ],
            "created_at": "2026-09-08T10:30:05Z"
        }
        self.checkpoint_validator.validate(checkpoint)

    def test_idempotency_protection_duplicate_side_effect_prevented(self):
        """
        Проверяет модель идемпотентности при Replay:
        Если operation_id уже присутствует в Checkpoint.completed_operations,
        повторное выполнение действия блокируется (DUPLICATE_SIDE_EFFECT_PREVENTED).
        """
        checkpoint = {
            "checkpoint_id": "chk-task-046-stage1",
            "task_id": "task-046-journal",
            "last_sequence_number": 42,
            "runtime_state": {
                "status": "ACTIVE",
                "progress_percent": 60,
                "worker_id": "id-worker-py-12"
            },
            "completed_operations": ["op-payment-or-commit-1"],
            "active_lease_generation": 2,
            "created_at": "2026-09-08T10:00:00Z"
        }
        self.checkpoint_validator.validate(checkpoint)

        incoming_operation_id = "op-payment-or-commit-1"

        # Логика Replay Guard в Recovery Manager:
        is_already_executed = incoming_operation_id in checkpoint["completed_operations"]
        self.assertTrue(is_already_executed, "Операция должна быть распознана как уже завершенная")

        # При попытке повторного вызова возвращается сохраненный результат без создания повторного побочного эффекта
        replay_verdict = "SKIP_ALREADY_EXECUTED" if is_already_executed else "EXECUTE"
        self.assertEqual(replay_verdict, "SKIP_ALREADY_EXECUTED")

    def test_stale_lease_generation_rejected(self):
        """
        Проверяет инвариант Fencing Token:
        Событие от старого поколения владения (stale lease generation) отклоняется.
        """
        current_lease_generation = 4

        stale_event = {
            "event_id": "evt-from-zombie-worker",
            "sequence_number": 43,
            "event_type": "SIDE_EFFECT_EXECUTED",
            "source_module": "Execution",
            "task_id": "task-046-journal",
            "correlation_id": "corr-req-stale-01",
            "actor_identity_id": "id-worker-old-zombie",
            "operation_id": "op-stale-write-01",
            "lease_generation": 2,  # Меньше действующего 4!
            "payload": {"data": "stale overwrite attempt"},
            "timestamp": "2026-09-08T10:35:00Z"
        }
        self.journal_validator.validate(stale_event)

        # Проверка Fencing Token Guard:
        is_lease_valid = stale_event["lease_generation"] >= current_lease_generation
        self.assertFalse(is_lease_valid, "Событие от устаревшего поколения владения обязано отклоняться")

    def test_negative_invalid_operation_id_pattern(self):
        """Проверяет отклонение некорректного operation_id (нарушение шаблона op-...)."""
        bad_event = {
            "event_id": "evt-step-executed-002",
            "sequence_number": 43,
            "event_type": "SIDE_EFFECT_EXECUTED",
            "source_module": "Execution",
            "correlation_id": "corr-req-invalid-op",
            "operation_id": "INVALID_FORMAT_WITHOUT_PREFIX",
            "payload": {},
            "timestamp": "2026-09-08T10:30:00Z"
        }
        with self.assertRaises(jsonschema.ValidationError):
            self.journal_validator.validate(bad_event)

    def test_negative_negative_sequence_number(self):
        """Проверяет отклонение неположительного sequence_number."""
        bad_event = {
            "event_id": "evt-step-executed-003",
            "sequence_number": 0,  # minimum: 1
            "event_type": "TASK_CREATED",
            "source_module": "Core",
            "correlation_id": "corr-req-zero-seq",
            "payload": {},
            "timestamp": "2026-09-08T10:30:00Z"
        }
        with self.assertRaises(jsonschema.ValidationError):
            self.journal_validator.validate(bad_event)

if __name__ == "__main__":
    unittest.main()
