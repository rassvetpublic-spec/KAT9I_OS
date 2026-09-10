# T0 — полный Requirements Registry KAT9I_OS

> Статус: **T0 INVENTORY / TRACEABILITY**.  
> Этот отчёт не является вторым источником истины требований. Содержание требований остаётся в соответствующих канонических SSoT; machine-readable индекс находится в `requirements_registry.json`.

## 1. Что проверено

Инвентаризация выполнена по baseline `main`:

`6e7eefc0dfac90a9b0bd37ec16b4670a84e1e231`.

В область T0 включены:

- `docs/tz/*.md`;
- все нумерованные канонические разделы `docs/architecture/`;
- `docs/spec/*.md`;
- ADR/OQ registry §32;
- `schemas/v1/*.json` и `schemas/README.md`;
- `modules_registry.json`;
- Gate/Roadmap и Architecture Convergence;
- GitHub development control documents;
- связанные Issue/PR там, где связь подтверждается текущим каноном.

Исторические `KAT9I_OS_ARCHITECTURE_CONTEXT.md` и `MODULE_RESPONSIBILITY_MAP.md` учитываются только как TRACEABILITY. Они не конкурируют с текущими профильными SSoT и §27.

Graveyard используется только как DATA. T0 не повышает Graveyard в CONTROL и не восстанавливает из него требования автоматически.

## 2. Результат T0

Machine Registry содержит **49 нормализованных Requirement-записей** на уровне архитектурной ответственности, инварианта, устойчивого контракта или явно отслеживаемого OQ/assumption.

Гранулярность намеренно не равна «одна строка на каждый абзац Markdown». Один Requirement соответствует отдельной инженерной ответственности или проверяемому системному требованию с одним каноническим SSoT/owner.

Все записи имеют:

- стабильный Requirement ID;
- область и тип;
- canonical SSoT;
- canonical owner;
- целевой Gate и версию;
- Requirement status;
- зависимости;
- machine contract refs, если они уже существуют;
- Evidence/Issue/PR traceability, если подтверждена;
- отдельный Coverage/Contradiction status;
- `ABC=UNASSESSED`;
- `XYZ=UNASSESSED`.

ABC и XYZ сознательно не назначаются до T1/T2.

## 3. Логическая архитектура и physical Module Registry — разные вещи

§27 является канонической логической картой ответственности. `modules_registry.json` на текущем этапе материализует только часть логических модулей.

Поэтому отсутствие, например, Planning, Knowledge, Inference или Coworker как отдельной записи в `modules_registry.json` **не считается автоматически архитектурным GAP**.

T0 различает:

- `MATERIALIZED` — существует текущая materialized/module representation;
- `LOGICAL_ONLY` — ответственность канонически определена, но отдельный runtime/module representation ещё не материализован;
- `DERIVED` — производное представление;
- `NOT_APPLICABLE` — materialization к требованию неприменима.

`Registry ownership ≠ semantic ownership`, а логическая ответственность не обязана совпадать с одним физическим процессом.

## 4. Найденные GAP / CONTRADICTION

Всего зарегистрировано **18** findings T0:

- `TRACEABILITY_GAP` — 1;
- `CONTRADICTION` — 1;
- `CONTRACT_GAP` — 16;
- `OWNER_GAP` — 0;
- `BLOCKED` — 0.

Из них 7 имеют status `OPEN`, остальные 11 явно отложены до своих целевых версий/Gates и не должны ошибочно восприниматься как срочная реализация.

### GAP-T0-001 — неправильная ссылка владельца Execution

`modules_registry.json` для `Execution` указывает `canonical_owner_ref` на §27.14.

Но §27.14 — Coworker, а каноническая ответственность Execution находится в §27.15.

Это **TRACEABILITY_GAP**, а не повод менять ownership в самом T0.

### GAP-T0-002 — конфликт статуса формата machine schemas

§32.45 всё ещё говорит, что точный формат внутренних схем является `OPEN IMPLEMENTATION CHOICE`.

При этом тот же §32 в сводке OQ фиксирует OQ-003/OQ-006 как `ACCEPTED` через ADR-034, а `schemas/README.md` однозначно устанавливает JSON Schema Draft 2020-12 как физический SSoT.

Это текущая **CONTRADICTION**, которую нужно устранять отдельным Architecture Convergence change.

### GAP-T0-003 / 004 — Core и Rule Manager

В §26 устойчиво определены TaskGraph, Effective Ruleset и RulesRef, но соответствующих самостоятельных схем v1 нет.

Для `TaskGraph` и Rules contracts это особенно важно, потому что Core/Rules входят в фундамент первой версии.

T0 фиксирует отсутствие, но не назначает им ABC/XYZ и не придумывает контракт за владельца.

