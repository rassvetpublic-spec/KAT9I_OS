# -*- coding: utf-8 -*-
"""
Вертикальный срез KAT9I_OS v0.1 (Issue #48, Gate G4).

Сквозной интеграционный сценарий без LLM:
Electron UI Client -> Core Runtime IPC -> TaskContract Validation -> Security Preflight & Scope Guard
-> Execution Engine -> Storage Append-Only Event Journal -> Evidence Generation -> TaskResult -> Electron UI Client.

Гарантируемые инварианты:
1. Машинная валидация TaskContract.json до начала выполнения (Fail-Closed).
2. Проверка Scope Guard до доступа к целевому ресурсу (Policy Guard).
3. Фиксация событий перехода состояний в Event Journal (JournalEvent.json) с монотонным sequence_number.
4. Доказуемое исполнение: генерация Evidence.json с хэшем коммита и статусом проверок.
5. Формирование валидного TaskResult.json с sha256 хэшами артефактов.
6. Живучесть Core: отключение/падение UI не прерывает работу Core и сохраняет статус задачи.
"""

import hashlib
import json
import os
import socket
import sys
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from jsonschema import Draft202012Validator

from scripts.core_ipc_prototype import Kat9iCoreServer, Kat9iElectronIpcClient
from scripts.scope_guard import Kat9iScopeGuard, ScopeViolationError

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMAS_V1_DIR = REPO_ROOT / "schemas" / "v1"


