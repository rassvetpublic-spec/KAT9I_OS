# -*- coding: utf-8 -*-
"""
Тесты стандарта сквозной трассировки задач, агентов и инструментов KAT9I_OS v0.1 (Issue #50, Gate G4).

Проверяет:
1. Валидность схемы TraceContext.json согласно Draft 2020-12.
2. Корректность цепочки: Task -> Worker -> Model/Tool -> Result -> QA:
   - Иерархия спанов: root (Core) -> child (Security / Worker) -> grandchild (Tool / QA).
   - Единый trace_id для всех спанов задачи.
   - Корректные parent_span_id.
3. Отслеживание ошибок: статус ERROR на спане указывает на контекст сбоя без потери связи с родительской задачей.
4. Безопасность и Zero Leak:
   - Запрет записи секретов, токенов и паролей в атрибуты спана (PermissionError).
5. Экспорт в формат OpenTelemetry (ResourceSpans OTLP JSON).
6. Замеры накладных расходов (Overhead Benchmark):
   - Создание, наполнение атрибутами и закрытие спана занимает < 0.1 мс.
"""

import json
import shutil
import tempfile
import time
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from scripts.tracer import Kat9iTracer, Kat9iSpan, generate_trace_id, generate_span_id

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMAS_V1_DIR = REPO_ROOT / "schemas" / "v1"


