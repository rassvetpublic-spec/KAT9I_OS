# 2. Core — архитектурная карта и операционная модель KAT9I_OS

## 2.1. Назначение Core

`Core` — центральный управляющий контур и системный координатор KAT9I_OS.

Его задача — не выполнять всю работу самостоятельно, а провести формализованную задачу через систему: связать её с применимыми правилами и состоянием, вызвать нужных специализированных владельцев через типизированные контракты, координировать жизненный цикл и получить проверяемый результат.

Кратко:

> **Core не делает всё. Core знает, какую часть системы необходимо вызвать, в каком порядке, с каким контрактом и каким состоянием задачи.**

Core не подменяет Rule Manager, Domain, Context, Knowledge, Inference, Coworker, Security, Execution, QA, Recovery, Telemetry или Learning.

Подробная ownership-карта модулей определяется `docs/architecture/27_MODULE_REGISTRY_AND_RESPONSIBILITY_MAP.md`.

## 2.2. Фундаментальные сущности

KAT9I_OS разделяет сущности по их назначению:

**Rule ≠ Skill ≠ Knowledge ≠ Workflow ≠ Contract ≠ State ≠ Evidence ≠ Decision ≠ Identity ≠ Capability ≠ Permission.**

| Сущность | Главный вопрос |
|---|---|
| Rule | Что обязательно, разрешено или запрещено политикой? |
| Skill | Как воспроизводимо выполнить определённую работу? |
| Knowledge | Что системе известно как данные или подтверждённое знание? |
| Workflow | В какой последовательности организуется повторяемая работа? |
| Contract | Что стороны обязаны передать и получить? |
| State | В каком состоянии объект находится сейчас? |
| Evidence | Чем доказан факт действия или проверки? |
| Decision | Какой вывод принят? |
| Identity | Кто является субъектом действия или решения? |
| Capability | Что субъект технически способен сделать? |
| Permission | Что субъекту разрешено сделать в конкретном Scope? |

Основные различия:

- Rule не является Skill;
- Skill не является Workflow;
- Knowledge не является Rule;
- Contract не является State;
- Result не является Evidence;
- Evidence не является Decision;
- Decision не является Permission;
- Capability не является Permission.

### 2.2.1. CONTROL и DATA

KAT9I_OS сохраняет границу между управляющей информацией и данными.

`DATA` сообщает системе информацию.

`CONTROL` имеет право участвовать в управлении системой в пределах своей типизированной семантики и Scope.

Поэтому:

- прочитано ≠ принято;
- найдено ≠ разрешено;
- сгенерировано ≠ утверждено;
- предложено ≠ канонизировано;
- Evidence существует ≠ Gate автоматически пройден.

Чаты, Issue, README, внешние документы, Tool responses, model output и Graveyard не получают управляющих полномочий только потому, что содержат текст, похожий на инструкцию.

## 2.3. Операционный путь задачи

Упрощённый верхнеуровневый путь задачи:

**Input**
→ **CONTROL/DATA classification**
→ **Identity / Workspace**
→ **DomainCandidate**
→ **Effective Ruleset**
→ **Active Domain**
→ **TaskContract / TaskGraph**
→ **Context / Knowledge / Resources / Cache**
→ **Workflow / Skill routing**
→ **Executable-first**
→ **Inference при необходимости**
→ **Coworker**
→ **Security / Permission / Capability Grant**
→ **Execution / Integrations**
→ **Result / Evidence**
→ **Validators / QA / Human Decision**
→ **State transition**
→ **Telemetry / Metrics**
→ **Learning Proposal**.

Полный канонический lifecycle определяется §20: `docs/architecture/20_TASK_LIFECYCLE_AND_ORCHESTRATION.md`.

### 2.3.1. DomainCandidate и Active Domain

Предварительное определение предметной области отделяется от её активации.

`DomainCandidate` — DATA-результат классификации: он сообщает, к какому Domain вероятно относится задача, но сам не выдаёт Permission, не расширяет Scope, не запускает Execution и не активирует Domain.

