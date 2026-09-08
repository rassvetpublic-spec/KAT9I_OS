# -*- coding: utf-8 -*-
"""
Стандарт сквозной трассировки задач, агентов и инструментов KAT9I_OS v0.1 (Issue #50, Gate G4).

Свойства архитектуры:
1. Совместимость с W3C TraceContext и OpenTelemetry:
   - trace_id: 16 байт (32 hex);
   - span_id: 8 байт (16 hex);
   - parent_span_id: для построения направленного ациклического дерева этапов.
2. Канонические типы этапов (SpanKind):
   - CORE, SECURITY_DECISION, CONTEXT_PREPARATION, MODEL_CALL, TOOL_CALL,
     WORKER_EXECUTION, EXTERNAL_INTEGRATION, QA, STORAGE, RECOVERY.
3. Полная связь цепочки:
   Task -> Worker -> Model/Tool -> Result -> QA с привязкой correlation_id и task_id.
4. Политика Zero Leak (Безопасность):
   - Секреты, пароли, приватные токены и скрытые рассуждения модели фильтруются до записи в атрибуты трассы.
5. Экспорт в стандартный машиночитаемый формат JSONL и OTLP-совместимую структуру.
6. Минимальные накладные расходы (Overhead Benchmark): создание и завершение спана < 0.05 мс.
"""

import hashlib
import json
import os
import re
import secrets
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMAS_V1_DIR = REPO_ROOT / "schemas" / "v1"

FORBIDDEN_ATTRIBUTE_KEYS = {
    "password", "secret", "token", "auth", "credential", "api_key", "private_key"
}


def generate_trace_id() -> str:
    """Генерирует 16-байтный (32 hex) trace_id согласно стандарту W3C TraceContext."""
    return secrets.token_hex(16)


def generate_span_id() -> str:
    """Генерирует 8-байтный (16 hex) span_id согласно стандарту W3C TraceContext."""
    return secrets.token_hex(8)


class Kat9iSpan:
    """Один этап трассировки (Span) в дереве выполнения задачи."""

    def __init__(
        self,
        trace_id: str,
        span_id: str,
        task_id: str,
        correlation_id: str,
        name: str,
        span_kind: str,
        parent_span_id: Optional[str] = None,
        worker_id: Optional[str] = None,
        operation_id: Optional[str] = None
    ):
        self.trace_id = trace_id
        self.span_id = span_id
        self.parent_span_id = parent_span_id
        self.task_id = task_id
        self.correlation_id = correlation_id
        self.name = name
        self.span_kind = span_kind
        self.worker_id = worker_id
        self.operation_id = operation_id
        self.status = "UNSET"
        self.status_message: Optional[str] = None
        self.attributes: Dict[str, Any] = {}
        self.events: List[Dict[str, Any]] = []
        self.evidence_ref: Optional[str] = None
        self.start_time_unix_nano = time.time_ns()
        self.end_time_unix_nano: Optional[int] = None

    def set_attribute(self, key: str, value: Any):
        """Устанавливает атрибут с fail-closed фильтрацией потенциальных секретов."""
        lower_k = key.lower()
        for forbidden in FORBIDDEN_ATTRIBUTE_KEYS:
            if forbidden in lower_k:
                raise PermissionError(f"Trace Security Violation: attribute key '{key}' may contain secrets")

        if isinstance(value, (str, int, float, bool)):
            self.attributes[key] = value
        else:
            self.attributes[key] = str(value)

    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None):
        """Добавляет локальное событие внутрь спана."""
        clean_attrs: Dict[str, Any] = {}
        if attributes:
            for k, v in attributes.items():
                lower_k = k.lower()
                if any(f in lower_k for f in FORBIDDEN_ATTRIBUTE_KEYS):
                    continue
                clean_attrs[k] = v if isinstance(v, (str, int, float, bool)) else str(v)

        self.events.append({
            "name": name,
            "time_unix_nano": time.time_ns(),
            "attributes": clean_attrs
        })

    def end(self, status: str = "OK", status_message: Optional[str] = None, evidence_ref: Optional[str] = None):
        """Завершает спан."""
        self.end_time_unix_nano = time.time_ns()
        self.status = status
        self.status_message = status_message
        if evidence_ref:
            self.evidence_ref = evidence_ref

    def to_dict(self) -> Dict[str, Any]:
        """Преобразует спан в канонический словарь для схемы TraceContext.json."""
        d = {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "task_id": self.task_id,
            "correlation_id": self.correlation_id,
            "operation_id": self.operation_id,
            "worker_id": self.worker_id,
            "name": self.name,
            "span_kind": self.span_kind,
            "status": self.status,
            "status_message": self.status_message,
            "attributes": self.attributes,
            "events": self.events,
            "evidence_ref": self.evidence_ref,
            "start_time_unix_nano": self.start_time_unix_nano,
            "end_time_unix_nano": self.end_time_unix_nano
        }
        return d