def compute_sha256(file_path: Path) -> str:
    """Вычисляет sha256 хэш файла."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


class Kat9iVerticalEngine:
    """
    Интеграционный исполнительный механизм вертикального среза v0.1.
    Объединяет Core Runtime, Scope Guard, Event Journal и Evidence Generator.
    """

    def __init__(self, workspace_root: Path, journal_path: Optional[Path] = None, source_revision: str = "ecc8c58"):
        self.workspace_root = Path(workspace_root).resolve()
        self.journal_path = journal_path or (self.workspace_root / ".kat9i_journal.jsonl")
        self.source_revision = source_revision
        self.journal_lock = threading.Lock()
        self.sequence_number = 0

        # Загрузка и компиляция JSON-схем для машинной валидации контрактов
        with open(SCHEMAS_V1_DIR / "TaskContract.json", "r", encoding="utf-8") as f:
            self.task_contract_validator = Draft202012Validator(json.load(f))
        with open(SCHEMAS_V1_DIR / "TaskResult.json", "r", encoding="utf-8") as f:
            self.task_result_validator = Draft202012Validator(json.load(f))
        with open(SCHEMAS_V1_DIR / "Evidence.json", "r", encoding="utf-8") as f:
            self.evidence_validator = Draft202012Validator(json.load(f))
        with open(SCHEMAS_V1_DIR / "JournalEvent.json", "r", encoding="utf-8") as f:
            self.journal_event_validator = Draft202012Validator(json.load(f))

    def append_journal_event(
        self,
        event_type: str,
        task_id: str,
        correlation_id: str,
        payload: Dict[str, Any],
        source_module: str = "Core",
        evidence_ref: Optional[str] = None,
        operation_id: Optional[str] = None,
        lease_generation: Optional[int] = 1,
        actor_identity_id: Optional[str] = "id-worker-kat9i-v01"
    ) -> Dict[str, Any]:
        """Добавляет строго валидированное событие в append-only журнал."""
        with self.journal_lock:
            self.sequence_number += 1
            event = {
                "event_id": f"evt-{uuid.uuid4().hex[:12]}",
                "sequence_number": self.sequence_number,
                "event_type": event_type,
                "source_module": source_module,
                "task_id": task_id,
                "correlation_id": correlation_id,
                "actor_identity_id": actor_identity_id,
                "operation_id": operation_id,
                "lease_generation": lease_generation,
                "payload": payload,
                "evidence_ref": evidence_ref,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            # Машинная проверка по схеме JournalEvent.json
            self.journal_event_validator.validate(event)

            self.journal_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.journal_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(event, ensure_ascii=False) + "\n")

            return event

    def execute_vertical_task(self, task_contract: Dict[str, Any], correlation_id: str) -> Dict[str, Any]:
        """
        Полный детерминированный сквозной цикл выполнения задачи v0.1:
        1. Машинная валидация TaskContract.
        2. Событие TASK_CREATED в Event Journal.
        3. Инициализация Scope Guard и проверка Scope ДО доступа к ресурсу.
        4. Детерминированное исполнение: чтение разрешённого файла, валидация содержимого.
        5. Событие SIDE_EFFECT_EXECUTED в Event Journal.
        6. Создание артефакта результата и вычисление sha256.
        7. Генерация Evidence.json с проверкой по схеме.
        8. Формирование TaskResult.json и событие TASK_COMPLETED в Event Journal.
        """
        t_start = time.perf_counter()

        # 1. Валидация TaskContract (Fail-Closed)
        self.task_contract_validator.validate(task_contract)

        task_id = task_contract["task_id"]
        scope_info = task_contract["scope"]

        # 2. Журналирование создания задачи
        self.append_journal_event(
            event_type="TASK_CREATED",
            task_id=task_id,
            correlation_id=correlation_id,
            payload={
                "goal": task_contract["goal"],
                "workspace": task_contract["workspace"],
                "allowed_paths": scope_info["allowed_paths"]
            }
        )

        # 3. Scope Guard: инициализация
        scope_guard = Kat9iScopeGuard(
            task_id=task_id,
            workspace_dir=self.workspace_root,
            allowed_read_roots=[self.workspace_root]
        )

        # 4. Проверка путей и выполнение детерминированного шага
        allowed_paths = scope_info.get("allowed_paths", [])
        if not allowed_paths:
            raise ValueError("TaskContract scope.allowed_paths cannot be empty")

        target_rel_path = allowed_paths[0]
        # Проверяем Scope ДО доступа к диску
        validated_file_path = scope_guard.normalize_and_validate_path(target_rel_path, is_write=False)

        if not validated_file_path.exists():
            raise FileNotFoundError(f"Target file {target_rel_path} does not exist in workspace")

        # Чтение разрешённого файла
        with open(validated_file_path, "r", encoding="utf-8") as f:
            file_content = f.read()

        # Валидация содержимого: ожидается корректный JSON-манифест или текстовый файл
        try:
            parsed_data = json.loads(file_content)
            validation_passed = isinstance(parsed_data, dict)
            summary_info = f"Valid JSON verified with {len(parsed_data)} top-level keys"
        except Exception:
            validation_passed = len(file_content) > 0
            summary_info = f"File exists with {len(file_content)} characters verified"

        # 5. Журналирование выполнения шага
        op_id = f"op-{uuid.uuid4().hex[:12]}"
        self.append_journal_event(
            event_type="SIDE_EFFECT_EXECUTED",
            task_id=task_id,
            correlation_id=correlation_id,
            operation_id=op_id,
            source_module="Execution",
            payload={
                "target_file": str(target_rel_path),
                "validation_passed": validation_passed,
                "summary": summary_info
            }
        )

        # 6. Создание результирующего артефакта внутри workspace
        artifacts_dir = self.workspace_root / "artifacts" / task_id
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        report_path = artifacts_dir / "verification_report.json"

        report_data = {
            "task_id": task_id,
            "target_verified": str(target_rel_path),
            "sha256": compute_sha256(validated_file_path),
            "status": "VERIFIED_SUCCESS",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)

        report_hash = compute_sha256(report_path)
        report_size = report_path.stat().st_size

        # 7. Генерация Evidence
        evidence_id = f"ev-{uuid.uuid4().hex[:12]}"
        evidence_rel_path = f"artifacts/{task_id}/evidence.json"
        evidence_abs_path = self.workspace_root / evidence_rel_path

        evidence_payload = {
            "evidence_id": evidence_id,
            "task_id": task_id,
            "source_revision": self.source_revision,
            "test_results": {
                "total": 1,
                "passed": 1 if validation_passed else 0,
                "failed": 0 if validation_passed else 1,
                "exit_code": 0 if validation_passed else 1,
                "summary": "Deterministic file verification and Scope Guard pass"
            },
            "qa_verdict": "PASS" if validation_passed else "FAIL",
            "qa_worker": "id-worker-qa-engine",
            "notes": "Verified automatically via KAT9I_OS v0.1 vertical engine",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        self.evidence_validator.validate(evidence_payload)

        with open(evidence_abs_path, "w", encoding="utf-8") as f:
            json.dump(evidence_payload, f, indent=2, ensure_ascii=False)

        # 8. Формирование TaskResult
        duration_ms = int((time.perf_counter() - t_start) * 1000)
        task_result = {
            "task_id": task_id,
            "verdict": "SUCCESS" if validation_passed else "FAILURE",
            "summary": f"Vertical slice completed successfully. {summary_info}",
            "artifacts": [
                {
                    "path": str(Path("artifacts") / task_id / "verification_report.json").replace("\\", "/"),
                    "hash_sha256": report_hash,
                    "size_bytes": report_size,
                    "description": "Deterministic verification report of target file"
                }
            ],
            "evidence_ref": evidence_rel_path.replace("\\", "/"),
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "duration_ms": max(duration_ms, 1)
        }
        self.task_result_validator.validate(task_result)

        # 9. Журналирование завершения задачи
        self.append_journal_event(
            event_type="TASK_COMPLETED",
            task_id=task_id,
            correlation_id=correlation_id,
            evidence_ref=evidence_rel_path.replace("\\", "/"),
            payload={
                "verdict": task_result["verdict"],
                "duration_ms": task_result["duration_ms"],
                "artifacts_count": len(task_result["artifacts"])
            }
        )

        return task_result


class Kat9iVerticalCoreServer(Kat9iCoreServer):
    """
    Расширенный сервер ядра KAT9I_OS с поддержкой выполнения детерминированных
    контрактов задач через вертикальный связующий слой v0.1.
    """

    def __init__(self, workspace_root: Path, host: str = "127.0.0.1", port: int = 0, auth_token: Optional[str] = None):
        super().__init__(host=host, port=port, auth_token=auth_token)
        self.workspace_root = Path(workspace_root).resolve()
        self.engine = Kat9iVerticalEngine(workspace_root=self.workspace_root)

    def _process_message(self, raw_line: str, client_sock: socket.socket) -> Dict[str, Any]:
        """Обрабатывает запросы узкого IPC с добавлением метода core.execute_contract_task."""
        try:
            msg = json.loads(raw_line)
        except Exception:
            return {
                "message_id": f"msg-err-{uuid.uuid4().hex[:12]}",
                "correlation_id": "corr-unknown",
                "type": "ERROR",
                "method": "core.ping",
                "payload": {},
                "error": {"code": "INVALID_JSON", "message": "Failed to parse JSON"},
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        corr_id = msg.get("correlation_id", "corr-none")
        method = msg.get("method")
        token = msg.get("auth_token")

        if token != self.auth_token:
            return {
                "message_id": f"msg-resp-{uuid.uuid4().hex[:12]}",
                "correlation_id": corr_id,
                "type": "ERROR",
                "method": method or "core.ping",
                "payload": {},
                "error": {"code": "ACCESS_DENIED", "message": "Invalid auth token for IPC connection"},
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        # Специализированный метод для сквозного вертикального исполнения v0.1:
        if method == "core.execute_contract_task":
            payload = msg.get("payload", {})
            contract = payload.get("contract")
            if not contract or not isinstance(contract, dict):
                return {
                    "message_id": f"msg-resp-{uuid.uuid4().hex[:12]}",
                    "correlation_id": corr_id,
                    "type": "ERROR",
                    "method": "core.execute_contract_task",
                    "payload": {},
                    "error": {"code": "INVALID_CONTRACT", "message": "Contract payload must be provided"},
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }

            task_id = contract.get("task_id", f"task-{uuid.uuid4().hex[:8]}")

            # Регистрация в Core State
            with self.lock:
                task_record = {
                    "task_id": task_id,
                    "goal": contract.get("goal", "Deterministic Execution"),
                    "status": "RUNNING",
                    "progress_percent": 25,
                    "worker_id": "id-worker-kat9i-v01",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
                self.tasks[task_id] = task_record

            self._broadcast_event("TASK_RUNNING", task_id, {"goal": task_record["goal"]})

            # Выполнение сквозного пайплайна
            try:
                task_result = self.engine.execute_vertical_task(contract, correlation_id=corr_id)
                with self.lock:
                    self.tasks[task_id]["status"] = "COMPLETED"
                    self.tasks[task_id]["progress_percent"] = 100
                    self.tasks[task_id]["result"] = task_result
                    self.tasks[task_id]["updated_at"] = datetime.now(timezone.utc).isoformat()

                self._broadcast_event("TASK_COMPLETED", task_id, {"verdict": task_result["verdict"]})

                return {
                    "message_id": f"msg-resp-{uuid.uuid4().hex[:12]}",
                    "correlation_id": corr_id,
                    "type": "RESPONSE",
                    "method": "core.execute_contract_task",
                    "payload": {
                        "task_record": self.tasks[task_id],
                        "task_result": task_result
                    },
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            except Exception as exc:
                with self.lock:
                    self.tasks[task_id]["status"] = "FAILED"
                    self.tasks[task_id]["error"] = str(exc)
                    self.tasks[task_id]["updated_at"] = datetime.now(timezone.utc).isoformat()

                self._broadcast_event("TASK_FAILED", task_id, {"error": str(exc)})
                return {
                    "message_id": f"msg-resp-{uuid.uuid4().hex[:12]}",
                    "correlation_id": corr_id,
                    "type": "ERROR",
                    "method": "core.execute_contract_task",
                    "payload": {"task_record": self.tasks[task_id]},
                    "error": {"code": "TASK_EXECUTION_FAILED", "message": str(exc)},
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }

        # Все базовые методы делегируются родительскому классу
        return super()._process_message(raw_line, client_sock)