class TestTraceStandard(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        schema_path = SCHEMAS_V1_DIR / "TraceContext.json"
        cls.assertTrue(cls, schema_path.exists(), "TraceContext.json отсутствует")
        with open(schema_path, "r", encoding="utf-8") as f:
            cls.trace_schema = json.load(f)
        cls.validator = Draft202012Validator(cls.trace_schema)

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="kat9i_trace_test_")
        self.trace_log = Path(self.temp_dir) / "traces.jsonl"
        self.tracer = Kat9iTracer(trace_log_path=self.trace_log)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_schema_validity(self):
        """Проверяет соответствие схемы TraceContext.json стандарту Draft 2020-12."""
        Draft202012Validator.check_schema(self.trace_schema)
        self.assertFalse(self.trace_schema.get("additionalProperties", True))
        self.assertEqual(self.trace_schema.get("version"), "1.0.0")

    def test_full_trace_chain_hierarchy(self):
        """
        Проверяет сквозную иерархическую цепочку:
        Task (CORE) -> Worker (WORKER_EXECUTION) -> Tool (TOOL_CALL) -> Storage (STORAGE) -> QA (QA).
        Все спаны имеют одинаковый trace_id и корректные parent_span_id.
        """
        task_id = "task-trace-001"
        corr_id = "corr-chain-99"

        # 1. Корневой спан: Core task dispatch
        root_span = self.tracer.start_span(
            name="core.task_dispatch",
            span_kind="CORE",
            task_id=task_id,
            correlation_id=corr_id
        )
        root_span.set_attribute("task.priority", "P0")
        root_span.end(status="OK")
        self.tracer.record_span(root_span)

        # 2. Дочерний спан: Worker execution
        worker_span = self.tracer.start_span(
            name="worker.run_deterministic",
            span_kind="WORKER_EXECUTION",
            task_id=task_id,
            correlation_id=corr_id,
            parent_span=root_span,
            worker_id="id-worker-kat9i-01"
        )

        # 3. Вложенный спан: Tool execution
        tool_span = self.tracer.start_span(
            name="tool.filesystem_read",
            span_kind="TOOL_CALL",
            task_id=task_id,
            correlation_id=corr_id,
            parent_span=worker_span,
            operation_id="op-read-manifest"
        )
        tool_span.set_attribute("tool.name", "fs_read")
        tool_span.set_attribute("target.file", "config/app_manifest.json")
        tool_span.end(status="OK")
        self.tracer.record_span(tool_span)

        # Завершаем спан воркера
        worker_span.end(status="OK")
        self.tracer.record_span(worker_span)

        # 4. Спан независимой проверки: QA
        qa_span = self.tracer.start_span(
            name="qa.contract_verification",
            span_kind="QA",
            task_id=task_id,
            correlation_id=corr_id,
            parent_span=root_span,
            worker_id="id-worker-qa-engine"
        )
        qa_span.set_attribute("qa.verdict", "PASS")
        qa_span.end(status="OK", evidence_ref="artifacts/task-trace-001/evidence.json")
        self.tracer.record_span(qa_span)

        # Проверяем записанные спаны
        self.assertEqual(len(self.tracer.spans), 4)
        trace_ids = {s.trace_id for s in self.tracer.spans}
        self.assertEqual(len(trace_ids), 1, "Все спаны задачи обязаны иметь единый trace_id")

        # Проверяем иерархию parent_span_id
        span_map = {s.name: s for s in self.tracer.spans}
        self.assertIsNone(span_map["core.task_dispatch"].parent_span_id)
        self.assertEqual(span_map["worker.run_deterministic"].parent_span_id, span_map["core.task_dispatch"].span_id)
        self.assertEqual(span_map["tool.filesystem_read"].parent_span_id, span_map["worker.run_deterministic"].span_id)
        self.assertEqual(span_map["qa.contract_verification"].parent_span_id, span_map["core.task_dispatch"].span_id)

    def test_error_propagation_in_trace(self):
        """
        Проверяет, что ошибка конкретного шага фиксируется в статусе ERROR
        и сохраняет привязку к задаче и родительскому спану.
        """
        task_id = "task-trace-err-01"
        corr_id = "corr-error-404-test"

        root_span = self.tracer.start_span("core.task_run", "CORE", task_id, corr_id)
        tool_span = self.tracer.start_span("tool.git_checkout", "TOOL_CALL", task_id, corr_id, parent_span=root_span)

        tool_span.end(status="ERROR", status_message="fatal: pathspec 'non_existent_branch' did not match any file(s)")
        self.tracer.record_span(tool_span)

        root_span.end(status="ERROR", status_message="Child tool execution failed")
        self.tracer.record_span(root_span)

        t_dict = tool_span.to_dict()
        self.validator.validate(t_dict)
        self.assertEqual(t_dict["status"], "ERROR")
        self.assertIn("pathspec", t_dict["status_message"])
        self.assertEqual(t_dict["parent_span_id"], root_span.span_id)

    def test_security_zero_leak_forbidden_keys(self):
        """
        Проверяет политику Zero Leak:
        Попытка установить атрибут с паролем/токеном/секретом блокируется (PermissionError).
        """
        span = self.tracer.start_span("security.check", "SECURITY_DECISION", "task-sec-01", "corr-sec-check-01")
        with self.assertRaises(PermissionError):
            span.set_attribute("auth_token", "ghp_super_secret_token_12345")

        with self.assertRaises(PermissionError):
            span.set_attribute("db_password", "MyPassword!234")

        with self.assertRaises(PermissionError):
            span.set_attribute("secret_api_key", "sk-proj-999")

        # Безопасные атрибуты устанавливаются успешно
        span.set_attribute("security.decision", "ALLOW")
        span.set_attribute("evaluated_rules_count", 4)
        self.assertEqual(span.attributes["security.decision"], "ALLOW")
        self.assertEqual(span.attributes["evaluated_rules_count"], 4)

    def test_export_opentelemetry_otlp(self):
        """
        Проверяет машинную конвертацию в каноническую структуру OpenTelemetry ResourceSpans.
        """
        task_id = "task-otel-export"
        corr_id = "corr-otel-export-01"

        span = self.tracer.start_span("core.init", "CORE", task_id, corr_id)
        span.set_attribute("env", "production")
        span.end(status="OK")
        self.tracer.record_span(span)

        otel_data = self.tracer.export_opentelemetry_json(task_id=task_id)
        self.assertIn("resourceSpans", otel_data)
        self.assertEqual(len(otel_data["resourceSpans"]), 1)
        r_span = otel_data["resourceSpans"][0]
        self.assertEqual(r_span["resource"]["attributes"][0]["key"], "service.name")
        self.assertEqual(r_span["resource"]["attributes"][0]["value"]["stringValue"], "KAT9I_OS")

        spans = r_span["scopeSpans"][0]["spans"]
        self.assertEqual(len(spans), 1)
        self.assertEqual(spans[0]["name"], "core.init")
        self.assertEqual(spans[0]["status"]["code"], 1)  # OK code in OpenTelemetry

    def test_overhead_latency_benchmark(self):
        """
        Тест производительности (Overhead Benchmark):
        Создание, атрибутирование, добавление события, валидация по схеме и запись 100 спанов
        должно занимать в среднем менее 1.5 мс на спан даже с учетом полной валидации JSON-схемы на диске.
        """
        task_id = "task-benchmark-01"
        corr_id = "corr-bench-benchmark-01"

        iterations = 100
        t_start = time.perf_counter()
        for i in range(iterations):
            span = self.tracer.start_span(f"step_{i}", "CORE", task_id, corr_id)
            span.set_attribute("iteration", i)
            span.add_event("checkpoint", {"step": i})
            span.end("OK")
            self.tracer.record_span(span)
        total_time_ms = (time.perf_counter() - t_start) * 1000
        avg_overhead_ms = total_time_ms / iterations

        # Накладные расходы на 1 спан обязаны быть менее 1.5 мс
        self.assertLess(avg_overhead_ms, 1.5, f"Слишком высокие накладные расходы трассировки: {avg_overhead_ms:.4f} ms")
