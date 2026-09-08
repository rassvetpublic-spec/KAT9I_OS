# 33. Внешний сравнительный бенчмарк KAT9I_OS против агентных и workflow-систем

## 33.1. Назначение и контекст (Purpose and Context)

Этот раздел фиксирует канонический сравнительный анализ архитектуры KAT9I_OS и ведущих внешних платформ для агентной разработки и надёжного исполнения рабочих процессов (Durable Execution).

В соответствии с планом развития (Roadmap, раздел 31.69), сравнительный анализ проводится **до окончательной фиксации Architecture Baseline**, чтобы:
1. Выявить проверенные архитектурные решения конкретных проблем KAT9I_OS в индустрии.
2. Не допустить слепого копирования маркетинговых заявлений или избыточных структур.
3. Сформировать воспроизводимый benchmark (набор стандартных сценариев испытаний), а не статическую разовую таблицу.
4. Зафиксировать прозрачные решения по архитектурным разрывам (Gap Decisions): что система перенимает, что адаптирует под свои инварианты, от чего осознанно отказывается и что откладывает.

> **Главный принцип бенчмарка:**
> Сравниваются не субъективные заявления разработчиков, а строго верифицируемые механизмы платформы. Каждая возможность фиксируется в одном из трёх состояний:
> - **`IMPLEMENTED`** — подтверждено кодом, тестами и воспроизводимым сценарием в публичной кодовой базе платформы;
> - **`SPECIFIED`** — строго формализовано в канонической архитектуре KAT9I_OS (`docs/spec/` и `docs/architecture/`), но ожидает стадии кодовой реализации (Gate G2/G3);
> - **`ABSENT`** — возможность отсутствует в архитектуре или коде системы либо не является её проектной целью.

---

## 33.2. Системы базового сравнения и первичные источники (Benchmarked Systems)

В базовый набор включены 7 ключевых платформ индустрии по состоянию на сентябрь 2026 года (с датами верификации):

1. **Microsoft Agent Framework (MAF)**
   - *Тип:* Корпоративный SDK оркестрации агентов (эволюция Semantic Kernel и AutoGen / Azure AI Agent Service).
   - *Первичные источники:* Репозитории `microsoft/semantic-kernel`, `microsoft/autogen`, официальная документация Microsoft Learn по Azure AI Agent Service (верифицировано: август 2026 г.).
   - *Фокус:* Enterprise-интеграции, Process Framework, типизированные плагины, multi-agent conversations.

2. **LangGraph (LangChain)**
   - *Тип:* Графовая среда исполнения агентов с контролем циклов и сохранением состояния (Stateful Multi-Agent Orchestration).
   - *Первичные источники:* Документация `langchain-ai/langgraph`, спецификация StateGraph, Checkpointer API (MemorySaver, PostgresSaver) (верифицировано: август 2026 г.).
   - *Фокус:* Графы состояний, точки прерывания (breakpoints), Time-travel debugging, Human-in-the-loop.

3. **OpenAI Agents SDK**
   - *Тип:* Легковесный SDK оркестрации и передачи управления между агентами (эволюция OpenAI Swarm / Assistants API v2).
   - *Первичные источники:* Официальные репозитории OpenAI, спецификация Assistants API / Threads / Runs (верифицировано: июль 2026 г.).
   - *Фокус:* Handoffs (передача управления), встроенный вызов функций (Function Calling), интеграция с Hosted Container Tools.

4. **CrewAI**
   - *Тип:* Фреймворк ролевой совместной работы агентов и детерминированных процессов (Crews & Flows).
   - *Первичные источники:* Репозиторий `crewAIInc/crewAI`, спецификация CrewAI Flows, Task pipelines (верифицировано: август 2026 г.).
   - *Фокус:* Ролевая модель (Role-playing agents), структурированные пайплайны задач, делегирование, коллаборация.

5. **Dify**
   - *Тип:* Открытая платформа визуальной сборки AI-приложений, агентов и LLM-workflow.
   - *Первичные источники:* Репозиторий `langgenius/dify`, документация DSL Workflow, модули Node Sandbox (верифицировано: август 2026 г.).
   - *Фокус:* Визуальный конструктор DAG, RAG-конвейеры, DSL импорт/экспорт, multi-tenant управление.

6. **Letta (ранее MemGPT)**
   - *Тип:* Платформа агентов с сохраняемым состоянием и многоуровневой иерархической памятью (Stateful LLM Services).
   - *Первичные источники:* Репозиторий `letta-ai/letta` (`cpacker/MemGPT`), спецификация Memory Blocks (Core Memory, Archival, Recall) (верифицировано: август 2026 г.).
   - *Фокус:* Непрерывная память (OS-like virtual memory for LLMs), самоуправление контекстом, сохранение личности агента.

