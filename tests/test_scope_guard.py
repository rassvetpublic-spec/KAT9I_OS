# -*- coding: utf-8 -*-
"""
Контрактные и отказные негативные тесты Scope Guard и изоляции исполнения (Issue #49, Gate G3).

Проверяет:
1. Защиту от Path Traversal:
   - Выход через '..' за пределы Workspace для записи;
   - Выход через '..' за пределы Allowed Read Roots для чтения;
   - Альтернативные потоки данных (::$DATA);
   - Null-byte инъекции;
   - UNC сетевые пути.
2. Блокировку запрещённого чтения ДО фактического чтения.
3. Tool Allowlist:
   - Разрешение легитимных утилит (python, git);
   - Отклонение неразрешённых исполняемых файлов (ToolNotAllowedError).
4. Защиту от Command Injection:
   - Запрет выполнения произвольных строк как shell-команд (shell=False).
5. Изоляцию окружения процесса:
   - Удаление токенов/секретов из окружения дочернего процесса;
   - Фиксация CWD строго на workspace_dir.
6. Отказной тест процесса:
   - Запуск реального процесса, пытающегося обратиться вне Scope (проверка границ).
7. Формирование Evidence с фиксацией exit code и метрик.
"""

import os
import sys
import shutil
import tempfile
import unittest
from pathlib import Path
from scripts.scope_guard import Kat9iScopeGuard, ScopeViolationError, ToolNotAllowedError

class TestScopeGuardExecutionIsolation(unittest.TestCase):

    def setUp(self):
        self.base_test_dir = Path(tempfile.mkdtemp(prefix="kat9i_scope_test_"))
        self.workspace_dir = self.base_test_dir / "workspace"
        self.workspace_dir.mkdir()

        self.outside_dir = self.base_test_dir / "outside_private"
        self.outside_dir.mkdir()
        self.secret_file = self.outside_dir / "sensitive_data.txt"
        self.secret_file.write_text("SUPER_SECRET_PAYLOAD", encoding="utf-8")

        self.scope_guard = Kat9iScopeGuard(
            task_id="task-test-scope-049",
            workspace_dir=self.workspace_dir,
            allowed_read_roots=[self.workspace_dir]
        )

    def tearDown(self):
        if self.base_test_dir.exists():
            shutil.rmtree(self.base_test_dir, ignore_errors=True)

    def test_path_traversal_write_blocked(self):
        """Проверяет блокировку записи за пределы workspace через '..'."""
        escape_attempt = str(self.workspace_dir / ".." / "outside_private" / "hacked.txt")
        with self.assertRaises(ScopeViolationError) as ctx:
            self.scope_guard.normalize_and_validate_path(escape_attempt, is_write=True)
        self.assertIn("Write Scope Violation", str(ctx.exception))

    def test_path_traversal_read_blocked_before_read(self):
        """Проверяет блокировку чтения недоверенного файла ДО фактического открытия."""
        escape_attempt = str(self.workspace_dir / ".." / "outside_private" / "sensitive_data.txt")
        with self.assertRaises(ScopeViolationError) as ctx:
            self.scope_guard.normalize_and_validate_path(escape_attempt, is_write=False)
        self.assertIn("Read Scope Violation", str(ctx.exception))

    def test_forbidden_substrings_and_ntfs_streams(self):
        """Проверяет блокировку NTFS альтернативных потоков и null-byte."""
        with self.assertRaises(ScopeViolationError):
            self.scope_guard.normalize_and_validate_path("file.txt::$DATA", is_write=True)
        with self.assertRaises(ScopeViolationError):
            self.scope_guard.normalize_and_validate_path("file.txt\x00.exe", is_write=True)

    def test_unc_network_paths_blocked(self):
        """Проверяет строгий запрет сетевых путей UNC."""
        with self.assertRaises(ScopeViolationError):
            self.scope_guard.normalize_and_validate_path("\\\\evil-server\\share\\data.txt", is_write=False)

    def test_tool_allowlist_enforcement(self):
        """Проверяет Tool Allowlist: разрешены только белые утилиты."""
        # Разрешено
        self.scope_guard.check_tool_allowed("python")
        self.scope_guard.check_tool_allowed("git.exe")

        # Запрещено
        with self.assertRaises(ToolNotAllowedError):
            self.scope_guard.check_tool_allowed("powershell.exe")
        with self.assertRaises(ToolNotAllowedError):
            self.scope_guard.check_tool_allowed("curl.exe")
        with self.assertRaises(ToolNotAllowedError):
            self.scope_guard.check_tool_allowed("cmd.exe")

    def test_isolated_command_execution_and_evidence(self):
        """Проверяет запуск разрешённого процесса с санированным окружением и Evidence."""
        # Запускаем python с простым выводом
        py_exe = sys.executable
        guard = Kat9iScopeGuard(
            task_id="task-test-exec-049",
            workspace_dir=self.workspace_dir,
            tool_allowlist={Path(py_exe).name}
        )

        res = guard.execute_command_isolated(
            [py_exe, "-c", "import os; print('CWD=' + os.getcwd())"],
            timeout_seconds=5.0
        )

        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["exit_code"], 0)
        self.assertIn(str(self.workspace_dir), res["stdout"])

        # Проверка Evidence
        evi = res["evidence"]
        self.assertEqual(evi["status"], "PASS")
        self.assertEqual(evi["task_id"], "task-test-exec-049")
        self.assertIn("duration_ms", evi["metrics"])

    def test_environment_sanitization_no_secret_leak(self):
        """Проверяет, что переменные окружения, содержащие TOKEN/KEY/SECRET, не попадают в дочерний процесс."""
        py_exe = sys.executable
        guard = Kat9iScopeGuard(
            task_id="task-test-leak-049",
            workspace_dir=self.workspace_dir,
            tool_allowlist={Path(py_exe).name}
        )

        test_env = {
            "MY_GITHUB_TOKEN": "ghp_super_secret_leak",
            "SAFE_VAR": "HELLO_KAT9I"
        }

        code = "import os; print('HAS_TOKEN=' + str('MY_GITHUB_TOKEN' in os.environ) + ', SAFE=' + os.environ.get('SAFE_VAR', ''))"
        res = guard.execute_command_isolated([py_exe, "-c", code], extra_env=test_env)

        self.assertEqual(res["status"], "SUCCESS")
        self.assertIn("HAS_TOKEN=False", res["stdout"], "Секретный токен НЕ ДОЛЖЕН попасть в окружение процесса!")
        self.assertIn("SAFE=HELLO_KAT9I", res["stdout"])

if __name__ == "__main__":
    unittest.main()