### GAP-T0-011 — ResultRef / EvidenceRef / OutputContract

§26 различает Result и Evidence и определяет ссылки/OutputContract как отдельные сущности. `TaskResult.json` и `Evidence.json` существуют, но самостоятельного физического SSoT для всех трёх логических контрактов пока нет.

Это сохранено как `CONTRACT_GAP`, без предположения, что существующие схемы автоматически эквивалентны отсутствующим сущностям.

### GAP-T0-014 — Telemetry Event / MetricsSnapshot

`SystemEvent.json` существует, но канон не объявляет его полной заменой `Telemetry Event` и `MetricsSnapshot`.

Поэтому T0 не делает скрытое архитектурное решение «SystemEvent = все telemetry/metrics contracts» и оставляет явный contract gap.

### GAP-T0-017 — UIEvent

`modules_registry.json` объявляет `UIEvent` как контракт, предоставляемый DesktopShell, но `schemas/v1/UIEvent.json` отсутствует.

Это прямой machine-registry → schema-catalog gap.

### Остальные отложенные contract gaps

До своих целевых версий явно сохранены gaps для:

- Context Manifest / Context Pack;
- ResourceRef;
- Claim / Lease / Worker Profile;
- Inference Requirement / Provider Route;
- TaskEstimate;
- KnowledgeRef / KnowledgeRecord;
- QA Result;
- Integration Request / Adapter Result;
- Learning Proposal / Safe Adaptation;
- Visualization Snapshot;
- CacheKey / CacheEntry / PayloadRef / CacheCapabilities.

Отложенный gap остаётся видимым; `DEFERRED` не превращается в `COVERED`.

## 5. OQ и незавершённые решения

### OQ-010

На baseline current `main` OQ-010 остаётся `OPEN`.

Есть связанный Issue #122 и PR #123. Его интеграционный candidate `89782343be82ee40e66d4214b91be108712924a0` прошёл deterministic Quality, но на момент T0 ожидает отдельный актуальный independent QA result.

Поэтому T0 сохраняет:

- Requirement status: `OPEN`;
- Coverage: `COVERED`;
- pending PR как Evidence/traceability;
- **без автоматического повышения pending PR в канон**.

После законного merge #123 Registry должен быть обновлён на новый baseline и OQ-010 станет ACCEPTED только потому, что изменился канонический SSoT, а не потому, что T0 решил вопрос самостоятельно.

### OQ-011 / OQ-012 / OQ-013

Они сохраняют текущие статусы §32:

- OQ-011 — `DEFERRED` до pre-release;
- OQ-012 — `DEFERRED` до v0.2;
- OQ-013 — `DEFERRED` до v0.2.

T0 не меняет их сроки.

## 6. Assumptions

A-001…A-007 сведены в отдельную запись типа `ASSUMPTION` со status `OPEN`.

Это важно, потому что предположение о производительности Electron, достаточности SQLite, эффективности Reference-first или локальной модели не должно незаметно становиться принятым архитектурным фактом до Evidence.

## 7. Что готово к T1/T2

После завершения QA T0 все 49 Requirement-записей готовы к следующему процессу:

`T1 ABC → T2 XYZ → T3 ABC×XYZ + Coverage/Contradiction`.

T1/T2 должны оценивать Requirement относительно текущего Gate/версии. Они не должны удалять зарегистрированные gaps и не должны использовать критичность как замену архитектурной определённости.

## 8. Что T0 намеренно не исправляет

T0 не:

- меняет §32.45;
- исправляет `modules_registry.json`;
- создаёт отсутствующие runtime contracts;
- закрывает OQ-010;
- присваивает ABC/XYZ;
- переводит deferred-функции в текущую реализацию;
- повышает Graveyard DATA в CONTROL;
- считает исторические документы вторым SSoT.

Каждое такое действие после T0 должно пройти обычный путь: Requirement/GAP → Issue → Scope → ChangeSet → Quality → независимый QA → Owner Gate.

## 9. Definition of Done T0

T0 считается готовым к независимому QA, когда одновременно выполняются условия:

1. `requirements_registry.json` проходит `schemas/v1/RequirementsRegistry.json`;
2. Requirement IDs уникальны, dependencies разрешаются;
3. каждый non-COVERED Requirement связан с явной gap-записью;
4. весь текущий источник T0 покрыт `source_inventory`;
5. ABC/XYZ везде остаются `UNASSESSED`;
6. known contradiction/gaps не скрыты;
7. Quality Gate проходит на exact HEAD;
8. Antigravity выполняет независимый QA этого exact HEAD.

Merge остаётся отдельным Owner Gate и не входит в автоматическую работу T0.