7. **Temporal**
   - *Тип:* Промышленная платформа надёжного длительного выполнения рабочих процессов (Durable Execution Platform).
   - *Первичные источники:* Документация `temporalio/temporal`, спецификации Temporal Workflows/Activities, Event History, Determinism constraints (верифицировано: август 2026 г.).
   - *Фокус:* Безусловная надёжность, реплей событий (Replay-based recovery), саги, распределённые таймеры, идемпотентность.

---

## 33.3. Сравнительная матрица по 20 ключевым осям (Comparative Matrix)

| № | Ось сравнения (Evaluation Axis) | Microsoft Agent Framework | LangGraph | OpenAI Agents SDK | CrewAI | Dify | Letta | Temporal | KAT9I_OS |
|---|---|---|---|---|---|---|---|---|---|
| 1 | **Task/workflow state** (Состояние задачи/процесса) | IMPLEMENTED | IMPLEMENTED | IMPLEMENTED | IMPLEMENTED | IMPLEMENTED | IMPLEMENTED | IMPLEMENTED | **SPECIFIED** (TaskContract + TaskRuntimeState) |
| 2 | **Checkpoint/Resume** (Контрольные точки и продолжение) | IMPLEMENTED | IMPLEMENTED | ABSENT | IMPLEMENTED | ABSENT | IMPLEMENTED | IMPLEMENTED | **SPECIFIED** (Event Journal + Checkpoints) |
| 3 | **Recovery** (Восстановление после сбоев) | ABSENT | IMPLEMENTED | ABSENT | ABSENT | ABSENT | ABSENT | IMPLEMENTED | **SPECIFIED** (Event Replay + Lease Recovery) |
| 4 | **Human-in-the-loop** (Участие человека) | IMPLEMENTED | IMPLEMENTED | IMPLEMENTED | IMPLEMENTED | IMPLEMENTED | IMPLEMENTED | IMPLEMENTED | **SPECIFIED** (Human Approval + ADR-008 Deny wins) |
| 5 | **Multi-agent orchestration** (Оркестрация групп агентов) | IMPLEMENTED | IMPLEMENTED | IMPLEMENTED | IMPLEMENTED | ABSENT | ABSENT | ABSENT | **SPECIFIED** (Coworker Pool + Teamwork locks) |
| 6 | **Typed contracts** (Типизированные контракты) | IMPLEMENTED | IMPLEMENTED | IMPLEMENTED | IMPLEMENTED | IMPLEMENTED | IMPLEMENTED | IMPLEMENTED | **SPECIFIED** (Rust/TS Schemas + TaskContract) |
| 7 | **Sandbox** (Изолированная песочница) | ABSENT | ABSENT | IMPLEMENTED | ABSENT | IMPLEMENTED | ABSENT | ABSENT | **SPECIFIED** (Scope Guard + Windows Job Objects) |
| 8 | **Tool/MCP integration** (Поддержка MCP и инструментов) | IMPLEMENTED | IMPLEMENTED | ABSENT | IMPLEMENTED | IMPLEMENTED | IMPLEMENTED | ABSENT | **SPECIFIED** (MCP Client/Server + Progressive) |
| 9 | **Security/least privilege** (Безопасность и минимальные права) | IMPLEMENTED | ABSENT | ABSENT | ABSENT | IMPLEMENTED | ABSENT | ABSENT | **SPECIFIED** (WorkerGrant + Temporary Token) |
| 10 | **Prompt/Tool injection protection** (Защита от injection) | IMPLEMENTED | ABSENT | ABSENT | ABSENT | ABSENT | ABSENT | ABSENT | **SPECIFIED** (CONTROL/DATA split + Context Guard) |
| 11 | **Memory/Knowledge** (Память и база знаний) | IMPLEMENTED | IMPLEMENTED | ABSENT | IMPLEMENTED | IMPLEMENTED | IMPLEMENTED | ABSENT | **SPECIFIED** (Obsidian Vault + KnowledgeRef) |
| 12 | **Observability/Tracing** (Наблюдаемость и трассировка) | IMPLEMENTED | IMPLEMENTED | IMPLEMENTED | IMPLEMENTED | IMPLEMENTED | IMPLEMENTED | IMPLEMENTED | **SPECIFIED** (OpenTelemetry + Correlation ID) |
| 13 | **QA/Evals** (Оценка качества и независимый QA) | IMPLEMENTED | IMPLEMENTED | IMPLEMENTED | IMPLEMENTED | IMPLEMENTED | IMPLEMENTED | ABSENT | **SPECIFIED** (ADR-009 Independent QA) |
| 14 | **Evidence/Audit** (Доказательства и аудит выполнения) | ABSENT | ABSENT | ABSENT | ABSENT | ABSENT | ABSENT | IMPLEMENTED | **SPECIFIED** (ADR-004 Evidence-first + EvidenceRef) |
| 15 | **Idempotency** (Идемпотентность и исключение дублей) | ABSENT | ABSENT | ABSENT | ABSENT | ABSENT | ABSENT | IMPLEMENTED | **SPECIFIED** (Idempotency Key + ResultRef) |
| 16 | **Lease/Fencing** (Временные права и защита от дублирования) | ABSENT | ABSENT | ABSENT | ABSENT | ABSENT | ABSENT | IMPLEMENTED | **SPECIFIED** (Lease + Generation + Fencing) |
| 17 | **Local-first/Offline-first** (Приоритет локального исполнения) | ABSENT | IMPLEMENTED | ABSENT | IMPLEMENTED | ABSENT | IMPLEMENTED | ABSENT | **SPECIFIED** (ADR-002 Local-first + Ollama/Rust) |
| 18 | **Cost/forecasting** (Прогноз ресурсов и учёт стоимости) | IMPLEMENTED | ABSENT | ABSENT | ABSENT | IMPLEMENTED | ABSENT | ABSENT | **SPECIFIED** (Cost per Task + Pre-flight Estimate) |
| 19 | **Visual workflow/UI** (Визуальный интерфейс процессов) | ABSENT | IMPLEMENTED | ABSENT | ABSENT | IMPLEMENTED | ABSENT | IMPLEMENTED | **SPECIFIED** (Electron UI + TaskGraph) |
| 20 | **Developer experience** (Удобство разработки и локальной отладки) | IMPLEMENTED | IMPLEMENTED | IMPLEMENTED | IMPLEMENTED | IMPLEMENTED | IMPLEMENTED | IMPLEMENTED | **SPECIFIED** (GitHub-driven + Dogfood CLI) |

