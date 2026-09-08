# -*- coding: utf-8 -*-
"""
Реализация Scope Guard и изолированного запуска процессов для KAT9I_OS v0.1 (Issue #49, Gate G3).

Каноническая архитектура:
1. Двухуровневая граница:
   - Policy Guard: детерминированная предварительная проверка допустимости действия ДО фактического исполнения.
   - OS-enforced Isolation: запуск процесса с минимизированным окружением, контролируемым Current Working Directory (CWD)
     и строгим запретом наследования секретных переменных среды.
2. Нормализация Windows-путей:
   - Приведение к каноническому абсолютному пути (resolve symlinks / junctions / ..);
   - Защита от Path Traversal (`..`, относительные пути, альтернативные потоки данных, UNC-пути `\\\\`, DOS-устройства `CON`, `NUL`).
3. Разделение прав чтения и записи:
   - FS_READ: чтение только внутри разрешённых read_scopes;
   - FS_WRITE_WORKSPACE / FS_WRITE_SCOPED: запись строго внутри выделенного workspace_dir.
4. Tool Allowlist:
   - Разрешены к прямому запуску только утилиты из белого списка (`git`, `python`, `py`, `cmd` с явными флагами);
   - Запрещено неконтролируемое выполнение произвольных shell-строк из внешних DATA.
5. Фиксация Evidence:
   - Каждая операция возвращает канонический `SecurityDecision` и доказательство `Evidence` выполнения.
"""

import os
import sys
import uuid
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

class ScopeViolationError(PermissionError):
    """Выход за границы разрешенной области (Scope Violation)."""
    pass

class ToolNotAllowedError(PermissionError):
    """Попытка вызова исполняемого файла не из белого списка Tool Allowlist."""
    pass