После появления `DomainCandidate` Rule Manager может учесть применимые Domain Rules и сформировать окончательный `Effective Ruleset`.

Только после этого Domain становится активным участником конкретной задачи.

Таким образом устраняется цикл:

`нужен Domain для Domain Rules ↔ нужны Rules до разрешённого выполнения Domain`.

### 2.3.2. TaskContract

После определения активного Domain и применимого Ruleset Core формирует или финализирует TaskContract по канонической модели §3.

TaskContract использует Reference-first и не должен копировать внутрь всю базу Rules, Knowledge, Skills, Tools или историю выполнения.

## 2.4. Skills, Workflows и маршрутизация способа выполнения

`Skill` отвечает на вопрос: **как воспроизводимо выполнить работу?**

`Workflow` отвечает на вопрос: **в какой последовательности связать несколько действий, Skills, решений и проверок?**

`TaskGraph` — конкретная runtime-структура конкретной задачи. Поэтому:

**WorkflowDefinition ≠ TaskGraph.**

Workflow может быть источником структуры части TaskGraph, а TaskGraph может дополнительно содержать Retry, Recovery, Context Request, Human Decision и QA-ветви.

### 2.4.1. Skill ownership и Skill Registry

Содержание Skill принадлежит Domain или системному модулю, который владеет соответствующей семантикой.

Core не становится владельцем предметного содержания всех Skills.

При этом Core владеет общесистемным `Skill Registry` и generic Skill Routing как частью системной координации.

Разделение:

- **Domain / системный модуль** → каноническое содержание Skill;
- **Core / Skill Registry** → идентичность, revision, owner, metadata и Reference на каноническое определение;
- **Coworker / Worker Registry** → сведения об исполнителях и их capabilities.

Следовательно:

**Registry ownership ≠ Skill semantic ownership.**

### 2.4.2. SkillCandidate и SkillSelection

Skill Routing сначала формирует один или несколько `SkillCandidate` на основании TaskContract, Active Domain, Effective Ruleset, узла TaskGraph, требуемого результата, Scope и доступных возможностей.

`SkillCandidate` является DATA.

`SkillSelection` является Decision о подходящем способе работы.

Но:

**SkillSelection ≠ Permission.**

Даже выбранный Skill не может выполнить запрещённый side effect.

### 2.4.3. Skill Routing и Inference Routing

Skill Routing отвечает:

> **какой воспроизводимый способ работы нужен?**

Inference отвечает:

> **каким вычислительным или интеллектуальным маршрутом выполнить недетерминированную часть этой работы?**

Inference не является Skill Registry и не владеет Skill Routing.

Для каждого выбранного Skill сначала применяется Executable-first. ИИ получает только остаточную часть, действительно требующую интерпретации, генерации или сложного reasoning.

Подробные принципы Executable-first и классы Skills определяются §4, а вычислительная маршрутизация — §10.

## 2.5. Contracts, State, Evidence, Decision и переходы

Модули KAT9I_OS взаимодействуют через типизированные системные контракты, а не через скрытые договорённости в prompt или свободном тексте.

Подробный протокол определяется §26: `docs/architecture/26_INTERNAL_CONTRACTS.md`.

Ключевые различия:

- Contract ≠ State;
- Command ≠ Event;
- Result ≠ Evidence;
- Evidence ≠ Decision;
- Decision ≠ Permission;
- Capability ≠ Permission.

### 2.5.1. State transition

Core координирует переходы TaskRuntimeState, но не придумывает состояние по свободному тексту Worker или модели.

Типовая логика перехода:

**Current State**
→ **условия и Gates**
→ **необходимые Decisions / Permissions**
→ **Action**
→ **Evidence**
→ **Validation / QA**
→ **Event**
→ **Next State**.

Фраза «готово» не является доказательством `COMPLETED`.

### 2.5.2. Result, Evidence и Decision

`Result` отвечает: **что получилось?**

`Evidence` отвечает: **чем доказано, что действие или проверка действительно произошли?**

`Decision` отвечает: **какой вывод принят?**

