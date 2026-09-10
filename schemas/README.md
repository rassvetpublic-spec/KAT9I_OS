# Канонические машинные контракты KAT9I_OS

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
├── README.md                         # Настоящий манифест и правила
└── v1/                               # Канонические схемы версии 1
    ├── TaskContract.json             # Паспорт и требования к задаче
    ├── TaskRuntimeState.json         # Текущее состояние исполнения задачи
    ├── TaskResult.json               # Итоговый результат выполнения
    ├── Evidence.json                 # Запись аудита и доказательства корректности
    ├── SecurityDecision.json         # Вердикт проверки безопасности Scope Guard
    ├── CapabilityGrant.json          # Выданный мандат прав и возможностей
    ├── SystemEvent.json              # Универсальный конверт системных событий
    ├── ModuleRegistry.json           # Машинный реестр модулей и граф зависимостей
    ├── Identity.json                 # Идентичность субъекта и привязка к Windows
    ├── ApprovalRecord.json           # Структурированное одобрение человеком с защитой от replay
    ├── JournalEvent.json             # Элемент append-only журнала событий Event Journal
    ├── Checkpoint.json               # Снимок состояния задачи для Replay Recovery
    ├── CoreIpcMessage.json           # Контракт типизированного IPC между Electron и Rust Core
    ├── SecretRef.json                # Ссылка на защищённый секрет (DPAPI) без раскрытия значения
    ├── PromotionRequest.json         # Состояние очереди продвижения (§36)
    ├── ChangeEvidence.json           # Доказательства проверки изменения
    ├── ImpactAssessment.json         # Применимость QA: REUSE / DELTA / FULL
    ├── PromotionTicket.json          # Точный билет финального продвижения
    ├── ContextRef.json               # Ссылка на контекст с provenance/trust/DATA-CONTROL признаками
    ├── GraveyardCandidate.json       # Неисполняемый кандидат на ручное возвращение идеи
    ├── GraveyardExcavateRequest.json # Запрос команды «Раскопать идею»
    └── GraveyardActivationTicket.json# Exact DATA-ticket, хэш которого подтверждает ApprovalRecord
```

Физический список файлов в `schemas/v1/` может быть шире этого краткого перечня по мере развития уже принятых контрактов. Каноническим является сам каталог и конкретные схемы, а не пример дерева выше.

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

## 5. Контекст и Graveyard

`ContextRef.json` материализует уже объявленный в Module Registry контракт Context и делает машинными свойства источника: provenance, trust, freshness, `actionable`, `control` и `canonical`.

Для любого ContextRef с Graveyard-provenance обязательны:

- `source_class=graveyard`;
- `actionable=false`;
- `control=false`;
- `canonical=false`;
- `freshness=ARCHIVED`;
- `access=read`;
- resolver `graveyard_manifest`.

Reference policy распознаёт Graveyard не только по `source_class`, но и по `ref_id`, resolver, URI и provenance URI. Поэтому изменение одного поля классификации не должно превращать архив в разрешение для Planner.

`GraveyardCandidate.json` описывает промежуточный DATA-объект. После завершённой сверки с текущим каноном обязательно сохраняется непустая `checked_revision`. Состояния `CONFLICT`, `SUPERSEDED` и `UNKNOWN` блокируются.

## 6. Команда «Раскопать идею» и Human Approval

Путь возврата идеи разделён на независимые объекты:

`Graveyard DATA → ContextRef → GraveyardCandidate → canon check → GraveyardActivationTicket → ApprovalRecord → provenance normal workflow`

`GraveyardExcavateRequest.json` — типизированное пользовательское намерение. Оно относится к уже существующей user-initiated review-задаче и само не создаёт новый Issue, ADR или TaskContract.

`GraveyardActivationTicket.json` запечатывает точные параметры предлагаемого перехода:

- candidate и Archive ID;
- ContextRef;
- точную revision проверенного текущего канона;
- какой обычный рабочий объект предлагается создать;
- target;
- время выдачи и истечения.

Ticket остаётся `actionable=false`, `control=false` и `requires_approval=true`.

Human Approval использует уже существующий канонический `ApprovalRecord.json`. Его `action_hash` должен быть равен SHA-256 канонического представления **точного** `GraveyardActivationTicket`. Дополнительно проверяются:

- `approver_identity_id` против `Identity.json`;
- `HUMAN_USER` и роль `LOCAL_USER`/`LOCAL_ADMIN`;
- допустимый Trust Level;
- Windows binding;
- elevation для `LOCAL_ADMIN`;
- совпадение `task_id`;
- срок действия ticket и Approval;
- одноразовый `nonce` против replay.

Даже после валидного Approval `GraveyardCandidate` остаётся DATA: `actionable=false` и `control=false`. На выход передаётся только provenance в обычный актуальный workflow.

## 7. Граница текущей реализации

`scripts/graveyard_excavate.py` и `scripts/graveyard_context.py` являются исполняемым reference implementation контрактов и security semantics без внешних side effects.

Они **не являются production Rust Core или Electron UI**. Физическая интеграция этих контрактов в Rust Core, IPC и DesktopShell выполняется только после разблокировки соответствующего Runtime Gate согласно управляющему Issue #62 и этапу G3/#41. До этого нельзя выдавать reference Python-слой за готовый product runtime.

Persistence replay-store (durable nonce consumption после перезапуска), Windows token verification в Rust и реальный UI→Core IPC также относятся к будущей Runtime-реализации. Reference tests проверяют семантику fail-closed, но не подменяют эти системные доказательства.