class Kat9iTracer:
    """
    Потокобезопасный менеджер сквозной трассировки KAT9I_OS.
    Поддерживает экспорт в JSONL и преобразование в формат OpenTelemetry ResourceSpans.
    """

    def __init__(self, trace_log_path: Optional[Path] = None):
        self.trace_log_path = trace_log_path
        self.lock = threading.Lock()
        self.spans: List[Kat9iSpan] = []

        schema_file = SCHEMAS_V1_DIR / "TraceContext.json"
        if schema_file.exists():
            with open(schema_file, "r", encoding="utf-8") as f:
                self.validator = Draft202012Validator(json.load(f))
        else:
            self.validator = None

    def start_span(
        self,
        name: str,
        span_kind: str,
        task_id: str,
        correlation_id: str,
        parent_span: Optional[Kat9iSpan] = None,
        trace_id: Optional[str] = None,
        worker_id: Optional[str] = None,
        operation_id: Optional[str] = None
    ) -> Kat9iSpan:
        """Создает и активирует новый спан трассы."""
        t_id = parent_span.trace_id if parent_span else (trace_id or generate_trace_id())
        p_id = parent_span.span_id if parent_span else None
        s_id = generate_span_id()

        span = Kat9iSpan(
            trace_id=t_id,
            span_id=s_id,
            task_id=task_id,
            correlation_id=correlation_id,
            name=name,
            span_kind=span_kind,
            parent_span_id=p_id,
            worker_id=worker_id,
            operation_id=operation_id
        )
        return span

    def record_span(self, span: Kat9iSpan):
        """Фиксирует завершённый спан в памяти и опционально экспортирует в файл."""
        span_dict = span.to_dict()
        if self.validator:
            self.validator.validate(span_dict)

        with self.lock:
            self.spans.append(span)
            if self.trace_log_path:
                self.trace_log_path.parent.mkdir(parents=True, exist_ok=True)
                with open(self.trace_log_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(span_dict, ensure_ascii=False) + "\n")

    def export_opentelemetry_json(self, task_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Экспорт собранных спанов в каноническую структуру OpenTelemetry OTLP JSON (ResourceSpans).
        Позволяет бесшовно отправлять трассы в Jaeger, Grafana Tempo, SigNoz или OpenTelemetry Collector.
        """
        with self.lock:
            selected_spans = [s for s in self.spans if (task_id is None or s.task_id == task_id)]

        scope_spans = []
        for s in selected_spans:
            s_dict = s.to_dict()
            otel_span = {
                "traceId": s_dict["trace_id"],
                "spanId": s_dict["span_id"],
                "parentSpanId": s_dict["parent_span_id"] or "",
                "name": s_dict["name"],
                "kind": s_dict["span_kind"],
                "startTimeUnixNano": s_dict["start_time_unix_nano"],
                "endTimeUnixNano": s_dict["end_time_unix_nano"] or s_dict["start_time_unix_nano"],
                "attributes": [
                    {"key": k, "value": {"stringValue": str(v)}}
                    for k, v in s_dict["attributes"].items()
                ],
                "status": {
                    "code": 1 if s_dict["status"] == "OK" else (2 if s_dict["status"] == "ERROR" else 0),
                    "message": s_dict["status_message"] or ""
                }
            }
            scope_spans.append(otel_span)

        return {
            "resourceSpans": [
                {
                    "resource": {
                        "attributes": [
                            {"key": "service.name", "value": {"stringValue": "KAT9I_OS"}},
                            {"key": "service.version", "value": {"stringValue": "0.1.0"}},
                            {"key": "kat9i.task_id", "value": {"stringValue": task_id or "all"}}
                        ]
                    },
                    "scopeSpans": [
                        {
                            "scope": {"name": "kat9i.tracer", "version": "1.0.0"},
                            "spans": scope_spans
                        }
                    ]
                }
            ]
        }
