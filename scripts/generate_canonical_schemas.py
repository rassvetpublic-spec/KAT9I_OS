# -*- coding: utf-8 -*-
"""
Генератор и верификатор канонических JSON Schema для KAT9I_OS (Issue #40, Gate G2).
Создаёт физические схемы в schemas/v1/:
- TaskContract.json
- TaskRuntimeState.json
- TaskResult.json
- Evidence.json
- SecurityDecision.json
- CapabilityGrant.json
- SystemEvent.json
"""

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMAS_V1_DIR = REPO_ROOT / "schemas" / "v1"

def build_schemas():
    SCHEMAS_V1_DIR.mkdir(parents=True, exist_ok=True)

    # 1. TaskContract
    task_contract = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://kat9i.org/schemas/v1/TaskContract.json",
        "title": "TaskContract",
        "description": "Универсальный паспорт и спецификация требований к выполняемой задаче в KAT9I_OS.",
        "type": "object",
        "version": "1.0.0",
        "additionalProperties": False,
        "required": [
            "task_id",
            "source",
            "goal",
            "workspace",
            "domain",
            "scope",
            "output_contract",
            "created_at"
        ],
        "properties": {
            "task_id": {
                "type": "string",
                "pattern": "^[a-zA-Z0-9_-]{3,64}$",
                "description": "Уникальный идентификатор задачи."
            },
            "parent_task_id": {
                "type": ["string", "null"],
                "pattern": "^[a-zA-Z0-9_-]{3,64}$",
                "description": "Идентификатор родительской задачи (null для корневой)."
            },
            "source": {
                "type": "string",
                "description": "Источник поступления задачи (user, system, github_issue, workflow)."
            },
            "goal": {
                "type": "string",
                "minLength": 1,
                "description": "Текстовое описание цели задачи."
            },
            "workspace": {
                "type": "string",
                "description": "Рабочее пространство задачи (путь к репозиторию или проекту)."
            },
            "domain": {
                "type": "string",
                "description": "Доменная область задачи (software_engineering, architecture, qa, security)."
            },
            "scope": {
                "type": "object",
                "additionalProperties": False,
                "required": ["allowed_paths"],
                "properties": {
                    "repository": {
                        "type": "string",
                        "description": "Целевой репозиторий."
                    },
                    "allowed_paths": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Разрешённые пути к файлам и каталогам."
                    },
                    "denied_paths": {
                        "type": "array",
                        "items": {"type": "string"},
                        "default": [],
                        "description": "Явно запрещённые пути."
                    },
                    "allowed_operations": {
                        "type": "array",
                        "items": {"type": "string"},
                        "default": ["read", "write"],
                        "description": "Разрешённые операции (read, write, execute, network)."
                    },
                    "network_allowed": {
                        "type": "boolean",
                        "default": False,
                        "description": "Флаг разрешения сетевого доступа."
                    }
                }
            },
            "context_refs": {
                "type": "array",
                "items": {"type": "string"},
                "default": [],
                "description": "Ссылки на источники контекста (документы, артефакты, память)."
            },
            "rules_ref": {
                "type": "string",
                "default": "canonical",
                "description": "Ссылка на действующий набор правил (SSoT)."
            },
            "required_capabilities": {
                "type": "array",
                "items": {"type": "string"},
                "default": [],
                "description": "Требуемые возможности исполнителя (filesystem, git, rust_build, etc.)."
            },
            "output_contract": {
                "type": "object",
                "additionalProperties": False,
                "required": ["expected_artifacts"],
                "properties": {
                    "expected_artifacts": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Ожидаемые артефакты выполнения."
                    },
                    "quality_gate_required": {
                        "type": "boolean",
                        "default": True,
                        "description": "Требуется ли прохождение Quality Gate."
                    },
                    "independent_qa_required": {
                        "type": "boolean",
                        "default": True,
                        "description": "Требуется ли независимый QA."
                    }
                }
            },
            "result_sink": {
                "type": "string",
                "default": "local_workspace",
                "description": "Место сохранения итоговых результатов."
            },
            "created_at": {
                "type": "string",
                "format": "date-time",
                "description": "Временная метка создания контракта в ISO 8601."
            }
        }
    }

    # 2. TaskRuntimeState
    task_runtime_state = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://kat9i.org/schemas/v1/TaskRuntimeState.json",
        "title": "TaskRuntimeState",
        "description": "Текущее состояние выполнения задачи в среде исполнения KAT9I_OS.",
        "type": "object",
        "version": "1.0.0",
        "additionalProperties": False,
        "required": [
            "task_id",
            "status",
            "worker_id",
            "progress_percent",
            "updated_at"
        ],
        "properties": {
            "task_id": {
                "type": "string",
                "pattern": "^[a-zA-Z0-9_-]{3,64}$",
                "description": "Идентификатор отслеживаемой задачи."
            },
            "status": {
                "type": "string",
                "enum": [
                    "QUEUED",
                    "ACQUIRING_RESOURCES",
                    "ACTIVE",
                    "PAUSED",
                    "BLOCKED_ON_INPUT",
                    "AWAITING_QA",
                    "COMPLETED",
                    "FAILED",
                    "CANCELLED"
                ],
                "description": "Текущий статус жизненного цикла задачи."
            },
            "worker_id": {
                "type": "string",
                "description": "Идентификатор назначенного исполнителя (Worker)."
            },
            "progress_percent": {
                "type": "integer",
                "minimum": 0,
                "maximum": 100,
                "description": "Процент завершения выполнения (0..100)."
            },
            "current_step": {
                "type": "string",
                "default": "",
                "description": "Краткое описание выполняемого шага."
            },
            "checkpoint_id": {
                "type": ["string", "null"],
                "description": "Идентификатор последнего созданного снимка состояния (контрольной точки)."
            },
            "error_message": {
                "type": ["string", "null"],
                "description": "Сообщение об ошибке в случае сбоя или блокировки."
            },
            "updated_at": {
                "type": "string",
                "format": "date-time",
                "description": "Временная метка последнего обновления состояния в ISO 8601."
            }
        }
    }

    # 3. TaskResult
    task_result = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://kat9i.org/schemas/v1/TaskResult.json",
        "title": "TaskResult",
        "description": "Итоговый результат выполнения задачи в KAT9I_OS.",
        "type": "object",
        "version": "1.0.0",
        "additionalProperties": False,
        "required": [
            "task_id",
            "verdict",
            "artifacts",
            "evidence_ref",
            "completed_at",
            "duration_ms"
        ],
        "properties": {
            "task_id": {
                "type": "string",
                "pattern": "^[a-zA-Z0-9_-]{3,64}$",
                "description": "Идентификатор завершённой задачи."
            },
            "verdict": {
                "type": "string",
                "enum": ["SUCCESS", "FAILURE", "ABORTED", "REJECTED_BY_QA"],
                "description": "Итоговый вердикт выполнения задачи."
            },
            "summary": {
                "type": "string",
                "default": "",
                "description": "Текстовое резюме проделанной работы."
            },
            "artifacts": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["path", "hash_sha256", "size_bytes"],
                    "properties": {
                        "path": {"type": "string"},
                        "hash_sha256": {"type": "string", "pattern": "^[a-fA-F0-9]{64}$"},
                        "size_bytes": {"type": "integer", "minimum": 0},
                        "description": {"type": "string", "default": ""}
                    }
                },
                "description": "Список созданных или изменённых артефактов с хэш-суммами."
            },
            "evidence_ref": {
                "type": "string",
                "description": "Ссылка на запись аудита доказательств (Evidence)."
            },
            "completed_at": {
                "type": "string",
                "format": "date-time",
                "description": "Временная метка завершения в ISO 8601."
            },
            "duration_ms": {
                "type": "integer",
                "minimum": 0,
                "description": "Длительность исполнения в миллисекундах."
            }
        }
    }

    # 4. Evidence
    evidence = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://kat9i.org/schemas/v1/Evidence.json",
        "title": "Evidence",
        "description": "Запись аудита и проверяемые доказательства корректности работы KAT9I_OS.",
        "type": "object",
        "version": "1.0.0",
        "additionalProperties": False,
        "required": [
            "evidence_id",
            "task_id",
            "source_revision",
            "test_results",
            "qa_verdict",
            "qa_worker",
            "created_at"
        ],
        "properties": {
            "evidence_id": {
                "type": "string",
                "pattern": "^ev-[a-zA-Z0-9_-]{8,64}$",
                "description": "Уникальный идентификатор доказательства."
            },
            "task_id": {
                "type": "string",
                "pattern": "^[a-zA-Z0-9_-]{3,64}$",
                "description": "Идентификатор связанной задачи."
            },
            "source_revision": {
                "type": "string",
                "pattern": "^[a-fA-F0-9]{7,40}$",
                "description": "Хэш коммита git, на котором проводилась верификация."
            },
            "test_results": {
                "type": "object",
                "additionalProperties": False,
                "required": ["total", "passed", "failed", "exit_code"],
                "properties": {
                    "total": {"type": "integer", "minimum": 0},
                    "passed": {"type": "integer", "minimum": 0},
                    "failed": {"type": "integer", "minimum": 0},
                    "exit_code": {"type": "integer"},
                    "summary": {"type": "string", "default": ""}
                }
            },
            "qa_verdict": {
                "type": "string",
                "enum": ["PASS", "FAIL", "NEEDS_REVISION"],
                "description": "Вердикт независимой проверки качества."
            },
            "qa_worker": {
                "type": "string",
                "description": "Идентификатор независимого исполнителя QA (отличного от автора реализации)."
            },
            "notes": {
                "type": "string",
                "default": "",
                "description": "Заметки и замечания QA."
            },
            "created_at": {
                "type": "string",
                "format": "date-time",
                "description": "Временная метка фиксации доказательства в ISO 8601."
            }
        }
    }

    # 5. SecurityDecision
    security_decision = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://kat9i.org/schemas/v1/SecurityDecision.json",
        "title": "SecurityDecision",
        "description": "Решение модуля безопасности (Scope Guard / Policy Engine) по запросу действия.",
        "type": "object",
        "version": "1.0.0",
        "additionalProperties": False,
        "required": [
            "decision_id",
            "task_id",
            "worker_id",
            "action",
            "verdict",
            "decided_at"
        ],
        "properties": {
            "decision_id": {
                "type": "string",
                "pattern": "^sec-[a-zA-Z0-9_-]{8,64}$",
                "description": "Уникальный идентификатор решения безопасности."
            },
            "task_id": {
                "type": "string",
                "pattern": "^[a-zA-Z0-9_-]{3,64}$",
                "description": "Идентификатор задачи."
            },
            "worker_id": {
                "type": "string",
                "description": "Исполнитель, запросивший действие."
            },
            "action": {
                "type": "object",
                "additionalProperties": False,
                "required": ["operation", "target"],
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["READ_FILE", "WRITE_FILE", "EXECUTE_COMMAND", "NETWORK_REQUEST", "ACCESS_SECRET"]
                    },
                    "target": {"type": "string", "description": "Путь к файлу, команда или URL."}
                }
            },
            "verdict": {
                "type": "string",
                "enum": ["ALLOW", "DENY", "REQUIRE_HUMAN_CONFIRMATION"],
                "description": "Вердикт безопасности: разрешить, запретить или запросить одобрение человека."
            },
            "reason": {
                "type": "string",
                "default": "",
                "description": "Причина принятия решения или пункт нарушенной политики."
            },
            "decided_at": {
                "type": "string",
                "format": "date-time",
                "description": "Временная метка принятия решения в ISO 8601."
            }
        }
    }

    # 6. CapabilityGrant
    capability_grant = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://kat9i.org/schemas/v1/CapabilityGrant.json",
        "title": "CapabilityGrant",
        "description": "Выданный мандат прав и возможностей для Worker или задачи.",
        "type": "object",
        "version": "1.0.0",
        "additionalProperties": False,
        "required": [
            "grant_id",
            "grantee_id",
            "capabilities",
            "expires_at",
            "issued_at"
        ],
        "properties": {
            "grant_id": {
                "type": "string",
                "pattern": "^cap-[a-zA-Z0-9_-]{8,64}$",
                "description": "Уникальный идентификатор мандата прав."
            },
            "grantee_id": {
                "type": "string",
                "description": "Идентификатор получателя прав (Worker ID или Task ID)."
            },
            "capabilities": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": [
                        "FS_READ",
                        "FS_WRITE_SCOPED",
                        "FS_WRITE_WORKSPACE",
                        "CMD_EXECUTE_SAFE",
                        "CMD_EXECUTE_BUILD",
                        "NETWORK_GITHUB_API",
                        "SECRET_READ_SCOPED"
                    ]
                },
                "minItems": 1,
                "description": "Перечень предоставленных прав."
            },
            "isolation_level": {
                "type": "string",
                "enum": ["PROCESS_ISOLATED", "JOB_OBJECT", "CONTAINER", "IN_PROCESS"],
                "default": "PROCESS_ISOLATED",
                "description": "Требуемый уровень изоляции исполнения."
            },
            "expires_at": {
                "type": "string",
                "format": "date-time",
                "description": "Временная метка истечения срока действия мандата в ISO 8601."
            },
            "issued_at": {
                "type": "string",
                "format": "date-time",
                "description": "Временная метка выдачи мандата в ISO 8601."
            }
        }
    }

    # 7. SystemEvent
    system_event = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://kat9i.org/schemas/v1/SystemEvent.json",
        "title": "SystemEvent",
        "description": "Универсальный конверт события Event Journal для аудита, стриминга и Replay Recovery.",
        "type": "object",
        "version": "1.0.0",
        "additionalProperties": False,
        "required": [
            "event_id",
            "event_type",
            "source_module",
            "payload",
            "timestamp"
        ],
        "properties": {
            "event_id": {
                "type": "string",
                "pattern": "^evt-[a-zA-Z0-9_-]{8,64}$",
                "description": "Уникальный монотонный идентификатор события."
            },
            "event_type": {
                "type": "string",
                "enum": [
                    "TASK_CREATED",
                    "TASK_STATUS_CHANGED",
                    "TASK_COMPLETED",
                    "SECURITY_VIOLATION_DETECTED",
                    "CAPABILITY_GRANTED",
                    "CHECKPOINT_CREATED",
                    "WORKER_REGISTERED",
                    "WORKER_HEARTBEAT"
                ],
                "description": "Тип системного события."
            },
            "source_module": {
                "type": "string",
                "description": "Идентификатор модуля-источника события (Core, Security, Worker, UI)."
            },
            "task_id": {
                "type": ["string", "null"],
                "description": "Связанный идентификатор задачи, если применимо."
            },
            "payload": {
                "type": "object",
                "description": "Полезная нагрузка события, соответствующая контракту типа события."
            },
            "timestamp": {
                "type": "string",
                "format": "date-time",
                "description": "Временная метка генерации события в ISO 8601."
            }
        }
    }

    schemas = {
        "TaskContract.json": task_contract,
        "TaskRuntimeState.json": task_runtime_state,
        "TaskResult.json": task_result,
        "Evidence.json": evidence,
        "SecurityDecision.json": security_decision,
        "CapabilityGrant.json": capability_grant,
        "SystemEvent.json": system_event
    }

    for fname, schema_data in schemas.items():
        out_file = SCHEMAS_V1_DIR / fname
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(schema_data, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print(f"Generated: {out_file.relative_to(REPO_ROOT)}")

    # README
    readme_path = REPO_ROOT / "schemas" / "README.md"
    readme_content = """# Канонические машинные контракты KAT9I_OS

## 1. Назначение каталога

Данный каталог является **единым физическим источником истины (SSoT)** для машинных контрактов между всеми технологическими слоями KAT9I_OS:
- **Rust Core Runtime** (ядро системы, планировщик, безопасность, журнал);
- **TypeScript Desktop/UI** (настольная оболочка Electron, интерфейс коворкера);
- **Python AI/ML Workers** (специализированные исполнители задач и инференса).

Все три слоя валидируют свои входные и выходные сообщения против схем из этого каталога либо генерируют строгие типы на их основе.

## 2. Формат схем

В качестве канонического формата принят **JSON Schema (Draft 2020-12)** (ADR-034, закрытие открытых вопросов `OQ-003` и `OQ-006` ворот G2):
- Обеспечивает нативную интеграцию со всеми тремя языками стека без необходимости во внешних бинарных компиляторах;
- Поддерживает строгую проверку ограничений данных (`pattern`, `enum`, `minimum`, `maximum`, `required`);
- Позволяет включать строгий инвариант безопасности `additionalProperties: false`, запрещающий передачу скрытых или непроверенных параметров;
- Человекочитаем и инспектируем в журналах, GitHub Issues и инструментах отладки.

## 3. Структура каталога

```text
schemas/
├── README.md             # Настоящий манифест и правила
└── v1/                   # Канонические схемы версии 1
    ├── TaskContract.json       # Паспорт и требования к задаче
    ├── TaskRuntimeState.json   # Текущее состояние исполнения задачи
    ├── TaskResult.json         # Итоговый результат выполнения
    ├── Evidence.json           # Запись аудита и доказательства корректности
    ├── SecurityDecision.json   # Вердикт проверки безопасности Scope Guard
    ├── CapabilityGrant.json    # Выданный мандат прав и возможностей
    └── SystemEvent.json        # Универсальный конверт системных событий
```

## 4. Политика версионирования и эволюции схем

Схемы версионируются по стандарту **Semantic Versioning (SemVer 2.0.0)**:
- Каталог `schemas/v{MAJOR}/` группирует схемы по мажорной версии;
- Каждая схема содержит метаданные:
  * `$schema`: `"https://json-schema.org/draft/2020-12/schema"`
  * `$id`: URI схемы (например, `"https://kat9i.org/schemas/v1/TaskContract.json"`)
  * `version`: версия контракта в формате `MAJOR.MINOR.PATCH` (например, `"1.0.0"`).

### Правила совместимости:
1. **Обратно совместимые изменения (MINOR / PATCH):**
   - Добавление нового необязательного поля с документированным значением по умолчанию;
   - Добавление нового типа событий или расширение допустимых вариантов в `enum` (с сохранением семантики существующих).
2. **Ломающие изменения (MAJOR):**
   - Удаление или переименование полей;
   - Добавление обязательного поля (`required`);
   - Изменение типа данных или формата;
   - Размещение в новом каталоге: `schemas/v2/`.
3. **Принцип Fail-Closed при неизвестной версии:**
   - Если модуль получает сообщение с неизвестной `MAJOR` версией, операция немедленно отклоняется с ошибкой `INCOMPATIBLE_SCHEMA_VERSION`. Никакая интерпретация «по догадке» не допускается.
"""
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(readme_content)
    print(f"Generated: {readme_path.relative_to(REPO_ROOT)}")

if __name__ == "__main__":
    build_schemas()