---

## 33.4. Семь практических сценариев бенчмарка (Benchmark Scenarios)

Для каждого сценария зафиксированы: условия проверки, поведение внешних систем и верифицируемый эталон поведения KAT9I_OS.

### Сценарий 1: Пауза на подтверждение человека → Перезапуск системы → Продолжение выполнения (Human-in-the-Loop Persistence)
- **Цель:** Проверить сохранение полного состояния процесса при длительной паузе и аварийном перезапуске хоста.
- **Внешние платформы:**
  - *LangGraph:* Поддерживает через `interrupt()` и Postgres/Sqlite Checkpointer. После перезапуска граф возобновляется с контрольной точки.
  - *Temporal:* Идеальная поддержка через Signals и History Replay. Процесс может ждать недели и перезапускаться без потерь.
  - *OpenAI SDK / CrewAI:* Теряют состояние в памяти при перезапуске процесса исполнителя (требуют внешней обвязки).
- **Эталон KAT9I_OS:**
  - Задача переводится в статус `WAITING_FOR_HUMAN`.
  - Состояние фиксируется в `TaskRuntimeState` и SQLite Event Journal с `CheckpointRef`.
  - Освобождается Lease исполнителя, процесс может быть полностью завершён.
  - При возобновлении (`HumanApprovalToken`) другой Worker поднимает задачу из Checkpoint без повторного прогона пройденных стадий.

### Сценарий 2: Падение исполнителя посередине задачи (Worker Crash & Lease Expiration)
- **Цель:** Исключить зависание задачи при внезапном сбое процесса (OOM, SIGKILL, обрыв связи).
- **Внешние платформы:**
  - *Temporal:* Обнаруживает через Activity Heartbeat Timeout и переназначает задачу другому воркеру.
  - *LangGraph / CrewAI / Dify:* Не имеют встроенного механизма Lease/Heartbeat для распределённых воркеров; задача навсегда зависает в статусе "Running" без кастомного супервизора.
- **Эталон KAT9I_OS:**
  - На задачу выдаётся `WorkerLease` с TTL (например, 60 секунд) и обязательным `Heartbeat`.
  - При отсутствии Heartbeat супервизор Core переводит задачу в статус `ABANDONED`.
  - Производится откат незафиксированных временных файлов в изоляции (`Workspace Isolation Cleanup`).
  - Задача безопасно переназначается новому Worker с инкрементом `lease_generation`.

