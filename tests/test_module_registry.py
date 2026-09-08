# -*- coding: utf-8 -*-
"""
Тесты целостности реестра модулей и графа зависимостей KAT9I_OS (Issue #47, Gate G2).

Проверяет:
1. Соответствие schemas/v1/ModuleRegistry.json стандарту Draft 2020-12.
2. Корректность канонического modules_registry.json.
3. Определение битых ссылок на зависимости (UNKNOWN_DEPENDENCY).
4. Определение циклических зависимостей (CIRCULAR_DEPENDENCY_DETECTED).
5. Контроль уникальности канонической ответственности (ADR-032).
6. Контроль покрытия требуемых контрактов.
"""

import json
import copy
import unittest
from pathlib import Path
from jsonschema import Draft202012Validator
from scripts.verify_module_registry import ModuleRegistryVerifier, REGISTRY_FILE, SCHEMA_FILE

REPO_ROOT = Path(__file__).resolve().parent.parent

class TestModuleRegistry(unittest.TestCase):

    def setUp(self):
        with open(SCHEMA_FILE, "r", encoding="utf-8") as f:
            self.schema = json.load(f)
        with open(REGISTRY_FILE, "r", encoding="utf-8") as f:
            self.registry_data = json.load(f)

    def test_schema_valid_draft202012(self):
        """Проверяет валидность мета-схемы ModuleRegistry.json."""
        Draft202012Validator.check_schema(self.schema)
        self.assertEqual(self.schema.get("$schema"), "https://json-schema.org/draft/2020-12/schema")
        self.assertEqual(self.schema.get("title"), "ModuleRegistry")
        self.assertFalse(self.schema.get("additionalProperties", True))

    def test_canonical_registry_passes(self):
        """Проверяет, что канонический файл modules_registry.json проходит все проверки."""
        verifier = ModuleRegistryVerifier()
        topo = verifier.run_full_verification()
        self.assertEqual(len(topo), 8)
        self.assertIn("Core", topo)
        self.assertIn("Storage", topo)
        self.assertIn("Security", topo)
        self.assertIn("CacheEngine", topo)

    def test_detect_unknown_dependency(self):
        """Проверяет отклонение при наличии несуществующей зависимости."""
        bad_data = copy.deepcopy(self.registry_data)
        bad_data["modules"][0]["dependencies"].append("NonExistentModule")

        verifier = ModuleRegistryVerifier()
        verifier.data = bad_data
        verifier.modules = {m["module_id"]: m for m in bad_data["modules"]}

        with self.assertRaises(ValueError) as ctx:
            verifier.check_dependency_integrity()
        self.assertIn("NonExistentModule", str(ctx.exception))

    def test_detect_circular_dependency(self):
        """Проверяет обнаружение циклических зависимостей (DFS/DAG)."""
        bad_data = copy.deepcopy(self.registry_data)
        # Вносим цикл: Storage -> DesktopShell -> Storage
        storage_mod = next(m for m in bad_data["modules"] if m["module_id"] == "Storage")
        storage_mod["dependencies"].append("DesktopShell")

        verifier = ModuleRegistryVerifier()
        verifier.data = bad_data
        verifier.modules = {m["module_id"]: m for m in bad_data["modules"]}

        with self.assertRaises(ValueError) as ctx:
            verifier.detect_cycles_and_topological_sort()
        self.assertIn("CIRCULAR_DEPENDENCY_DETECTED", str(ctx.exception))

    def test_detect_duplicate_responsibility(self):
        """Проверяет соблюдение инварианта ADR-032 (один владелец канонической ответственности)."""
        bad_data = copy.deepcopy(self.registry_data)
        # Делаем двум модулям одинаковую ответственность
        resp = bad_data["modules"][0]["canonical_responsibility"]
        bad_data["modules"][1]["canonical_responsibility"] = resp

        verifier = ModuleRegistryVerifier()
        verifier.data = bad_data
        verifier.modules = {m["module_id"]: m for m in bad_data["modules"]}

        with self.assertRaises(ValueError) as ctx:
            verifier.check_unique_responsibility()
        self.assertIn("ADR-032", str(ctx.exception))

    def test_detect_uncovered_contract(self):
        """Проверяет обнаружение непокрытого контракта."""
        bad_data = copy.deepcopy(self.registry_data)
        # Модуль требует контракт, которого нет ни у кого
        bad_data["modules"][0]["requires_contracts"].append("NonExistentContractXYZ")

        verifier = ModuleRegistryVerifier()
        verifier.data = bad_data
        verifier.modules = {m["module_id"]: m for m in bad_data["modules"]}

        with self.assertRaises(ValueError) as ctx:
            verifier.check_contract_coverage()
        self.assertIn("NonExistentContractXYZ", str(ctx.exception))

if __name__ == "__main__":
    unittest.main()