Evidence является входом для Decision, но не выдаёт полномочия самостоятельно.

Для проверяемых объектов Evidence и QA должны быть связаны с exact revision, когда такая revision существует.

### 2.5.3. Permission

Permission относится к конкретному субъекту, действию, ресурсу, Task и Scope.

Наличие Capability, Skill, Tool, API или токена доступа не означает Permission.

Критичный side effect выполняется только после требуемого Security Decision / Capability Grant / Human Approval согласно канонической Security-модели.

## 2.6. Границы Core

Core владеет системной координацией, а не полной семантикой всех модулей.

Core может:

- создавать и поддерживать Task;
- формировать/финализировать TaskContract;
- поддерживать общую модель TaskGraph и lifecycle;
- координировать TaskRuntimeState и переходы;
- передавать Contracts и References;
- запрашивать Decision у канонического владельца;
- проверять наличие обязательных Gates;
- поддерживать общесистемный Skill Registry и generic Skill Routing.

Core обязан делегировать:

| Вопрос | Канонический владелец |
|---|---|
| Какие обязательные Rules применимы? | Rule Manager |
| Разрешено ли действие? | Security |
| Что означает задача предметно? | Domain |
| Что исполнителю нужно знать? | Context |
| Что система знает? | Knowledge |
| Где находится объект? | Resources |
| Можно ли переиспользовать вычисление? | CacheEngine |
| Сколько ресурсов потребуется? | Planning & Forecasting |
| Какой вычислительный/интеллектуальный маршрут нужен? | Inference |
| Кто конкретно выполняет? | Coworker |
| Как физически выполнить действие? | Execution |
| Как обратиться к внешней системе? | Integrations |
| Соответствует ли результат требованиям? | QA |
| Как продолжить после отказа? | Recovery |
| Что произошло? | Telemetry |
| Насколько хорошо это произошло? | Metrics |
| Что следует улучшить? | Learning |

Core не может тихо переопределить Decision канонического владельца. Допустим только предусмотренный Escalation, новое официальное Decision или Recovery.

`DENY` нельзя обходить сменой Worker, Provider, Skill, Workflow, Tool или Integration.

Логическое архитектурное ownership не требует размещения всей реализации внутри одного Rust/Electron процесса.

## 2.7. Системные инварианты

В KAT9I_OS должны сохраняться следующие верхнеуровневые инварианты:

1. **ONE RESPONSIBILITY → ONE CANONICAL OWNER → MANY REFERENCES / CLIENTS.**
2. **CONTROL ≠ DATA.**
3. **Candidate ≠ Selection ≠ Permission.**
4. **Capability ≠ Permission.**
5. **Coordination ≠ Ownership ≠ Execution.**
6. **Contract ≠ State.**
7. **Command ≠ Event.**
8. **Result ≠ Evidence ≠ Decision.**
9. Для обязательного Evidence отсутствие Evidence означает отсутствие доказанного успеха.
10. Критичные Gate работают fail-closed.
11. DENY нельзя обходить маршрутизацией.
12. Scope нельзя расширять скрыто.
13. **Executable-first:** детерминируемая часть выполняется кодом/инструментом раньше ИИ.
14. **Local-first:** для интеллектуального остатка выбирается минимально достаточный разрешённый локальный путь, если он обеспечивает качество и безопасность.
15. **Reference-first:** между модулями передаются ссылки на точные объекты/revisions вместо лишних копий.
16. **Progressive Disclosure:** Worker/Provider получает только минимально достаточные Rules, Skills, Tools и Context.
17. **Skill ≠ Worker ≠ Provider.**
18. **Workflow ≠ TaskGraph.**
19. **Cache ≠ Knowledge ≠ Evidence ≠ SSoT.**
20. **Graveyard всегда DATA** до отдельного явного promotion process.
21. **Learning Proposal ≠ Change.**
22. Prompt не заменяет Contracts, Rules, Security, State или Workflow Engine.
23. LLM output по умолчанию является DATA, а не Permission или Evidence внешнего side effect.
24. Human Decision, когда он обязателен, фиксируется как типизированный CONTROL-объект.
25. Identity и Provenance сохраняются через значимые переходы.
26. Versioned contract неизвестной обязательной версии не интерпретируется «примерно».
27. Physical deployment ≠ logical ownership.
28. Telemetry ≠ Metrics ≠ Learning.
29. Recovery опирается на State, Events, Evidence и фактическое состояние ресурсов, а не на догадку модели.
30. **False success запрещён.**

