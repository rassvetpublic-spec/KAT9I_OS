# -*- coding: utf-8 -*-
"""
Контрактные тесты для канонических машинных схем KAT9I_OS (Issue #40, Gate G2).
Проверяет:
1. Синтаксическую и семантическую валидность JSON Schema в schemas/v1/.
2. Корректную валидацию эталонных валидных сообщений для всех 7 сущностей.
3. Отклонение невалидных данных (нарушение required, enum, pattern, additionalProperties).
4. Правила версионирования SemVer.
"""

import json
import unittest
from pathlib import Path
import jsonschema
import referencing
from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMAS_V1_DIR = REPO_ROOT / "schemas" / "v1"

class TestCanonicalContractSchemas(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.schema_files = [
            "TaskContract.json",
            "TaskRuntimeState.json",
            "TaskResult.json",
            "Evidence.json",
            "SecurityDecision.json",
            "CapabilityGrant.json",
            "SystemEvent.json",
            "CacheEntry.json",
            "PayloadRef.json"
        ]
        cls.schemas = {}
        cls.registry = referencing.Registry()
        for sf in cls.schema_files:
            p = SCHEMAS_V1_DIR / sf
            cls.assertTrue(cls, p.exists(), f"Файл схемы {sf} отсутствует в {SCHEMAS_V1_DIR}")
            with open(p, "r", encoding="utf-8") as f:
                schema_dict = json.load(f)
                cls.schemas[sf] = schema_dict
                res = referencing.Resource.from_contents(schema_dict)
                cls.registry = cls.registry.with_resource(sf, res)
                if "$id" in schema_dict:
                    cls.registry = cls.registry.with_resource(schema_dict["$id"], res)

    def test_all_schemas_are_valid_draft202012(self):
        """Проверяет, что все схемы синтаксически корректны согласно мета-схеме Draft 2020-12."""
        for sf, schema in self.schemas.items():
            Draft202012Validator.check_schema(schema)
            self.assertEqual(schema.get("$schema"), "https://json-schema.org/draft/2020-12/schema")
            self.assertTrue(schema.get("$id", "").startswith("https://kat9i.org/schemas/v1/"))
            self.assertEqual(schema.get("version"), "1.0.0")
            self.assertFalse(schema.get("additionalProperties", True), f"Схема {sf} обязана иметь additionalProperties: False")

    def test_task_contract_valid_and_invalid(self):
        """Проверяет контракт TaskContract."""
        schema = self.schemas["TaskContract.json"]
        validator = Draft202012Validator(schema)

        valid_contract = {
            "task_id": "task-001-setup",
            "parent_task_id": None,
            "source": "github_issue",
            "goal": "Разработать канонические машинные контракты",
            "workspace": "C:\\GIT\\KAT9I_OS",
            "domain": "architecture",
            "scope": {
                "repository": "rassvetpublic-spec/KAT9I_OS",
                "allowed_paths": ["schemas/", "tests/"],
                "denied_paths": [".git/"],
                "allowed_operations": ["read", "write"],
                "network_allowed": False
            },
            "context_refs": ["docs/architecture/03_TASK_CONTRACT.md"],
            "rules_ref": "canonical",
            "required_capabilities": ["FS_READ", "FS_WRITE_WORKSPACE"],
            "output_contract": {
                "expected_artifacts": ["schemas/v1/TaskContract.json"],
                "quality_gate_required": True,
                "independent_qa_required": True
            },
            "result_sink": "local_workspace",
            "created_at": "2026-09-08T10:00:00Z"
        }
        self.assertTrue(validator.is_valid(valid_contract))

        # Нарушение: отсутствует обязательное поле goal
        invalid_missing = dict(valid_contract)
        del invalid_missing["goal"]
        self.assertFalse(validator.is_valid(invalid_missing))

        # Нарушение: передано неизвестное поле (Fail-Closed)
        invalid_extra = dict(valid_contract)
        invalid_extra["injected_param"] = "malicious_data"
        self.assertFalse(validator.is_valid(invalid_extra))

        # Нарушение: некорректный task_id (недопустимые символы)
        invalid_id = dict(valid_contract)
        invalid_id["task_id"] = "bad id with spaces!"
        self.assertFalse(validator.is_valid(invalid_id))

    def test_task_runtime_state_valid_and_invalid(self):
        """Проверяет контракт TaskRuntimeState."""
        schema = self.schemas["TaskRuntimeState.json"]
        validator = Draft202012Validator(schema)

        valid_state = {
            "task_id": "task-001",
            "status": "ACTIVE",
            "worker_id": "worker-agy",
            "progress_percent": 75,
            "current_step": "Компиляция контрактов",
            "checkpoint_id": "chk-001",
            "error_message": None,
            "updated_at": "2026-09-08T10:05:00Z"
        }
        self.assertTrue(validator.is_valid(valid_state))

        # Нарушение: недопустимый enum статуса
        invalid_status = dict(valid_state)
        invalid_status["status"] = "UNKNOWN_STATUS"
        self.assertFalse(validator.is_valid(invalid_status))

        # Нарушение: progress_percent > 100
        invalid_percent = dict(valid_state)
        invalid_percent["progress_percent"] = 150
        self.assertFalse(validator.is_valid(invalid_percent))

    def test_task_result_valid_and_invalid(self):
        """Проверяет контракт TaskResult."""
        schema = self.schemas["TaskResult.json"]
        validator = Draft202012Validator(schema)

        valid_result = {
            "task_id": "task-001",
            "verdict": "SUCCESS",
            "summary": "Контракты разработаны и протестированы",
            "artifacts": [
                {
                    "path": "schemas/v1/TaskContract.json",
                    "hash_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                    "size_bytes": 1024,
                    "description": "Схема TaskContract"
                }
            ],
            "evidence_ref": "ev-001-verification",
            "completed_at": "2026-09-08T10:10:00Z",
            "duration_ms": 5400
        }
        self.assertTrue(validator.is_valid(valid_result))

        # Нарушение: невалидный hash_sha256 (короче 64 hex)
        invalid_hash = dict(valid_result)
        invalid_hash["artifacts"] = [{
            "path": "test.txt",
            "hash_sha256": "not-a-sha256",
            "size_bytes": 10
        }]
        self.assertFalse(validator.is_valid(invalid_hash))

    def test_evidence_valid_and_invalid(self):
        """Проверяет контракт Evidence."""
        schema = self.schemas["Evidence.json"]
        validator = Draft202012Validator(schema)

        valid_evidence = {
            "evidence_id": "ev-task-001-qa",
            "task_id": "task-001",
            "source_revision": "a395d4f0ff2abf4ff9de9ae866c7c7bb026622fa",
            "test_results": {
                "total": 14,
                "passed": 14,
                "failed": 0,
                "exit_code": 0,
                "summary": "14 tests ran, 0 failed"
            },
            "qa_verdict": "PASS",
            "qa_worker": "worker-chatgpt",
            "notes": "Независимый QA подтверждён",
            "created_at": "2026-09-08T10:15:00Z"
        }
        self.assertTrue(validator.is_valid(valid_evidence))

        # Нарушение: неизвестный вердикт QA
        invalid_qa = dict(valid_evidence)
        invalid_qa["qa_verdict"] = "MAYBE"
        self.assertFalse(validator.is_valid(invalid_qa))

    def test_security_decision_valid_and_invalid(self):
        """Проверяет контракт SecurityDecision."""
        schema = self.schemas["SecurityDecision.json"]
        validator = Draft202012Validator(schema)

        valid_decision = {
            "decision_id": "sec-chk-001-allow",
            "task_id": "task-001",
            "worker_id": "worker-agy",
            "action": {
                "operation": "WRITE_FILE",
                "target": "schemas/v1/TaskContract.json"
            },
            "verdict": "ALLOW",
            "reason": "Путь входит в разрешённый Scope",
            "decided_at": "2026-09-08T10:02:00Z"
        }
        self.assertTrue(validator.is_valid(valid_decision))

        # Нарушение: недопустимая операция
        invalid_op = dict(valid_decision)
        invalid_op["action"] = {"operation": "DROP_DATABASE", "target": "all"}
        self.assertFalse(validator.is_valid(invalid_op))

    def test_capability_grant_valid_and_invalid(self):
        """Проверяет контракт CapabilityGrant."""
        schema = self.schemas["CapabilityGrant.json"]
        validator = Draft202012Validator(schema)

        valid_grant = {
            "grant_id": "cap-grant-001",
            "grantee_id": "worker-agy",
            "capabilities": ["FS_READ", "FS_WRITE_WORKSPACE"],
            "isolation_level": "JOB_OBJECT",
            "expires_at": "2026-09-08T12:00:00Z",
            "issued_at": "2026-09-08T10:00:00Z"
        }
        self.assertTrue(validator.is_valid(valid_grant))

        # Нарушение: пустой список capabilities (minItems: 1)
        invalid_caps = dict(valid_grant)
        invalid_caps["capabilities"] = []
        self.assertFalse(validator.is_valid(invalid_caps))

    def test_system_event_valid_and_invalid(self):
        """Проверяет контракт SystemEvent."""
        schema = self.schemas["SystemEvent.json"]
        validator = Draft202012Validator(schema)

        valid_event = {
            "event_id": "evt-001-created",
            "event_type": "TASK_CREATED",
            "source_module": "Core.Scheduler",
            "task_id": "task-001",
            "payload": {"goal": "Тестовая задача", "priority": "P0"},
            "timestamp": "2026-09-08T10:00:01Z"
        }
        self.assertTrue(validator.is_valid(valid_event))

        # Нарушение: недопустимый event_type
        invalid_type = dict(valid_event)
        invalid_type["event_type"] = "INVALID_EVENT_TYPE"
        self.assertFalse(validator.is_valid(invalid_type))

    def test_cache_entry_valid_and_invalid(self):
        """Проверяет контракт CacheEntry (Issue #84)."""
        schema = self.schemas["CacheEntry.json"]
        validator = Draft202012Validator(schema, registry=self.registry)

        valid_payload_ref = {
            "payload_id": "pay-001-symbols",
            "storage_mode": "RAM_REGION",
            "byte_size": 2048,
            "checksum": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "checksum_algorithm": "SHA-256",
            "created_at": "2026-09-08T10:00:00Z"
        }

        valid_entry = {
            "schema_version": "1.0.0",
            "key": "AST_SYMBOL:core.rs:rev-123:parser:1.0.0:SESSION_LOCAL:session-42",
            "namespace": "AST_SYMBOL",
            "source_ref": "src/core.rs",
            "revision": "rev-123",
            "hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "transform_id": "tree_sitter_rust",
            "transform_version": "0.20.0",
            "payload_ref": valid_payload_ref,
            "created_at": "2026-09-08T10:00:00Z",
            "hit_count": 0,
            "scope": "SESSION_LOCAL",
            "owner_id": "session-42"
        }
        self.assertTrue(validator.is_valid(valid_entry))

        # SYSTEM_GLOBAL без owner_id валиден
        valid_global_entry = dict(valid_entry)
        valid_global_entry["scope"] = "SYSTEM_GLOBAL"
        valid_global_entry["owner_id"] = None
        self.assertTrue(validator.is_valid(valid_global_entry))

        # Нарушение: SESSION_LOCAL без owner_id
        invalid_no_owner = dict(valid_entry)
        del invalid_no_owner["owner_id"]
        self.assertFalse(validator.is_valid(invalid_no_owner))

        # Нарушение: отсутствие schema_version
        invalid_no_version = dict(valid_entry)
        del invalid_no_version["schema_version"]
        self.assertFalse(validator.is_valid(invalid_no_version))

        # Нарушение вложенного контракта: пустой payload_ref или отсутствующие required поля
        invalid_nested = dict(valid_entry)
        invalid_nested["payload_ref"] = {}
        self.assertFalse(validator.is_valid(invalid_nested))

        # Нарушение вложенного контракта: недопустимый storage_mode во вложенном объекте
        invalid_nested_mode = dict(valid_entry)
        invalid_nested_mode["payload_ref"] = dict(valid_payload_ref, storage_mode="INVALID_MODE")
        self.assertFalse(validator.is_valid(invalid_nested_mode))

        # Нарушение: попытка передать дублирующий top-level checksum (additionalProperties: false)
        invalid_dup_checksum = dict(valid_entry)
        invalid_dup_checksum["checksum"] = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        self.assertFalse(validator.is_valid(invalid_dup_checksum))

        # Нарушение: недопустимый namespace
        invalid_entry = dict(valid_entry)
        invalid_entry["namespace"] = "INVALID_NS"
        self.assertFalse(validator.is_valid(invalid_entry))

        # Нарушение: additionalProperties
        invalid_props = dict(valid_entry)
        invalid_props["unknown_prop"] = "leak"
        self.assertFalse(validator.is_valid(invalid_props))

    def test_payload_ref_valid_and_invalid(self):
        """Проверяет контракт PayloadRef (Issue #84)."""
        schema = self.schemas["PayloadRef.json"]
        validator = Draft202012Validator(schema)

        valid_payload = {
            "payload_id": "pay-002-spill",
            "storage_mode": "SPILL_SEGMENT",
            "byte_size": 1048576,
            "checksum": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "checksum_algorithm": "SHA-256",
            "segment_id": "seg-001-immutable",
            "offset": 4096,
            "created_at": "2026-09-08T10:00:00Z"
        }
        self.assertTrue(validator.is_valid(valid_payload))

        # Проверка BLAKE3 алгоритма
        valid_blake3 = dict(valid_payload)
        valid_blake3["checksum_algorithm"] = "BLAKE3"
        self.assertTrue(validator.is_valid(valid_blake3))

        # Нарушение: невалидный алгоритм контрольной суммы
        invalid_alg = dict(valid_payload)
        invalid_alg["checksum_algorithm"] = "MD5"
        self.assertFalse(validator.is_valid(invalid_alg))

        # Нарушение: не 64-символьный хэш
        invalid_hash_len = dict(valid_payload)
        invalid_hash_len["checksum"] = "abcd1234"
        self.assertFalse(validator.is_valid(invalid_hash_len))

        # Нарушение SPILL_SEGMENT: отсутствует segment_id
        invalid_spill_no_seg = dict(valid_payload)
        del invalid_spill_no_seg["segment_id"]
        self.assertFalse(validator.is_valid(invalid_spill_no_seg))

        # Нарушение SPILL_SEGMENT: отсутствует offset
        invalid_spill_no_offset = dict(valid_payload)
        del invalid_spill_no_offset["offset"]
        self.assertFalse(validator.is_valid(invalid_spill_no_offset))

        # Проверка MMAP с mmap_path
        valid_mmap = {
            "payload_id": "pay-004-mmap",
            "storage_mode": "MMAP",
            "byte_size": 2097152,
            "checksum": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "checksum_algorithm": "SHA-256",
            "mmap_path": "C:\\GIT\\KAT9I_OS\\data\\cache\\mapped.bin",
            "offset": 0,
            "created_at": "2026-09-08T10:00:00Z"
        }
        self.assertTrue(validator.is_valid(valid_mmap))

        # Нарушение MMAP: отсутствует и mmap_path, и segment_id
        invalid_mmap_no_target = {
            "payload_id": "pay-004-mmap",
            "storage_mode": "MMAP",
            "byte_size": 2097152,
            "checksum": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "checksum_algorithm": "SHA-256",
            "offset": 0,
            "created_at": "2026-09-08T10:00:00Z"
        }
        self.assertFalse(validator.is_valid(invalid_mmap_no_target))

        # Проверка RAM_REGION
        valid_ram = {
            "payload_id": "pay-003-ram-region",
            "storage_mode": "RAM_REGION",
            "byte_size": 1024,
            "checksum": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "checksum_algorithm": "SHA-256",
            "created_at": "2026-09-08T10:00:00Z"
        }
        self.assertTrue(validator.is_valid(valid_ram))

        # Проверка INLINE с inline_data
        valid_inline = {
            "payload_id": "pay-005-inline",
            "storage_mode": "INLINE",
            "byte_size": 13,
            "checksum": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "checksum_algorithm": "SHA-256",
            "inline_data": "SGVsbG8sIFdvcmxkIQ==",
            "created_at": "2026-09-08T10:00:00Z"
        }
        self.assertTrue(validator.is_valid(valid_inline))

        # Нарушение INLINE: отсутствует inline_data
        invalid_inline_no_data = {
            "payload_id": "pay-005-inline",
            "storage_mode": "INLINE",
            "byte_size": 13,
            "checksum": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "checksum_algorithm": "SHA-256",
            "created_at": "2026-09-08T10:00:00Z"
        }
        self.assertFalse(validator.is_valid(invalid_inline_no_data))

        # Нарушение: недопустимый storage_mode (например, устаревший IN_RAM)
        invalid_mode = dict(valid_payload)
        invalid_mode["storage_mode"] = "IN_RAM"
        self.assertFalse(validator.is_valid(invalid_mode))

if __name__ == "__main__":
    unittest.main()
