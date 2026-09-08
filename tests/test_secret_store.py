# -*- coding: utf-8 -*-
"""
Контрактные и отказные тесты безопасности Windows 11 Secret Store и SecretRef (Issue #45, Gate G3).

Проверяет:
1. Синтаксическую валидность схемы SecretRef.json по Draft 2020-12.
2. Сохранение секрета в защищённом хранилище и генерацию валидного SecretRef.
3. Доступ к секрету только при наличии Capability "SECRET_READ_SCOPED".
4. Отказ в доступе (Security Violation) при отсутствии прав у Worker.
5. Невозможность утечки секрета в обычный TaskContract, logs или индекс метаданных:
   - Проверка secrets_index.json на отсутствие открытого значения секрета.
6. Процедуру отзыва (Revocation): удаление секрета и невозможность дальнейшего доступа.
7. Проверку существования без раскрытия значения (check_exists).
"""

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from jsonschema import Draft202012Validator
from scripts.windows_secret_store import Kat9iSecretStore

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMAS_V1_DIR = REPO_ROOT / "schemas" / "v1"

class TestWindowsSecretStore(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        schema_path = SCHEMAS_V1_DIR / "SecretRef.json"
        cls.assertTrue(cls, schema_path.exists(), "SecretRef.json отсутствует")
        with open(schema_path, "r", encoding="utf-8") as f:
            cls.secret_ref_schema = json.load(f)
        cls.validator = Draft202012Validator(cls.secret_ref_schema)

    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp(prefix="kat9i_vault_test_"))
        self.store = Kat9iSecretStore(storage_dir=self.test_dir)

    def tearDown(self):
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_schema_validity(self):
        """Проверяет валидность схемы SecretRef.json."""
        Draft202012Validator.check_schema(self.secret_ref_schema)
        self.assertFalse(self.secret_ref_schema.get("additionalProperties", True))

    def test_store_and_access_with_valid_capability(self):
        """Проверяет создание секрета и доступ при наличии корректного CapabilityGrant."""
        raw_secret = "ghp_super_secret_production_token_12345"
        ref = self.store.store_secret("GITHUB_TOKEN", raw_secret, scope="USER_LOCAL")

        # 1. Проверка структуры SecretRef
        self.validator.validate(ref)
        self.assertEqual(ref["name"], "GITHUB_TOKEN")
        self.assertEqual(ref["provider"], "WINDOWS_DPAPI")

        # 2. Проверка, что в SecretRef нет открытого секрета
        self.assertNotIn(raw_secret, json.dumps(ref))

        # 3. Проверка метаданных на диске: в индексе secrets_index.json значение отсутствует
        with open(self.test_dir / "secrets_index.json", "r", encoding="utf-8") as f:
            index_content = f.read()
        self.assertNotIn(raw_secret, index_content, "Секрет НЕ ДОЛЖЕН храниться в метаданных открытым текстом!")

        # 4. Проверка существования
        self.assertTrue(self.store.check_exists(ref["secret_id"]))

        # 5. Извлечение с валидным CapabilityGrant
        valid_grant = {
            "grant_id": "cap-grant-valid-01",
            "capabilities": ["FS_READ", "SECRET_READ_SCOPED"]
        }
        retrieved_value = self.store.access_secret_value(ref["secret_id"], valid_grant)
        self.assertEqual(retrieved_value, raw_secret)

    def test_access_denied_without_capability(self):
        """Проверяет блокировку доступа для неавторизованного Worker без SECRET_READ_SCOPED."""
        raw_secret = "sk-openai-api-key-very-confidential"
        ref = self.store.store_secret("OPENAI_API_KEY", raw_secret)

        invalid_grant = {
            "grant_id": "cap-grant-unauthorized-02",
            "capabilities": ["FS_READ", "CMD_EXECUTE_SAFE"]  # Нет SECRET_READ_SCOPED!
        }

        with self.assertRaises(PermissionError) as ctx:
            self.store.access_secret_value(ref["secret_id"], invalid_grant)
        self.assertIn("denied without SECRET_READ_SCOPED", str(ctx.exception))

    def test_revocation_procedure(self):
        """Проверяет отзыв и удаление секрета (Revocation)."""
        raw_secret = "anthropic_secret_token_abc123"
        ref = self.store.store_secret("ANTHROPIC_KEY", raw_secret)
        secret_id = ref["secret_id"]

        self.assertTrue(self.store.check_exists(secret_id))

        # Отзыв
        revoked = self.store.revoke_secret(secret_id)
        self.assertTrue(revoked)
        self.assertFalse(self.store.check_exists(secret_id))

        valid_grant = {"capabilities": ["SECRET_READ_SCOPED"]}
        with self.assertRaises(KeyError):
            self.store.access_secret_value(secret_id, valid_grant)

    def test_nonexistent_secret_access(self):
        """Проверяет обращение к несуществующему secret_id."""
        valid_grant = {"capabilities": ["SECRET_READ_SCOPED"]}
        with self.assertRaises(KeyError):
            self.store.access_secret_value("sec-nonexistent-9999", valid_grant)

if __name__ == "__main__":
    unittest.main()