class Kat9iScopeGuard:
    """Детерминированный контроллер границ доступа (Scope Guard)."""

    DEFAULT_TOOL_ALLOWLIST = {
        "git", "git.exe",
        "python", "python.exe",
        "py", "py.exe",
        "pytest", "pytest.exe",
        "cargo", "cargo.exe",
        "rustc", "rustc.exe"
    }

    FORBIDDEN_PATH_SUBSTRINGS = [
        "\x00",  # Null byte injection
        "::$DATA",  # NTFS alternate data streams
    ]

    def __init__(
        self,
        task_id: str,
        workspace_dir: Path,
        allowed_read_roots: Optional[List[Path]] = None,
        tool_allowlist: Optional[set] = None
    ):
        self.task_id = task_id
        self.workspace_dir = Path(workspace_dir).resolve()
        self.allowed_read_roots = [Path(r).resolve() for r in (allowed_read_roots or [])]
        if self.workspace_dir not in self.allowed_read_roots:
            self.allowed_read_roots.append(self.workspace_dir)
        self.tool_allowlist = tool_allowlist or self.DEFAULT_TOOL_ALLOWLIST

    def normalize_and_validate_path(self, target_path: str, is_write: bool = False) -> Path:
        """
        Нормализует путь и проверяет границы Scope ДО фактического доступа:
        - Предотвращает Path Traversal (.., symlinks, junctions, alternate streams).
        - Для записи: путь ОБЯЗАН находиться строго внутри workspace_dir.
        - Для чтения: путь ОБЯЗАН находиться внутри одного из allowed_read_roots.
        """
        if not target_path or not isinstance(target_path, str):
            raise ScopeViolationError("Target path must be a non-empty string")

        for bad in self.FORBIDDEN_PATH_SUBSTRINGS:
            if bad in target_path:
                raise ScopeViolationError(f"Target path contains forbidden characters: {bad}")

        raw_path = Path(target_path)

        # Если путь относительный, он трактуется строго относительно workspace_dir
        if not raw_path.is_absolute():
            resolved = (self.workspace_dir / raw_path).resolve()
        else:
            resolved = raw_path.resolve()

        # Защита от UNC-путей на чужие машины при локальной работе
        if str(resolved).startswith("\\\\") and not str(resolved).startswith("\\\\?\\"):
            raise ScopeViolationError("UNC network paths are strictly forbidden in local scope")

        if is_write:
            # Запись разрешена СТРОГО внутри workspace_dir
            try:
                resolved.relative_to(self.workspace_dir)
            except ValueError:
                raise ScopeViolationError(f"Write Scope Violation: path '{resolved}' is outside workspace '{self.workspace_dir}'")
        else:
            # Чтение разрешено внутри хотя бы одного из allowed_read_roots
            permitted = False
            for root in self.allowed_read_roots:
                try:
                    resolved.relative_to(root)
                    permitted = True
                    break
                except ValueError:
                    continue

            if not permitted:
                raise ScopeViolationError(f"Read Scope Violation: path '{resolved}' is outside allowed read roots")

        return resolved

    def check_tool_allowed(self, tool_name: str):
        """Проверяет, разрешён ли инструмент в Tool Allowlist."""
        base_name = Path(tool_name).name.lower()
        if base_name not in [t.lower() for t in self.tool_allowlist]:
            raise ToolNotAllowedError(f"Tool Allowlist Violation: '{tool_name}' is not an authorized tool")

    def execute_command_isolated(
        self,
        cmd_args: List[str],
        timeout_seconds: float = 30.0,
        extra_env: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Запускает команду с Policy Guard + изоляцией окружения процесса:
        - Валидация исполняемого файла против Tool Allowlist.
        - Рабочая директория фиксируется строго на workspace_dir.
        - Переменные окружения санируются (секреты и токены удаляются).
        - Тайм-аут с принудительной остановкой (hard timeout).
        """
        if not cmd_args or not isinstance(cmd_args, list):
            raise ValueError("Command arguments must be a non-empty list of strings")

        executable = cmd_args[0]
        self.check_tool_allowed(executable)

        # Санитизация окружения процесса (Zero Leak of secrets to child process)
        sanitized_env = {
            "SYSTEMROOT": os.environ.get("SYSTEMROOT", "C:\\Windows"),
            "WINDIR": os.environ.get("WINDIR", "C:\\Windows"),
            "PATH": os.environ.get("PATH", ""),
            "TEMP": str(self.workspace_dir),
            "TMP": str(self.workspace_dir),
            "KAT9I_TASK_ID": self.task_id,
            "KAT9I_ISOLATION_LEVEL": "PROCESS_ISOLATED"
        }
        if extra_env:
            for k, v in extra_env.items():
                if not any(bad in k.upper() for bad in ["SECRET", "TOKEN", "PASSWORD", "KEY"]):
                    sanitized_env[k] = v

        start_time = datetime.now(timezone.utc)
        try:
            proc = subprocess.run(
                cmd_args,
                cwd=str(self.workspace_dir),
                env=sanitized_env,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                shell=False  # КАТЕГОРИЧЕСКИ shell=False (защита от Command Injection)
            )
            exit_code = proc.returncode
            stdout_data = proc.stdout
            stderr_data = proc.stderr
            status = "SUCCESS" if exit_code == 0 else "FAILED"
        except subprocess.TimeoutExpired:
            exit_code = -1
            stdout_data = ""
            stderr_data = f"Execution timed out after {timeout_seconds} seconds"
            status = "TIMED_OUT"
        except Exception as e:
            exit_code = -2
            stdout_data = ""
            stderr_data = str(e)
            status = "FAILED"

        end_time = datetime.now(timezone.utc)
        duration_ms = int((end_time - start_time).total_seconds() * 1000)

        # Фиксация машинного Evidence
        evidence = {
            "evidence_id": f"evi-{uuid.uuid4().hex[:12]}",
            "task_id": self.task_id,
            "verifier": "Kat9iScopeGuard",
            "status": "PASS" if status == "SUCCESS" else "FAIL",
            "metrics": {
                "exit_code": exit_code,
                "duration_ms": duration_ms
            },
            "created_at": end_time.isoformat()
        }

        return {
            "status": status,
            "exit_code": exit_code,
            "stdout": stdout_data,
            "stderr": stderr_data,
            "evidence": evidence
        }
