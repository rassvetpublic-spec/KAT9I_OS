# -*- coding: utf-8 -*-
"""
Прототип изолированного Rust Core Runtime и безопасного IPC-сервера KAT9I_OS (Issue #41, Gate G3).

Архитектурные свойства:
1. Физически отдельный локальный процесс ядра (Rust Core Runtime).
2. Безопасный транспорт IPC: локальный сокет / Loopback TCP (127.0.0.1) со строгим сессионным токеном.
3. Узкий типизированный API (JSON-RPC стиль по схеме CoreIpcMessage.json):
   - core.ping: проверка доступности (health check);
   - core.get_system_state: получение текущего состояния ядра и задач;
   - core.create_task: создание детерминированной задачи;
   - core.cancel_task: отмена задачи;
   - core.subscribe_events: подписка на стрим системных событий.
4. Полная независимость Core от UI:
   - Падение или закрытие клиента (Electron Renderer/Main) не уничтожает состояние активных задач.
   - Reconnect: повторное подключение мгновенно возвращает актуальное состояние и возобновляет получение событий.
5. Изоляция: любые попытки передать произвольные shell-команды или неразрешённые методы отклоняются (METHOD_NOT_ALLOWED).
"""

import json
import socket
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent

class Kat9iCoreServer:
    def __init__(self, host: str = "127.0.0.1", port: int = 0, auth_token: Optional[str] = None):
        self.host = host
        self.requested_port = port
        self.auth_token = auth_token or f"tok-{uuid.uuid4().hex[:16]}"
        self.server_socket: Optional[socket.socket] = None
        self.actual_port: int = 0
        self.is_running = False
        self._thread: Optional[threading.Thread] = None

        # Внутреннее состояние задач ядра (Core State):
        self.lock = threading.Lock()
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self.subscribers: list[socket.socket] = []
        self.event_counter = 0

    def start(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.requested_port))
        self.actual_port = self.server_socket.getsockname()[1]
        self.server_socket.listen(5)
        self.is_running = True

        self._thread = threading.Thread(target=self._accept_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self.is_running = False
        if self.server_socket:
            try:
                self.server_socket.close()
            except Exception:
                pass
        with self.lock:
            for s in self.subscribers:
                try:
                    s.close()
                except Exception:
                    pass
            self.subscribers.clear()

    def _accept_loop(self):
        while self.is_running:
            try:
                client_sock, _ = self.server_socket.accept()
                client_thread = threading.Thread(target=self._handle_client, args=(client_sock,), daemon=True)
                client_thread.start()
            except Exception:
                break

    def _handle_client(self, client_sock: socket.socket):
        buffer = ""
        while self.is_running:
            try:
                data = client_sock.recv(4096)
                if not data:
                    break
                buffer += data.decode("utf-8")
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if not line:
                        continue
                    response = self._process_message(line, client_sock)
                    if response:
                        client_sock.sendall((json.dumps(response) + "\n").encode("utf-8"))
            except Exception:
                break

        with self.lock:
            if client_sock in self.subscribers:
                self.subscribers.remove(client_sock)
        try:
            client_sock.close()
        except Exception:
            pass

    def _broadcast_event(self, event_type: str, task_id: str, payload: Dict[str, Any]):
        with self.lock:
            self.event_counter += 1
            evt_msg = {
                "message_id": f"msg-evt-{uuid.uuid4().hex[:12]}",
                "correlation_id": f"corr-evt-{self.event_counter}",
                "type": "EVENT_STREAM",
                "method": "core.subscribe_events",
                "payload": {
                    "event_id": f"evt-{uuid.uuid4().hex[:12]}",
                    "event_type": event_type,
                    "task_id": task_id,
                    "sequence_number": self.event_counter,
                    "payload": payload,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            raw = (json.dumps(evt_msg) + "\n").encode("utf-8")
            stale = []
            for s in self.subscribers:
                try:
                    s.sendall(raw)
                except Exception:
                    stale.append(s)
            for s in stale:
                if s in self.subscribers:
                    self.subscribers.remove(s)

    def _process_message(self, raw_line: str, client_sock: socket.socket) -> Dict[str, Any]:
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

        msg_id = msg.get("message_id", f"msg-resp-{uuid.uuid4().hex[:12]}")
        corr_id = msg.get("correlation_id", "corr-none")
        method = msg.get("method")
        token = msg.get("auth_token")

        # 1. Проверка аутентификации (Security Boundary)
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

        # 2. Обработка разрешённых методов (Narrow API Surface)
        if method == "core.ping":
            return {
                "message_id": f"msg-resp-{uuid.uuid4().hex[:12]}",
                "correlation_id": corr_id,
                "type": "RESPONSE",
                "method": "core.ping",
                "payload": {"status": "PONG", "server": "KAT9I_OS_CORE_PROTOTYPE"},
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        elif method == "core.get_system_state":
            with self.lock:
                task_list = list(self.tasks.values())
            return {
                "message_id": f"msg-resp-{uuid.uuid4().hex[:12]}",
                "correlation_id": corr_id,
                "type": "RESPONSE",
                "method": "core.get_system_state",
                "payload": {
                    "core_status": "ONLINE",
                    "active_tasks_count": len(task_list),
                    "tasks": task_list
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        elif method == "core.create_task":
            payload = msg.get("payload", {})
            task_id = payload.get("task_id", f"task-{uuid.uuid4().hex[:8]}")
            goal = payload.get("goal", "Deterministic Test Task")

            with self.lock:
                task_record = {
                    "task_id": task_id,
                    "goal": goal,
                    "status": "ACTIVE",
                    "progress_percent": 10,
                    "worker_id": "id-worker-core-internal",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
                self.tasks[task_id] = task_record

            self._broadcast_event("TASK_CREATED", task_id, {"goal": goal})
            return {
                "message_id": f"msg-resp-{uuid.uuid4().hex[:12]}",
                "correlation_id": corr_id,
                "type": "RESPONSE",
                "method": "core.create_task",
                "payload": {"task": task_record},
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        elif method == "core.cancel_task":
            payload = msg.get("payload", {})
            task_id = payload.get("task_id")
            with self.lock:
                if task_id in self.tasks:
                    self.tasks[task_id]["status"] = "CANCELLED"
                    self.tasks[task_id]["updated_at"] = datetime.now(timezone.utc).isoformat()
                    updated = self.tasks[task_id]
                else:
                    updated = None

            if updated:
                self._broadcast_event("TASK_CANCELLED", task_id, {"reason": "Cancelled via UI request"})
                return {
                    "message_id": f"msg-resp-{uuid.uuid4().hex[:12]}",
                    "correlation_id": corr_id,
                    "type": "RESPONSE",
                    "method": "core.cancel_task",
                    "payload": {"task": updated},
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            else:
                return {
                    "message_id": f"msg-resp-{uuid.uuid4().hex[:12]}",
                    "correlation_id": corr_id,
                    "type": "ERROR",
                    "method": "core.cancel_task",
                    "payload": {},
                    "error": {"code": "TASK_NOT_FOUND", "message": f"Task {task_id} not found"},
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }

        elif method == "core.subscribe_events":
            with self.lock:
                if client_sock not in self.subscribers:
                    self.subscribers.append(client_sock)
            return {
                "message_id": f"msg-resp-{uuid.uuid4().hex[:12]}",
                "correlation_id": corr_id,
                "type": "RESPONSE",
                "method": "core.subscribe_events",
                "payload": {"subscribed": True},
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        else:
            return {
                "message_id": f"msg-resp-{uuid.uuid4().hex[:12]}",
                "correlation_id": corr_id,
                "type": "ERROR",
                "method": method or "unknown",
                "payload": {},
                "error": {"code": "METHOD_NOT_ALLOWED", "message": f"Method {method} is not permitted on this IPC interface"},
                "timestamp": datetime.now(timezone.utc).isoformat()
            }


class Kat9iElectronIpcClient:
    """Клиент границы Preload в Electron Main process."""
    def __init__(self, host: str, port: int, auth_token: str):
        self.host = host
        self.port = port
        self.auth_token = auth_token
        self.sock: Optional[socket.socket] = None

    def connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.host, self.port))

    def disconnect(self):
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None

    def send_request(self, method: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if not self.sock:
            raise ConnectionError("Not connected to Core IPC")

        corr_id = f"corr-{uuid.uuid4().hex[:12]}"
        req = {
            "message_id": f"msg-{uuid.uuid4().hex[:12]}",
            "correlation_id": corr_id,
            "type": "REQUEST",
            "method": method,
            "auth_token": self.auth_token,
            "payload": payload or {},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        self.sock.sendall((json.dumps(req) + "\n").encode("utf-8"))

        # Чтение ответа
        buffer = ""
        while "\n" not in buffer:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise ConnectionError("Connection lost during read")
            buffer += chunk.decode("utf-8")

        line, _ = buffer.split("\n", 1)
        return json.loads(line.strip())
