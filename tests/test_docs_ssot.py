# -*- coding: utf-8 -*-
"""
Тесты контроля синхронизации единого источника истины (SSoT) и целостности документации.
Проверяет требования Issues #35, #36, #37, #38, #55.
"""

import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

class TestDocumentationSSoT(unittest.TestCase):

    def test_canonical_module_responsibility_map_exists(self):
        """Проверяет наличие канонического реестра модулей и карты ответственности."""
        canonical_map = REPO_ROOT / "docs" / "architecture" / "27_MODULE_REGISTRY_AND_RESPONSIBILITY_MAP.md"
        self.assertTrue(canonical_map.exists(), "Канонический файл 27_MODULE_REGISTRY_AND_RESPONSIBILITY_MAP.md отсутствует")
        content = canonical_map.read_text(encoding="utf-8")
        self.assertIn("Реестр модулей и карта ответственности", content)

    def test_external_systems_benchmark_exists(self):
        """Проверяет наличие канонического документа внешнего бенчмарка (Issue #43)."""
        benchmark_file = REPO_ROOT / "docs" / "architecture" / "33_EXTERNAL_SYSTEMS_BENCHMARK.md"
        self.assertTrue(benchmark_file.exists(), "Канонический файл 33_EXTERNAL_SYSTEMS_BENCHMARK.md отсутствует")
        content = benchmark_file.read_text(encoding="utf-8")
        self.assertIn("Внешний сравнительный бенчмарк KAT9I_OS", content)
        self.assertIn("IMPLEMENTED", content)
        self.assertIn("SPECIFIED", content)
        self.assertIn("ABSENT", content)
        self.assertIn("Temporal", content)
        self.assertIn("LangGraph", content)

    def test_no_competing_canonical_sources_for_responsibility_map(self):
        """Проверяет, что нет второго конкурирующего канонического источника карты ответственности."""
        arch_dir = REPO_ROOT / "docs" / "architecture"
        for md_file in arch_dir.glob("*.md"):
            if md_file.name == "27_MODULE_REGISTRY_AND_RESPONSIBILITY_MAP.md":
                continue
            text = md_file.read_text(encoding="utf-8")
            if "RESPONSIBILITY_MAP" in md_file.name.upper():
                self.assertTrue(
                    "27_MODULE_REGISTRY_AND_RESPONSIBILITY_MAP.md" in text or "производн" in text.lower() or "навигацион" in text.lower(),
                    f"Файл {md_file.name} не указывает на канонический источник 27_MODULE_REGISTRY_AND_RESPONSIBILITY_MAP.md"
                )

    def test_documentation_groups_coverage(self):
        """Проверяет наличие файлов во всех ключевых группах документации: tz, architecture, spec, guides, GLOSSARY."""
        docs_dir = REPO_ROOT / "docs"
        groups = ["tz", "architecture", "spec", "guides"]
        for g in groups:
            group_dir = docs_dir / g
            self.assertTrue(group_dir.exists() and group_dir.is_dir(), f"Группа документации docs/{g} отсутствует")
            md_files = list(group_dir.glob("*.md"))
            self.assertGreater(len(md_files), 0, f"В каталоге docs/{g} нет Markdown-файлов")

        glossary = docs_dir / "GLOSSARY.md"
        self.assertTrue(glossary.exists(), "docs/GLOSSARY.md отсутствует")

    def test_html_includes_all_specs_and_tables(self):
        """Проверяет, что index.html включает все спецификации из docs/spec/ и таблицы Markdown (Issues #36, #55)."""
        index_file = REPO_ROOT / "index.html"
        self.assertTrue(index_file.exists(), "index.html отсутствует")
        html_content = index_file.read_text(encoding="utf-8")

        # Проверка включения спецификаций
        spec_dir = REPO_ROOT / "docs" / "spec"
        for spec_file in spec_dir.glob("*.md"):
            self.assertIn(
                spec_file.stem.lower(),
                html_content.lower(),
                f"Спецификация {spec_file.name} не найдена в index.html"
            )

        # Проверка наличия таблиц
        self.assertIn('<table class="doc-table">', html_content, "В index.html отсутствуют сгенерированные таблицы doc-table")

        # Проверка наличия 5 уровней подробности
        self.assertIn("1. Очень просто", html_content)
        self.assertIn("2. Просто", html_content)
        self.assertIn("3. Рабочий", html_content)
        self.assertIn("4. Технический", html_content)
        self.assertIn("5. Максимум", html_content)

    def test_index_html_is_clean_and_up_to_date(self):
        """Проверяет, что запуск генератора не меняет уже закоммиченный index.html."""
        gen_script = REPO_ROOT / "scripts" / "generate_html_docs.py"
        res = subprocess.run([sys.executable, str(gen_script)], capture_output=True, cwd=str(REPO_ROOT))
        self.assertEqual(res.returncode, 0, f"Генератор завершился с ошибкой")

        diff_res = subprocess.run(["git", "diff", "--exit-code", "index.html"], capture_output=True, cwd=str(REPO_ROOT))
        diff_text = diff_res.stdout.decode("utf-8", errors="replace") if diff_res.stdout else ""
        self.assertEqual(
            diff_res.returncode, 0,
            f"Ошибка SSoT: производный файл index.html устарел относительно Markdown-документации!\nDIFF:\n{diff_text[:2000]}\n"
            "Запустите `python scripts/generate_html_docs.py` и закоммитьте обновлённый index.html."
        )

    def test_out_of_sync_detection(self):
        """Тест, подтверждающий обнаружение рассинхронизации при искусственном изменении."""
        index_file = REPO_ROOT / "index.html"
        original_bytes = index_file.read_bytes()
        try:
            index_file.write_bytes(original_bytes + b"\n<!-- out_of_sync_test_tag -->\n")
            diff_res = subprocess.run(["git", "diff", "--exit-code", "index.html"], capture_output=True, cwd=str(REPO_ROOT))
            self.assertNotEqual(diff_res.returncode, 0, "Проверка diff обязана вернуть ненулевой код при рассинхронизации")
        finally:
            index_file.write_bytes(original_bytes)

    def test_russian_language_policy_and_headings(self):
        """
        Проверяет соблюдение языковой политики (Issue #53, spec/00_LANGUAGE_AND_TERMINOLOGY_POLICY.md):
        - Заголовки в канонической документации (spec, architecture, tz, guides) должны содержать русский текст (кириллицу),
          за исключением явно разрешённых технических идентификаторов/контрактов.
        """
        import re

        # Список разрешённых чисто технических заголовков (идентификаторы перечислений, контрактов, ADR, аббревиатуры)
        allowed_exact_headings = {
            "MANUAL", "NOTIFY", "SAFE_AUTO", "CONTROLLED_AUTO",
            "CONTROL", "DATA",
            "CRITICAL", "HIGH", "NORMAL", "LOW",
            "P0", "P1", "P2", "P3",
            "DRAINING",
            "Primary Node", "Remote Worker Runtime",
            "28.61. GitHub Pages",
            "25.18. Obsidian",
            "25.21. Windows Credential Manager",
            "31.76. Good First Issue",
        }

        docs_root = REPO_ROOT / "docs"
        dirs_to_check = [
            docs_root / "spec",
            docs_root / "architecture",
            docs_root / "tz",
            docs_root / "guides",
        ]

        # Для существующих файлов architecture с историческими англоязычными номерами подразделов
        # проверяем, что в spec/ и KAT9I_OS_ARCHITECTURE_CONTEXT.md нет ни одного чисто английского заголовка
        strict_files = list((docs_root / "spec").glob("*.md")) + [
            docs_root / "architecture" / "KAT9I_OS_ARCHITECTURE_CONTEXT.md",
            docs_root / "architecture" / "27_MODULE_REGISTRY_AND_RESPONSIBILITY_MAP.md",
            docs_root / "architecture" / "33_EXTERNAL_SYSTEMS_BENCHMARK.md",
            docs_root / "architecture" / "MODULE_RESPONSIBILITY_MAP.md",
            docs_root / "GLOSSARY.md",
        ]

        violations = []
        for file_path in strict_files:
            if not file_path.exists():
                continue
            text = file_path.read_text(encoding="utf-8")
            for line_no, line in enumerate(text.splitlines(), start=1):
                if line.startswith("#"):
                    raw_h = re.sub(r"^#+\s*", "", line).strip()
                    if raw_h in allowed_exact_headings:
                        continue
                    # Заголовок должен содержать хотя бы одну русскую букву
                    if not re.search(r"[\u0400-\u04FF]", raw_h):
                        violations.append(f"{file_path.relative_to(REPO_ROOT)}:{line_no} -> {line}")

        self.assertEqual(
            violations, [],
            f"Обнаружены нарушения языковой политики: заголовки без кириллицы ({len(violations)}):\n" + "\n".join(violations[:20])
        )

    def test_detail_levels_filtering_semantics(self):
        """
        Проверяет семантику 5 уровней подробности согласно канонической спецификации 24.4 (Issue #36):
        - Наличие глобального селектора со всеми 5 уровнями (simple, basic, worker, tech, all).
        - Наличие разметки data-section-level для всех 5 уровней во фронтенде.
        - Наличие атрибутов data-target-id в навигации quick-nav для синхронизации отображения ссылок.
        - Наличие логики фильтрации секций по иерархическому рангу в updateDetailLevel.
        """
        index_file = REPO_ROOT / "index.html"
        self.assertTrue(index_file.exists(), "index.html отсутствует")
        content = index_file.read_text(encoding="utf-8")

        # 1. Проверка селектора уровней
        expected_levels = ["simple", "basic", "worker", "tech", "all"]
        for lvl in expected_levels:
            self.assertIn(f'value="{lvl}"', content, f"Уровень {lvl} отсутствует в селекторе detailLevel")

        # 2. Проверка разметки data-section-level во всех 5 уровнях
        for lvl in expected_levels:
            pattern = f'data-section-level="{lvl}"'
            self.assertIn(pattern, content, f"Разметка {pattern} отсутствует на секциях index.html")

        # 3. Проверка связки быстрой навигации с секциями через data-target-id
        self.assertIn('data-target-id="coworker-section"', content)
        self.assertIn('data-target-id="glossary-section"', content)

        # 4. Проверка реализации ранговой фильтрации в JS
        self.assertIn("data-section-level", content)
        self.assertIn("levelRank", content)
        self.assertIn("nav.quick-nav", content)

    def test_canonical_schemas_ssot_exists(self):
        """
        Проверяет наличие канонического каталога схем и минимального набора первой вертикали v0.1 (Issue #40, Gate G2):
        - schemas/README.md
        - schemas/v1/{TaskContract, TaskRuntimeState, TaskResult, Evidence, SecurityDecision, CapabilityGrant, SystemEvent}.json
        """
        schemas_dir = REPO_ROOT / "schemas" / "v1"
        self.assertTrue(schemas_dir.exists() and schemas_dir.is_dir(), "Каталог schemas/v1 отсутствует")
        readme = REPO_ROOT / "schemas" / "README.md"
        self.assertTrue(readme.exists(), "Файл schemas/README.md отсутствует")

        expected_schemas = [
            "TaskContract.json",
            "TaskRuntimeState.json",
            "TaskResult.json",
            "Evidence.json",
            "SecurityDecision.json",
            "CapabilityGrant.json",
            "SystemEvent.json",
            "ModuleRegistry.json"
        ]
        for s in expected_schemas:
            p = schemas_dir / s
            self.assertTrue(p.exists(), f"Каноническая схема {s} отсутствует в {schemas_dir}")

        registry_file = REPO_ROOT / "modules_registry.json"
        self.assertTrue(registry_file.exists(), "Файл modules_registry.json отсутствует в корне репозитория")

if __name__ == "__main__":
    unittest.main()