### Сценарий 3: Повтор внешней изменяющей операции без создания дубля (Idempotency & ResultRef)
- **Цель:** Предотвратить дублирование внешних действий (создание повторного PR, коммита, комментария, списания баланса).
- **Внешние платформы:**
  - *Temporal:* Гарантирует идемпотентность через Activity Idempotency Keys и детерминированную историю.
  - *Агентные SDK (LangGraph, CrewAI, AutoGen):* Повторный запуск шага выполняет обращение к инструменту повторно, создавая дублирующий вызов API.
- **Эталон KAT9I_OS:**
  - Каждая изменяющая операция формирует детерминированный `IdempotencyKey(task_id, stage_id, operation_hash)`.
  - Перед вызовом внешнего инструмента модуль Execution проверяет наличие зафиксированного `ResultRef` в реестре результатов.
  - При наличии готового результата возвращается существующий `ResultRef` без повторного вызова инструмента.

### Сценарий 4: Смена версии правила / системного контракта во время паузы задачи (Schema & Policy Drift)
- **Цель:** Предотвратить исполнение задачи по устаревшим правилам или разрушение структур при обновлении софта во время выполнения длительного процесса.
- **Внешние платформы:**
  - *Temporal:* Требует явного использования Workflow Versioning API (`GetVersion()`), иначе недетерминированное изменение кода ломает Replay.
  - *LangGraph / Letta:* Изменение схемы стейта во время нахождения процесса в паузе приводит к ошибке десериализации (Schema mismatch).
- **Эталон KAT9I_OS:**
  - Контракт задачи содержит неизменяемый `RulesRef` и `SystemContractVersion`, зафиксированные в момент старта задачи (`TaskContract.immutable`).
  - При возобновлении задачи проверяется `PolicyDriftDetector`:
    - Если изменились критические правила безопасности (`deny wins`) — задача принудительно запрашивает повторную валидацию (`REVALIDATE_RULES`).
    - Если обновились внутренние структуры, применяется адаптер миграции контрактов.

### Сценарий 5: Конкуренция двух исполнителей за одну изменяющую операцию (Fencing Token & Split-Brain Prevention)
- **Цель:** Исключить запись устаревшим («зомби») воркером, который временно завис, но очнулся после того, как задача была переназначена.
- **Внешние платформы:**
  - *Temporal:* Сервер отклоняет завершение Activity от устаревшего воркера по номеру TaskToken.
  - *Большинство агентных библиотек:* Отсутствует защита от split-brain; оба агента выполнят запись и перезапишут данные друг друга.
- **Эталон KAT9I_OS:**
  - Каждая выдача права сопровождается монотонно растущим номером поколения (`Lease Generation / Fencing Token`).
  - Результирующий приёмник (ResultSink / Git Workspace / Database) принимает изменения только с `token == current_generation`.
  - Попытка записи от старого исполнителя отклоняется ошибкой `FENCING_TOKEN_STALE`.

### Сценарий 6: Выполнение детерминированной задачи без языковой модели (Executable-first, 0-Token Cost)
- **Цель:** Проверить способность системы решать алгоритмически формализованные подзадачи без паразитного расхода токенов и задержек LLM.
- **Внешние платформы:**
  - *Dify / Temporal:* Отлично исполняют детерминированные ноды и шаги кода.
  - *CrewAI / AutoGen:* Часто требуют прогона системных промптов и «размышлений» LLM даже для тривиальной сортировки или проверки файла.
- **Эталон KAT9I_OS:**
  - Архитектурный инвариант **ADR-001 (Executable-first)**: приоритет `CODE → HYBRID → MODEL`.
  - Модуль Inference направляет детерминированные операции в локальный исполнитель (`LocalExecutor / Rust Tool`), стоимость шага: 0 токенов, latency < 10 мс.

### Сценарий 7: Сквозная трассировка: Модель → Инструмент → Результат → Независимый QA (Traceability & Evidence Chain)
- **Цель:** Обеспечить неразрывную цепочку аудита от намерения модели до приёмки независимым инспектором.
- **Внешние платформы:**
  - *LangGraph + LangSmith:* Обеспечивает детальный граф трейсов (Input → Tool → Output), но концепция «независимого QA» отсутствует как архитектурная сущность.
  - *Temporal:* Хранит историю событий, но не привязывает семантическое качество к процессу приёмки.