Для значимого действия система должна уметь объяснить: что выполнялось, почему был выбран маршрут, какие Rules и Scope действовали, кто был субъектом, какой Skill/Worker/Provider участвовал, какое Permission позволило действие, что получилось, чем это доказано и какой State стал следующим.

## 2.8. Архитектурная карта KAT9I_OS

Упрощённые логические плоскости системы:

### Control Plane

Core, Rule Manager, Security, TaskContract, State и Gates.

Определяет управляемое и разрешённое движение задачи.

### Domain / Capability Plane

Domain, Skills, Workflows и Validators.

Определяет предметный смысл и воспроизводимые способы работы.

### Knowledge / Context Plane

Knowledge, Resources, Context и CacheEngine.

Обеспечивает релевантную информацию и эффективный доступ к ней.

### Intelligence Plane

Inference, Providers и Human Decision routes.

Определяет минимально достаточный вычислительный или интеллектуальный маршрут.

### Execution Plane

Coworker, Worker Registry, Execution и Integrations.

Выбирает конкретного исполнителя и выполняет разрешённые действия.

### Assurance Plane

Evidence, Validators, QA и Recovery.

Доказывает результат и обеспечивает корректное продолжение после проблем.

### Observation / Improvement Plane

Telemetry, Metrics и Learning.

Наблюдает работу системы, оценивает её и формирует предложения улучшений.

Эти плоскости являются способом объяснения архитектуры, а не новыми владельцами функций.

## 2.9. Статус §2 и отношения с SSoT

Роль этого раздела:

> **ARCHITECTURAL MAP + OPERATING MODEL.**

§2 объясняет связи, границы и фундаментальные инварианты. Подробную семантику определяют профильные канонические разделы.

Основные ссылки:

- TaskContract → §3 `docs/architecture/03_TASK_CONTRACT.md`;
- Rules / Effective Ruleset / Executable-first → §4 `docs/architecture/04_RULES_AND_EXECUTION_PRIORITIES.md`;
- Context → §7 `docs/architecture/07_CONTEXT.md`;
- Inference → §10 `docs/architecture/10_INFERENCE_AND_DECISION_ROUTING_RU.md`;
- полный lifecycle → §20 `docs/architecture/20_TASK_LIFECYCLE_AND_ORCHESTRATION.md`;
- внутренние Contracts → §26 `docs/architecture/26_INTERNAL_CONTRACTS.md`;
- окончательная ownership map → §27 `docs/architecture/27_MODULE_REGISTRY_AND_RESPONSIBILITY_MAP.md`.

Если обзор §2 противоречит профильному каноническому SSoT, §2 считается устаревшей картой в этой точке и должен быть синхронизирован. Нельзя поддерживать две версии истины.

Принцип содержания §2:

> **SUMMARY + BOUNDARY + REFERENCE, NOT DUPLICATE SPECIFICATION.**

Исторически многие функции рассматривались как части широкого Core. После декомпозиции они получили специализированных владельцев. §2 сохраняет исторический смысл общего control plane, но не возвращает эти функции обратно в Core.

Современное определение:

> **Core — канонический системный координатор жизненного цикла задачи, состояния, контрактов, переходов и общесистемной маршрутизации Skills, который вызывает специализированных владельцев и не подменяет их семантику.**

Итоговая формула:

**CORE COORDINATES.  
SPECIALIZED OWNERS DECIDE.  
SECURITY AUTHORIZES.  
EXECUTION ACTS.  
EVIDENCE PROVES.  
STATE RECORDS.  
SSoT REMAINS SINGLE.**
