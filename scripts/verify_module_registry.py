# -*- coding: utf-8 -*-
"""
Утилита проверки целостности реестра модулей и графа зависимостей KAT9I_OS (Issue #47, Gate G2).

Проверяет:
1. Валидность modules_registry.json согласно schemas/v1/ModuleRegistry.json.
2. Отсутствие несуществующих зависимостей (UNKNOWN_DEPENDENCY).
3. Отсутствие циклических зависимостей (CIRCULAR_DEPENDENCY_DETECTED).
4. Связность контрактов: все requires_contracts должны обеспечиваться модулями системы.
5. Инвариант ADR-032: уникальность канонической ответственности модулей.
6. Вычисляет и печатает топологический порядок инициализации модулей.
"""

import sys
import json
from pathlib import Path
import jsonschema

REPO_ROOT = Path(__file__).resolve().parent.parent
REGISTRY_FILE = REPO_ROOT / "modules_registry.json"
SCHEMA_FILE = REPO_ROOT / "schemas" / "v1" / "ModuleRegistry.json"

class ModuleRegistryVerifier:

    def __init__(self, registry_path=REGISTRY_FILE, schema_path=SCHEMA_FILE):
        self.registry_path = Path(registry_path)
        self.schema_path = Path(schema_path)
        self.data = None
        self.modules = {}

    def load_and_validate_schema(self):
        if not self.registry_path.exists():
            raise FileNotFoundError(f"Файл реестра не найден: {self.registry_path}")
        if not self.schema_path.exists():
            raise FileNotFoundError(f"Файл схемы не найден: {self.schema_path}")

        with open(self.schema_path, "r", encoding="utf-8") as f:
            schema = json.load(f)
        with open(self.registry_path, "r", encoding="utf-8") as f:
            self.data = json.load(f)

        jsonschema.validate(instance=self.data, schema=schema)
        self.modules = {m["module_id"]: m for m in self.data["modules"]}
        return True

    def check_references_and_documentation(self):
        """Проверяет существование файлов документации."""
        missing_docs = []
        for m_id, m in self.modules.items():
            doc_ref = m.get("documentation_ref")
            if doc_ref:
                doc_path = REPO_ROOT / doc_ref
                if not doc_path.exists():
                    missing_docs.append(f"Модуль {m_id}: документация не найдена по пути {doc_ref}")
        if missing_docs:
            raise ValueError("Обнаружены отсутствующие файлы документации:\n" + "\n".join(missing_docs))
        return True

    def check_dependency_integrity(self):
        """Проверяет отсутствие неизвестных зависимостей."""
        unknown_deps = []
        for m_id, m in self.modules.items():
            for dep in m.get("dependencies", []):
                if dep not in self.modules:
                    unknown_deps.append(f"Модуль {m_id} зависит от неизвестного модуля '{dep}'")
        if unknown_deps:
            raise ValueError("Нарушение целостности зависимостей:\n" + "\n".join(unknown_deps))
        return True

    def check_contract_coverage(self):
        """Проверяет, что все требуемые контракты кем-либо предоставляются."""
        all_provided = set()
        for m in self.modules.values():
            all_provided.update(m.get("provides_contracts", []))

        uncovered = []
        for m_id, m in self.modules.items():
            for req in m.get("requires_contracts", []):
                if req not in all_provided:
                    uncovered.append(f"Модуль {m_id} требует контракт '{req}', который не предоставляется ни одним модулем")
        if uncovered:
            raise ValueError("Непокрытые системные контракты:\n" + "\n".join(uncovered))
        return True

    def check_unique_responsibility(self):
        """Проверяет уникальность канонической ответственности (инвариант ADR-032)."""
        seen_resp = {}
        duplicates = []
        for m_id, m in self.modules.items():
            resp = m.get("canonical_responsibility", "").strip().lower()
            if resp in seen_resp:
                duplicates.append(f"Конфликт ответственности: модули '{m_id}' и '{seen_resp[resp]}' имеют идентичную ответственность: '{resp}'")
            else:
                seen_resp[resp] = m_id
        if duplicates:
            raise ValueError("Нарушение инварианта ADR-032 (один канонический владелец ответственности):\n" + "\n".join(duplicates))
        return True

    def detect_cycles_and_topological_sort(self):
        """
        Проверяет граф на ацикличность (DAG) и возвращает топологический порядок инициализации.
        Модули без зависимостей идут первыми.
        """
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {m_id: WHITE for m_id in self.modules}
        topo_order = []

        def dfs(node, path):
            color[node] = GRAY
            for dep in self.modules[node].get("dependencies", []):
                if color[dep] == GRAY:
                    cycle = path + [node, dep]
                    cycle_str = " -> ".join(cycle)
                    raise ValueError(f"CIRCULAR_DEPENDENCY_DETECTED: обнаружен цикл в графе зависимостей: {cycle_str}")
                if color[dep] == WHITE:
                    dfs(dep, path + [node])
            color[node] = BLACK
            topo_order.append(node)

        for m_id in self.modules:
            if color[m_id] == WHITE:
                dfs(m_id, [])

        return topo_order

    def run_full_verification(self):
        print(f"Запуск верификации реестра модулей: {self.registry_path}")
        self.load_and_validate_schema()
        print("  [OK] Валидация JSON Schema Draft 2020-12 пройдена")

        self.check_references_and_documentation()
        print("  [OK] Все ссылки на каноническую документацию валидны")

        self.check_dependency_integrity()
        print("  [OK] Отсутствуют битые ссылки на зависимости")

        self.check_contract_coverage()
        print("  [OK] Все требуемые контракты покрыты поставщиками")

        self.check_unique_responsibility()
        print("  [OK] Инвариант ADR-032 соблюдён: нет дублирования канонической ответственности")

        topo = self.detect_cycles_and_topological_sort()
        print(f"  [OK] Граф зависимостей ацикличен (DAG). Модулей в реестре: {len(topo)}")
        print("\nКанонический порядок инициализации подсистем первой вертикали v0.1:")
        for idx, m_id in enumerate(topo, start=1):
            m = self.modules[m_id]
            print(f"  {idx}. [{m['tier']}] {m_id} (v{m['version']}) -> {m['name']}")
        return topo

if __name__ == "__main__":
    try:
        verifier = ModuleRegistryVerifier()
        verifier.run_full_verification()
    except Exception as e:
        print(f"ОШИБКА ВЕРИФИКАЦИИ РЕЕСТРА МОДУЛЕЙ: {e}", file=sys.stderr)
        sys.exit(1)