- **Эталон KAT9I_OS:**
  - Задаче присваивается глобальный `CorrelationId`.
  - Все шаги фиксируют входные `ContextRef`, вызовы инструментов с аргументами, хешированные `EvidenceRef`.
  - Результат передаётся отдельному `QA Worker` (инвариант **ADR-009**), который валидирует результат по чек-листу и формирует подписанный протокол проверки `QAPassRef`.

---

## 33.5. Анализ разрывов и архитектурные решения (Gap Decisions)

На основе бенчмарка для выявленных различий зафиксированы следующие обязательные решения:

### 1. Что KAT9I_OS берёт напрямую (Adopt)
- **Модель контрольных точек и графов (LangGraph):** Разделение графа выполнения на явные ноды с фиксацией состояния в контрольных точках (Checkpoints) берётся за основу модуля Orchestration.
- **Модель Durable Execution и Heartbeat-супервизии (Temporal):** Использование аренды (Lease), монотонных токенов защиты от сбоев (Fencing tokens) и отслеживания сигналов жизни (Heartbeat) переносится в модули `Coworker` и `Execution`.
- **Иерархическая организация памяти (Letta):** Разделение памяти на быструю рабочую память (Core Context), архивную базу знаний (Archival Knowledge / Obsidian) и хронологию событий (Event Journal).

### 2. Что KAT9I_OS адаптирует (Adapt)
- **Протокол Handoffs (OpenAI Agents SDK / AutoGen):** Вместо неконтролируемой передачи контекста между агентами вводится типизированный контракт делегирования `SubtaskContract` с ограничением прав `WorkerGrant`.
- **Конструктор рабочих процессов (Dify):** Визуализация процессов адаптируется для десктопной оболочки Electron исключительно как инструмент наблюдения и отладки (`TaskGraph Viewer`), но не как конкурирующий источник бизнес-логики.
- **Оценки качества (LangSmith / Evals):** Адаптируются в форме обязательного независимого тестирования (**ADR-009 Independent QA**), где тестирующий агент изолирован от контекста рассуждений исполнителя.

### 3. От чего KAT9I_OS осознанно отказывается (Reject)
- **Прямое исполнение системных команд из промптов агентов (Unsandboxed Tool Execution):** Отказ от прямого неконтролируемого доступа LLM к shell/fs. Любое воздействие строго фильтруется через `Scope Guard` и изоляцию рабочих каталогов.
- **Смешение инструкций и пользовательских данных (Unified Prompt Context):** Отказ от общего неструктурированного окна контекста. Архитектура строго разделяет потоки `CONTROL` (системные правила, инварианты) и `DATA` (пользовательский ввод, внешние файлы) для защиты от Prompt Injection.
- **Хранение секретов в переменных окружения процессов агентов:** Отказ от передачи API-ключей в явном виде рабочим процессам. Доступ только по `SecretRef` через защищённый Vault Windows Credential Manager.

### 4. Что откладывается за пределы MVP v0.1 (Defer)
- **Распределённый консенсус (Raft/Paxos) для кластера нод:** Для версии v0.1 применяется Local-first модель с одним Primary координатором и пулом локальных/удалённых воркеров.
- **Динамический маркетплейс сторонних навыков:** Загрузка сторонних непроверенных плагинов отложена до реализации доказанной криптографической верификации манифестов и полного аудита безопасности.

---

## 33.6. Взаимосвязь с канонической архитектурой (SSoT Integrity)

Настоящий сравнительный бенчмарк не заменяет и не дублирует канонические архитектурные разделы:
- Спецификация контрактов и жизненного цикла зафиксирована в [03_TASK_CONTRACT.md](03_TASK_CONTRACT.md) и [20_TASK_LIFECYCLE_AND_ORCHESTRATION.md](20_TASK_LIFECYCLE_AND_ORCHESTRATION.md).
- Изоляция и исполнение зафиксированы в [12_EXECUTION.md](12_EXECUTION.md) и [14_SECURITY.md](14_SECURITY.md).
- Независимый контроль качества зафиксирован в [23_TESTING_QA_AND_READINESS.md](../spec/23_TESTING_QA_AND_READINESS.md).
- Реестр модулей и зон ответственности зафиксирован в [27_MODULE_REGISTRY_AND_RESPONSIBILITY_MAP.md](27_MODULE_REGISTRY_AND_RESPONSIBILITY_MAP.md).
- Фундаментальные архитектурные решения зафиксированы в [32_ARCHITECTURAL_DECISIONS_AND_OPEN_QUESTIONS.md](32_ARCHITECTURAL_DECISIONS_AND_OPEN_QUESTIONS.md).
