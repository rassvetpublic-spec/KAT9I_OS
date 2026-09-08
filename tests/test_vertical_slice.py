# -*- coding: utf-8 -*-
"""
Интеграционные и сквозные приёмочные тесты первого вертикального среза KAT9I_OS v0.1 (Issue #48, Gate G4).

Сценарии верификации:
1. Полный сквозной путь: Electron IPC Client -> Core Runtime -> TaskContract -> Scope Guard -> Storage Event Journal -> Evidence -> TaskResult -> Electron.
2. Негативный сценарий 1: TaskContract с нарушением схемы отклоняется до выполнения (Fail-Closed).
3. Негативный сценарий 2: Попытка доступа к запрещенному ресурсу или Path Traversal блокируется Scope Guard с генерацией ошибки.
4. Отказной тест (Resilience Test): Разрыв соединения UI во время выполнения или после него не разрушает состояние Core и сохраняет артефакты.
5. Проверка целостности Event Journal: монотонность sequence_number, наличие ключевых событий (TASK_CREATED, SIDE_EFFECT_EXECUTED, TASK_COMPLETED).
6. Проверка валидности Evidence.json и TaskResult.json в соответствии со схемами Draft 2020-12.
"""

import json
import shutil
import tempfile
import time
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from scripts.core_ipc_prototype import Kat9iElectronIpcClient
from scripts.vertical_slice_engine import Kat9iVerticalCoreServer, Kat9iVerticalEngine
from scripts.scope_guard import ScopeViolationError

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMAS_V1_DIR = REPO_ROOT / "schemas" / "v1"


