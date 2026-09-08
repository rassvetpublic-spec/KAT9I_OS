# -*- coding: utf-8 -*-
"""
Тесты контроля синхронизации единого источника истины (SSoT) и целостности документации.
Проверяет требования Issues #35, #37, #38.
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

    def test_index_html_is_clean_and_up_to_date(self):
        """Проверяет, что запуск генератора не меняет уже закоммиченный index.html."""
        gen_script = REPO_ROOT / "scripts" / "generate_html_docs.py"
        res = subprocess.run([sys.executable, str(gen_script)], capture_output=True, cwd=str(REPO_ROOT))
        self.assertEqual(res.returncode, 0, f"Генератор завершился с ошибкой")

        diff_res = subprocess.run(["git", "diff", "--exit-code", "index.html"], capture_output=True, cwd=str(REPO_ROOT))
        self.assertEqual(
            diff_res.returncode, 0,
            "Ошибка SSoT: производный файл index.html устарел относительно Markdown-документации! "
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

if __name__ == "__main__":
    unittest.main()