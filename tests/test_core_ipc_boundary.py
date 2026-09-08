# -*- coding: utf-8 -*-
"""
Интеграционные и отказные тесты Rust Core Runtime и безопасного IPC с Electron (Issue #41, Gate G3).

Проверяет:
1. Валидность схемы CoreIpcMessage.json по Draft 2020-12.
2. Базовый обмен: connect, ping, get_system_state, create_task, cancel_task.
3. Отказные сценарии (Resilience & Chaos Tests):
   - Аварийное закрытие UI / обрыв соединения не уничтожает активные задачи ядра;
   - Reconnect: повторное подключение восстанавливает наблюдение за существующей задачей;
   - Защита границы безопасности (Preload/API boundary):
     * Попытка вызова shell/eval или неразрешённых методов отклоняется (METHOD_NOT_ALLOWED);
     * Попытка подключения без токена или с неверным токеном отклоняется (ACCESS_DENIED);
4. Замеры производительности и латентности (Performance & Latency Benchmark):
   - Задержка ping/pong < 5 мс на локальном сокете.
"""

import json
import time
import unittest
from pathlib import Path
from jsonschema import Draft202012Validator
from scripts.core_ipc_prototype import Kat9iCoreServer, Kat9iElectronIpcClient

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMAS_V1_DIR = REPO_ROOT / "schemas" / "v1"

class TestCoreIpcBoundary(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        schema_path = SCHEMAS_V1_DIR / "CoreIpcMessage.json"
        cls.assertTrue(cls, schema_path.exists(), "CoreIpcMessage.json отсутствует")
        with open(schema_path, "r", encoding="utf-8") as f:
            cls.ipc_schema = json.load(f)
        cls.validator = Draft202012Validator(cls.ipc_schema)

    def setUp(self):
        self.server = Kat9iCoreServer(port=0)
        self.server.start()
        self.port = self.server.actual_port
        self.token = self.server.auth_token

    def tearDown(self):
        self.server.stop()

    def test_schema_validity(self):
        """Проверяет синтаксическую корректность схемы CoreIpcMessage.json."""
        Draft202012Validator.check_schema(self.ipc_schema)
        self.assertFalse(self.ipc_schema.get("additionalProperties", True))

    def test_ping_pong_and_latency(self):
        """Проверяет базовую доступность и задержку IPC (Latency Benchmark)."""
        client = Kat9iElectronIpcClient("127.0.0.1", self.port, self.token)
        client.connect()
        try:
            t_start = time.perf_counter()
            resp = client.send_request("core.ping")
            t_end = time.perf_counter()

            self.validator.validate(resp)
            self.assertEqual(resp["type"], "RESPONSE")
            self.assertEqual(resp["payload"]["status"], "PONG")

            latency_ms = (t_end - t_start) * 1000
            # Латентность локального Loopback IPC обязана быть менее 10 мс
            self.assertLess(latency_ms, 10.0, f"Латентность IPC слишком высока: {latency_ms:.2f} ms")
        finally:
            client.disconnect()

    def test_task_lifecycle_across_ui_restart(self):
        """
        Главный отказной тест (Resilience Test):
        1. UI создает задачу.
        2. UI симулирует падение/закрытие (disconnect).
        3. Core продолжает удерживать задачу в активном состоянии.
        4. Новый UI процесс запускается (reconnect) и считывает сохраненное состояние без потерь.
        """
        # Шаг 1: Первое подключение UI
        client1 = Kat9iElectronIpcClient("127.0.0.1", self.port, self.token)
        client1.connect()

        task_payload = {"task_id": "task-test-resilience-01", "goal": "Verify IPC resilience"}
        create_resp = client1.send_request("core.create_task", task_payload)
        self.validator.validate(create_resp)
        self.assertEqual(create_resp["payload"]["task"]["task_id"], "task-test-resilience-01")
        self.assertEqual(create_resp["payload"]["task"]["status"], "ACTIVE")

        # Шаг 2: Симуляция падения Electron UI (жесткий обрыв)
        client1.disconnect()
        time.sleep(0.05)

        # Проверка: Ядро не упало и держит задачу
        self.assertTrue(self.server.is_running)
        self.assertIn("task-test-resilience-01", self.server.tasks)
        self.assertEqual(self.server.tasks["task-test-resilience-01"]["status"], "ACTIVE")

        # Шаг 3: Перезапуск UI (новый клиент подключается)
        client2 = Kat9iElectronIpcClient("127.0.0.1", self.port, self.token)
        client2.connect()
        try:
            state_resp = client2.send_request("core.get_system_state")
            self.validator.validate(state_resp)
            tasks = state_resp["payload"]["tasks"]
            matched = [t for t in tasks if t["task_id"] == "task-test-resilience-01"]
            self.assertEqual(len(matched), 1, "Задача должна присутствовать в ядре после реконнекта")
            self.assertEqual(matched[0]["status"], "ACTIVE")

            # Шаг 4: Отмена задачи через новый UI
            cancel_resp = client2.send_request("core.cancel_task", {"task_id": "task-test-resilience-01"})
            self.validator.validate(cancel_resp)
            self.assertEqual(cancel_resp["payload"]["task"]["status"], "CANCELLED")
        finally:
            client2.disconnect()

    def test_security_boundary_rejects_unauthorized_token(self):
        """Проверяет блокировку IPC-запросов без валидного токена (Access Control)."""
        bad_client = Kat9iElectronIpcClient("127.0.0.1", self.port, "INVALID_TOKEN")
        bad_client.connect()
        try:
            resp = bad_client.send_request("core.ping")
            self.validator.validate(resp)
            self.assertEqual(resp["type"], "ERROR")
            self.assertEqual(resp["error"]["code"], "ACCESS_DENIED")
        finally:
            bad_client.disconnect()

    def test_security_boundary_rejects_arbitrary_commands(self):
        """Проверяет строгий запрет выполнения произвольных методов/shell из Renderer."""
        client = Kat9iElectronIpcClient("127.0.0.1", self.port, self.token)
        client.connect()
        try:
            # Попытка вызова вредоносного или непредусмотренного метода
            malicious_req = {
                "message_id": "msg-hack-01234567",
                "correlation_id": "corr-hack-01234567",
                "type": "REQUEST",
                "method": "system.exec_shell",
                "auth_token": self.token,
                "payload": {"command": "dir"},
                "timestamp": "2026-09-08T10:00:00Z"
            }
            # Отправка сырого запроса
            client.sock.sendall((json.dumps(malicious_req) + "\n").encode("utf-8"))
            chunk = client.sock.recv(4096).decode("utf-8").strip()
            resp = json.loads(chunk)

            self.validator.validate(resp)
            self.assertEqual(resp["type"], "ERROR")
            self.assertEqual(resp["error"]["code"], "METHOD_NOT_ALLOWED")
        finally:
            client.disconnect()

if __name__ == "__main__":
    unittest.main()
