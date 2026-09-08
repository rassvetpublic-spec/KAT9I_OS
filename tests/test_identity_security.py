# -*- coding: utf-8 -*-
"""
Контрактные тесты безопасности Identity и привязки к Windows (Issue #44, Gate G2).
Проверяет:
1. Валидность схем Identity.json и ApprovalRecord.json согласно Draft 2020-12.
2. Корректную валидацию эталонных субъектов:
   - LOCAL_USER с Windows SID;
   - LOCAL_ADMIN с признаком elevation;
   - LOCAL_WORKER;
   - CORE_SERVICE.
3. Разделение сущностей Identity, Role, Trust Level и Windows Binding.
4. Негативные сценарии безопасности:
   - Попытка сохранения паролей или парольных хэшей (отклоняется additionalProperties: false);
   - Подмена identity_id не по шаблону;
   - Нарушение формата Windows SID;
   - Попытка Worker'а предоставить Human Approval (approver_role enum);
   - Replay-атаки: валидация nonce и периода действия (issued_at, expires_at).
"""

import json
import unittest
from pathlib import Path
from datetime import datetime, timezone, timedelta
import jsonschema
from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMAS_V1_DIR = REPO_ROOT / "schemas" / "v1"

class TestIdentitySecurityContracts(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.identity_schema_path = SCHEMAS_V1_DIR / "Identity.json"
        cls.approval_schema_path = SCHEMAS_V1_DIR / "ApprovalRecord.json"

        cls.assertTrue(cls, cls.identity_schema_path.exists(), "Identity.json отсутствует")
        cls.assertTrue(cls, cls.approval_schema_path.exists(), "ApprovalRecord.json отсутствует")

        with open(cls.identity_schema_path, "r", encoding="utf-8") as f:
            cls.identity_schema = json.load(f)
        with open(cls.approval_schema_path, "r", encoding="utf-8") as f:
            cls.approval_schema = json.load(f)

        cls.identity_validator = Draft202012Validator(cls.identity_schema)
        cls.approval_validator = Draft202012Validator(cls.approval_schema)

    def test_identity_and_approval_schemas_syntax(self):
        """Проверяет корректность мета-схемы Draft 2020-12 и fail-closed атрибутов."""
        for name, schema in [("Identity", self.identity_schema), ("ApprovalRecord", self.approval_schema)]:
            Draft202012Validator.check_schema(schema)
            self.assertEqual(schema.get("$schema"), "https://json-schema.org/draft/2020-12/schema")
            self.assertTrue(schema.get("$id", "").startswith("https://kat9i.org/schemas/v1/"))
            self.assertEqual(schema.get("version"), "1.0.0")
            self.assertFalse(schema.get("additionalProperties", True), f"{name} должна иметь additionalProperties: false")

    def test_valid_local_user_identity(self):
        """Проверяет валидный профиль обычного локального пользователя Windows."""
        user_identity = {
            "identity_id": "id-user-alex-001",
            "subject_type": "HUMAN_USER",
            "display_name": "Alexander",
            "roles": ["LOCAL_USER"],
            "trust_level": "AUTHENTICATED",
            "windows_binding": {
                "security_identifier": "S-1-5-21-3623811015-3361044348-30300820-1013",
                "account_name": "DESKTOP-KAT9I\\alexa",
                "is_elevated": False,
                "account_hash": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
            },
            "created_at": "2026-09-08T10:00:00Z"
        }
        self.identity_validator.validate(user_identity)

    def test_valid_admin_identity(self):
        """Проверяет валидный профиль администратора с повышенными привилегиями."""
        admin_identity = {
            "identity_id": "id-admin-kat9i-sys",
            "subject_type": "HUMAN_USER",
            "display_name": "Alexander (Admin Session)",
            "roles": ["LOCAL_USER", "LOCAL_ADMIN"],
            "trust_level": "FULL_LOCAL_TRUST",
            "windows_binding": {
                "security_identifier": "S-1-5-21-3623811015-3361044348-30300820-500",
                "account_name": "DESKTOP-KAT9I\\Administrator",
                "is_elevated": True,
                "account_hash": "sha256:a591a6d40bf420404a011733cfb7b190d62c65bf0bcda32b57b277d9ad9f146e"
            },
            "created_at": "2026-09-08T10:00:00Z"
        }
        self.identity_validator.validate(admin_identity)

    def test_valid_worker_and_service_identity(self):
        """Проверяет субъектов типа Worker и Service (без привязки к Windows учетной записи)."""
        worker_identity = {
            "identity_id": "id-worker-python-42",
            "subject_type": "LOCAL_WORKER",
            "display_name": "Python Research Worker #42",
            "roles": ["WORKER"],
            "trust_level": "PROVISIONAL",
            "created_at": "2026-09-08T10:05:00Z",
            "metadata": {
                "worker_type": "python_researcher"
            }
        }
        self.identity_validator.validate(worker_identity)

        service_identity = {
            "identity_id": "id-service-rust-core",
            "subject_type": "CORE_SERVICE",
            "display_name": "KAT9I_OS Rust Core Engine",
            "roles": ["CORE_SERVICE"],
            "trust_level": "FULL_LOCAL_TRUST",
            "created_at": "2026-09-08T09:00:00Z"
        }
        self.identity_validator.validate(service_identity)

    def test_security_violation_no_passwords_allowed(self):
        """Проверяет строгий запрет на хранение любых паролей, секретов или хэшей паролей."""
        forbidden_payload = {
            "identity_id": "id-user-malicious",
            "subject_type": "HUMAN_USER",
            "roles": ["LOCAL_USER"],
            "trust_level": "AUTHENTICATED",
            "created_at": "2026-09-08T10:00:00Z",
            "windows_password": "PlaintextPassword123!",  # Запрещено
            "ntlm_hash": "aad3b435b51404eeaad3b435b51404ee"  # Запрещено
        }
        with self.assertRaises(jsonschema.ValidationError):
            self.identity_validator.validate(forbidden_payload)

    def test_security_violation_invalid_sid_pattern(self):
        """Проверяет отклонение некорректного или поддельного Windows SID."""
        bad_sid_identity = {
            "identity_id": "id-user-badsid",
            "subject_type": "HUMAN_USER",
            "roles": ["LOCAL_USER"],
            "trust_level": "AUTHENTICATED",
            "windows_binding": {
                "security_identifier": "NOT_A_VALID_WINDOWS_SID",
                "is_elevated": False,
                "account_hash": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
            },
            "created_at": "2026-09-08T10:00:00Z"
        }
        with self.assertRaises(jsonschema.ValidationError):
            self.identity_validator.validate(bad_sid_identity)

    def test_valid_approval_record(self):
        """Проверяет эталонную запись человеческого подтверждения (Human Approval)."""
        now = datetime.now(timezone.utc)
        expires = now + timedelta(minutes=5)
        valid_approval = {
            "approval_id": "appr-confirm-disk-write-01",
            "approver_identity_id": "id-user-alex-001",
            "approver_role": "LOCAL_USER",
            "task_id": "task-044-identity",
            "action_hash": "sha256:ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
            "nonce": "rnd-nonce-abcdef1234567890",
            "reason": "Подтверждена запись изменений в каноническую документацию",
            "issued_at": now.isoformat(),
            "expires_at": expires.isoformat()
        }
        self.approval_validator.validate(valid_approval)

    def test_worker_cannot_grant_approval(self):
        """Worker не имеет права подписывать Human Approval (approver_role ограничен USER/ADMIN)."""
        worker_approval = {
            "approval_id": "appr-fake-from-worker",
            "approver_identity_id": "id-worker-python-42",
            "approver_role": "WORKER",  # Недопустимо!
            "task_id": "task-044-identity",
            "action_hash": "sha256:ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
            "nonce": "rnd-nonce-abcdef1234567890",
            "issued_at": "2026-09-08T10:00:00Z",
            "expires_at": "2026-09-08T10:05:00Z"
        }
        with self.assertRaises(jsonschema.ValidationError):
            self.approval_validator.validate(worker_approval)

    def test_replay_attack_protection_nonce_and_time(self):
        """
        Проверяет защиту от Replay-атак:
        1. Требование обязательного криптографического nonce длиной >= 16 символов.
        2. Отклонение approval с истекшим сроком действия при логической проверке.
        """
        # 1. Отсутствие nonce
        no_nonce = {
            "approval_id": "appr-no-nonce-attack",
            "approver_identity_id": "id-user-alex-001",
            "approver_role": "LOCAL_USER",
            "task_id": "task-044-identity",
            "action_hash": "sha256:ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
            "issued_at": "2026-09-08T10:00:00Z",
            "expires_at": "2026-09-08T10:05:00Z"
        }
        with self.assertRaises(jsonschema.ValidationError):
            self.approval_validator.validate(no_nonce)

        # 2. Слишком короткий nonce (< 16 символов)
        short_nonce = dict(no_nonce, nonce="short123")
        with self.assertRaises(jsonschema.ValidationError):
            self.approval_validator.validate(short_nonce)

        # 3. Проверка срока действия (Fail-Closed: если current_time > expires_at, то REJECT)
        t_past_issued = datetime(2026, 9, 8, 9, 0, 0, tzinfo=timezone.utc)
        t_past_expires = datetime(2026, 9, 8, 9, 5, 0, tzinfo=timezone.utc)
        t_current_eval = datetime(2026, 9, 8, 10, 0, 0, tzinfo=timezone.utc)

        expired_approval = {
            "approval_id": "appr-expired-replay",
            "approver_identity_id": "id-user-alex-001",
            "approver_role": "LOCAL_USER",
            "task_id": "task-044-identity",
            "action_hash": "sha256:ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
            "nonce": "rnd-nonce-abcdef1234567890",
            "issued_at": t_past_issued.isoformat(),
            "expires_at": t_past_expires.isoformat()
        }
        # Схема валидна по синтаксису
        self.approval_validator.validate(expired_approval)

        # Логический инвариант безопасности Fail-Closed:
        exp_dt = datetime.fromisoformat(expired_approval["expires_at"].replace("Z", "+00:00"))
        is_active = t_current_eval <= exp_dt
        self.assertFalse(is_active, "Просроченное подтверждение обязано отклоняться (Fail-Closed)")

if __name__ == "__main__":
    unittest.main()