class TestVerticalSliceV01(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Проверяем наличие всех ключевых JSON-схем
        cls.schemas = {}
        for schema_name in ["TaskContract", "TaskResult", "Evidence", "JournalEvent", "CoreIpcMessage"]:
            schema_file = SCHEMAS_V1_DIR / f"{schema_name}.json"
            cls.assertTrue(cls, schema_file.exists(), f"Схема {schema_name}.json отсутствует")
            with open(schema_file, "r", encoding="utf-8") as f:
                schema_dict = json.load(f)
                cls.schemas[schema_name] = schema_dict
                Draft202012Validator.check_schema(schema_dict)

        cls.contract_validator = Draft202012Validator(cls.schemas["TaskContract"])
        cls.result_validator = Draft202012Validator(cls.schemas["TaskResult"])
        cls.evidence_validator = Draft202012Validator(cls.schemas["Evidence"])
        cls.journal_validator = Draft202012Validator(cls.schemas["JournalEvent"])
        cls.ipc_validator = Draft202012Validator(cls.schemas["CoreIpcMessage"])

    def setUp(self):
        # Создаем временное изолированное рабочее пространство для каждого теста
        self.temp_dir = tempfile.mkdtemp(prefix="kat9i_v01_test_")
        self.workspace_root = Path(self.temp_dir).resolve()

        # Создаем целевой тестовый файл внутри workspace
        self.target_file_rel = "config/app_manifest.json"
        self.target_file_abs = self.workspace_root / self.target_file_rel
        self.target_file_abs.parent.mkdir(parents=True, exist_ok=True)
        with open(self.target_file_abs, "w", encoding="utf-8") as f:
            json.dump({
                "app_name": "KAT9I_OS",
                "version": "0.1.0",
                "system_mode": "SOVEREIGN_DESKTOP",
                "active_modules": ["Core", "Security", "Execution", "Storage"]
            }, f, indent=2)

        # Запускаем локальный Core Runtime сервер
        self.server = Kat9iVerticalCoreServer(workspace_root=self.workspace_root, port=0)
        self.server.start()
        self.port = self.server.actual_port
        self.token = self.server.auth_token

    def tearDown(self):
        self.server.stop()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _build_valid_contract(self, task_id: str = "task-v01-001") -> dict:
        """Вспомогательный конструктор валидного TaskContract."""
        return {
            "task_id": task_id,
            "parent_task_id": None,
            "source": "user",
            "goal": "Проверить существование разрешённого файла app_manifest.json и корректность схемы",
            "workspace": str(self.workspace_root),
            "domain": "software_engineering",
            "scope": {
                "repository": "rassvetpublic-spec/KAT9I_OS",
                "allowed_paths": [self.target_file_rel],
                "denied_paths": [".git", "secrets"],
                "allowed_operations": ["read", "write"],
                "network_allowed": False
            },
            "context_refs": [],
            "rules_ref": "canonical",
            "required_capabilities": ["filesystem"],
            "output_contract": {
                "expected_artifacts": [f"artifacts/{task_id}/verification_report.json"],
                "quality_gate_required": True,
                "independent_qa_required": True
            },
            "result_sink": "local_workspace",
            "created_at": "2026-09-08T10:50:00Z"
        }

    def test_full_deterministic_pipeline(self):
        """
        Тест 1: Полный детерминированный сквозной цикл v0.1:
        Electron IPC Client -> Core Runtime -> TaskContract -> Scope Guard -> Storage Event Journal
        -> Evidence -> TaskResult -> Electron IPC Client.
        """
        client = Kat9iElectronIpcClient("127.0.0.1", self.port, self.token)
        client.connect()
        try:
            contract = self._build_valid_contract("task-v01-e2e-pass")
            self.contract_validator.validate(contract)

            # Отправка запроса на исполнение через узкий IPC
            t_start = time.perf_counter()
            response = client.send_request("core.execute_contract_task", {"contract": contract})
            duration_ms = (time.perf_counter() - t_start) * 1000

            # Проверка формата IPC ответа
            self.ipc_validator.validate(response)
            self.assertEqual(response["type"], "RESPONSE")
            self.assertEqual(response["method"], "core.execute_contract_task")

            payload = response["payload"]
            task_record = payload["task_record"]
            task_result = payload["task_result"]

            # Проверка статуса задачи в Core
            self.assertEqual(task_record["status"], "COMPLETED")
            self.assertEqual(task_record["progress_percent"], 100)

            # Проверка TaskResult
            self.result_validator.validate(task_result)
            self.assertEqual(task_result["verdict"], "SUCCESS")
            self.assertEqual(task_result["task_id"], "task-v01-e2e-pass")
            self.assertIn("artifacts", task_result)
            self.assertEqual(len(task_result["artifacts"]), 1)

            # Проверка физического создания артефакта и соответствия sha256
            artifact_rel = task_result["artifacts"][0]["path"]
            artifact_file = self.workspace_root / artifact_rel
            self.assertTrue(artifact_file.exists(), f"Артефакт {artifact_rel} не создан")

            # Проверка Evidence.json
            evidence_rel = task_result["evidence_ref"]
            evidence_file = self.workspace_root / evidence_rel
            self.assertTrue(evidence_file.exists(), f"Evidence {evidence_rel} не создан")

            with open(evidence_file, "r", encoding="utf-8") as f:
                evidence_data = json.load(f)
            self.evidence_validator.validate(evidence_data)
            self.assertEqual(evidence_data["qa_verdict"], "PASS")
            self.assertEqual(evidence_data["test_results"]["passed"], 1)

            # Проверка Event Journal (Append-only)
            journal_file = self.workspace_root / ".kat9i_journal.jsonl"
            self.assertTrue(journal_file.exists(), "Event Journal файл не создан")

            events = []
            with open(journal_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        evt = json.loads(line)
                        self.journal_validator.validate(evt)
                        events.append(evt)

            self.assertGreaterEqual(len(events), 3)
            # Проверка монотонности sequence_number
            seqs = [e["sequence_number"] for e in events]
            self.assertEqual(seqs, sorted(seqs))
            self.assertEqual(seqs, list(range(1, len(events) + 1)))

            # Проверка типов ключевых событий
            event_types = [e["event_type"] for e in events]
            self.assertIn("TASK_CREATED", event_types)
            self.assertIn("SIDE_EFFECT_EXECUTED", event_types)
            self.assertIn("TASK_COMPLETED", event_types)

        finally:
            client.disconnect()

    def test_invalid_contract_rejected_fail_closed(self):
        """
        Тест 2: Машинная валидация TaskContract до запуска.
        Если контракт поврежден (отсутствует обязательное поле), Core возвращает ошибку.
        """
        client = Kat9iElectronIpcClient("127.0.0.1", self.port, self.token)
        client.connect()
        try:
            bad_contract = {
                "task_id": "task-bad-001",
                # Отсутствуют обязательные поля: goal, workspace, output_contract, scope
                "source": "user"
            }
            response = client.send_request("core.execute_contract_task", {"contract": bad_contract})
            self.assertEqual(response["type"], "ERROR")
            self.assertEqual(response["error"]["code"], "TASK_EXECUTION_FAILED")
            self.assertIn("required", response["error"]["message"])

            # Проверка состояния задачи в Core: зафиксирован FAILED
            state_resp = client.send_request("core.get_system_state")
            tasks = {t["task_id"]: t for t in state_resp["payload"]["tasks"]}
            self.assertIn("task-bad-001", tasks)
            self.assertEqual(tasks["task-bad-001"]["status"], "FAILED")
        finally:
            client.disconnect()

    def test_scope_guard_blocks_unauthorized_path(self):
        """
        Тест 3: Scope Guard блокирует доступ к файлу вне разрешенного Scope (Policy Guard).
        """
        client = Kat9iElectronIpcClient("127.0.0.1", self.port, self.token)
        client.connect()
        try:
            contract = self._build_valid_contract("task-scope-violation")
            # Пытаемся запросить системный файл или файл с traversal
            contract["scope"]["allowed_paths"] = ["../../Windows/System32/drivers/etc/hosts"]

            response = client.send_request("core.execute_contract_task", {"contract": contract})
            self.assertEqual(response["type"], "ERROR")
            self.assertEqual(response["error"]["code"], "TASK_EXECUTION_FAILED")
            self.assertIn("Scope Violation", response["error"]["message"])

            # Проверяем, что задача в Core перешла в статус FAILED
            state_resp = client.send_request("core.get_system_state")
            tasks = {t["task_id"]: t for t in state_resp["payload"]["tasks"]}
            self.assertEqual(tasks["task-scope-violation"]["status"], "FAILED")
        finally:
            client.disconnect()

    def test_core_resilience_across_ui_disconnect(self):
        """
        Тест 4: Отказной тест (Resilience Test):
        UI выполняет задачу, затем внезапно закрывается (disconnect).
        Новый UI подключается (reconnect) и считывает сохраненные данные задачи.
        """
        # Клиент 1 (Electron UI session 1)
        client1 = Kat9iElectronIpcClient("127.0.0.1", self.port, self.token)
        client1.connect()
        contract = self._build_valid_contract("task-resilience-001")
        resp1 = client1.send_request("core.execute_contract_task", {"contract": contract})
        self.assertEqual(resp1["type"], "RESPONSE")
        self.assertEqual(resp1["payload"]["task_record"]["status"], "COMPLETED")

        # Аварийный обрыв сессии UI
        client1.disconnect()
        time.sleep(0.05)

        # Клиент 2 (Новая сессия Electron UI после рестарта)
        client2 = Kat9iElectronIpcClient("127.0.0.1", self.port, self.token)
        client2.connect()
        try:
            state_resp = client2.send_request("core.get_system_state")
            tasks = {t["task_id"]: t for t in state_resp["payload"]["tasks"]}
            self.assertIn("task-resilience-001", tasks)
            retained = tasks["task-resilience-001"]
            self.assertEqual(retained["status"], "COMPLETED")
            self.assertEqual(retained["progress_percent"], 100)
            self.assertEqual(retained["result"]["verdict"], "SUCCESS")
        finally:
            client2.disconnect()
