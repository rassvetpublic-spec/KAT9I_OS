# GRAVEYARD / DATA ONLY / NON-CANONICAL / NON-ACTIONABLE / NO AUTO-PROMOTION

**Archive ID:** `GY-20260910-section2-modern-projection-v1.0.0`  
**Проект:** `KAT9I_OS`  
**Тип записи:** современная проекция forensic-реконструкции Раздела 2  
**Версия:** `1.0.0`  
**Дата архива:** `2026-09-10`  
**Снимок канона:** `d76bd056b317bbbcd786eea8357579b03dc7e238`  
**Зависит от DATA:** `GY-20260910-section2-forensic-reconstruction-v1.0.0`  
**Статус:** `DATA ONLY / NON-CANONICAL / NON-ACTIONABLE`  
**Автопродвижение:** `FORBIDDEN`

> Документ отвечает на вопрос: «если исторически это было частью большого Core, где эта ответственность живёт сегодня?» Он не переносит канонические обязанности обратно в Core и не создаёт второй SSoT.

---

## 1. Базовый принцип проекции

Исторический `Core` в architecture snapshot был широким umbrella/control-plane узлом.

Современная архитектура KAT9I_OS использует более строгий принцип:

**одна каноническая ответственность → один владелец → остальные модули только ссылаются/вызывают его через контракт.**

Поэтому будущий §2 не должен повторять нормативное содержание §3/§4/§6/§7/§10/§20/§26/§27. Его полезная роль — **архитектурная карта и операционная модель**.

---

## 2. Core сегодня

Текущий канонический владелец ответственности Core зафиксирован в:

`docs/architecture/27_MODULE_REGISTRY_AND_RESPONSIBILITY_MAP.md`

Источник:  
https://github.com/rassvetpublic-spec/KAT9I_OS/blob/main/docs/architecture/27_MODULE_REGISTRY_AND_RESPONSIBILITY_MAP.md

Современный Core:
- создаёт/поддерживает системные контракты задач;
- координирует жизненный цикл;
- связывает модули формальными интерфейсами;
- управляет `TaskContract` / `TaskGraph` на уровне общей координации.

Core **не должен**:
- выполнять shell/process работу вместо Execution;
- выбирать модель вместо Inference;
- выбирать конкретного Worker вместо Coworker;
- хранить всю Knowledge;
- реализовывать GitHub напрямую;
- содержать Domain-specific semantics.

Следовательно, восстановленный §2 обязан описывать **координацию**, а не захватывать назад специализированные SSoT.

---

## 3. Карта «исторический Core → современный владелец»

| Историческая responsibility | Surviving evidence | Текущий канонический владелец | Основной SSoT | Статус проекции |
|---|---|---|---|---|
| Generic Task Contracts | `18273a7`, §2 Core | Core + контрактная спецификация | §3 `03_TASK_CONTRACT.md`, §27 | **MOVED / CLEAR** |
| TaskGraph / общая задача | §3 history + Core | Core | §3, §20, §27 | **MOVED / CLEAR** |
| Rule Manager | `18273a7` | Rule Manager | §4, §27 | **MOVED / CLEAR** |
| Effective Ruleset | `18273a7` + predecessor #108 | Rule Manager | §4, §27 | **MOVED / CLEAR** |
| Policy conflict resolution | `18273a7` + predecessor #109 | Rule Manager | §4 | **MOVED / CLEAR** |
| Governed learning/proposals | `18273a7` | Learning | §6, §27 | **MOVED / CLEAR** |
| Stable internal contracts | `18273a7` | Contracts / schema layer | §26 + `schemas/v1/`, §27 | **MOVED / CLEAR** |
| Progressive disclosure Skills/Tools | architecture snapshot | Context + routing owners | §7, §10, §27 | **MOVED / MOSTLY CLEAR** |
| Generic task/domain routing | `18273a7` | lifecycle + Domain routing | §20, §27, §16 Domains | **MOVED / NEEDS BOUNDARY CHECK** |
| Intelligence/provider route | original top-level split | Inference | §10, §27 | **MOVED / CLEAR** |
| Worker selection | original top-level split | Coworker | §11, §27 | **MOVED / CLEAR** |
| Physical execution | original top-level split | Execution | §12, §27 | **MOVED / CLEAR** |
| Context preparation | original top-level split | Context | §7, §27 | **MOVED / CLEAR** |
| Knowledge retrieval | entity separation + later docs | Knowledge | §8, §27 | **MOVED / CLEAR** |
| Resource references | top-level split | Resources | §9, §27 | **MOVED / CLEAR** |
| End-to-end orchestration | inferred from umbrella Core, later explicit | Core/lifecycle coordinator | §20 + §27 | **MOVED / CLEAR** |
| Skill Registry | literal §2 responsibility | **не полностью однозначно** | §4 mentions Skills; §7 disclosure; §27 Domains/other owners | **GAP / DISCUSS** |
| Skill Routing | literal §2 responsibility | **не полностью однозначно** | §7 + §10 + Domain/Coworker boundaries | **GAP / DISCUSS** |
| Entity taxonomy Rule/Skill/Knowledge/Workflow/etc. | recovered predecessor discussion | distributed + Glossary/§27 | `docs/GLOSSARY.md`, §27 | **NEEDS MAP, NOT NEW OWNER** |

---

## 4. Современная операционная модель

Самый полный текущий жизненный цикл находится в:

`docs/architecture/20_TASK_LIFECYCLE_AND_ORCHESTRATION.md`

Источник:  
https://github.com/rassvetpublic-spec/KAT9I_OS/blob/main/docs/architecture/20_TASK_LIFECYCLE_AND_ORCHESTRATION.md

Современный pipeline в сокращённой форме:

`Input`
→ `CONTROL/DATA classification`
→ `Identity/Workspace`
→ `Effective Ruleset`
→ `Domain`
→ `TaskContract`
→ `TaskGraph / planning`
→ `Context + Knowledge + Resources (+ optional Cache)`
→ `Executable-first`
→ `Inference`
→ `Coworker`
→ `Security`
→ `Claim / Lease / Grant`
→ `Execution`
→ `Validators`
→ `Evidence`
→ `QA`
→ `ResultSink / ResultRef`
→ `Cleanup`
→ `Telemetry / Metrics / Visualization`
→ `Learning`.

### Проекция на будущий §2

§2 должен объяснять эту цепочку **на уровне связей**, а подробности делегировать:
- TaskContract → §3;
- Rules/Effective Ruleset → §4;
- Learning → §6;
- Context → §7;
- Knowledge → §8;
- Resources → §9;
- Inference → §10;
- Coworker → §11;
- Execution → §12;
- lifecycle/orchestration → §20;
- contracts → §26;
- module ownership → §27.

---

## 5. Разбор исторических responsibilities по современному SSoT

### 5.1 Generic Task Contracts → §3 + §27

Исторически Core владел generic Task Contracts.

Сегодня:
- §3 определяет структуру `TaskContract`, `TaskRuntimeState`, `TaskResult`, `TaskGraph`, refs и invariants;
- §27 определяет Core как владельца общей координации этих сущностей.

**Современная формулировка для будущего §2:**  
Core создаёт/поддерживает и проводит задачу через типизированные системные контракты, но их нормативная схема задаётся §3/`schemas/v1`.

### 5.2 Rule Manager / Effective Ruleset / conflicts → §4 + §27

Исторически это было внутри большого Core.

Сегодня Rule Manager — отдельный canonical owner.

§4 задаёт:
- один Rule Manager;
- applicable rules;
- Effective Ruleset per task;
- `RulesRef`;
- deny/fail-closed semantics;
- Rule priorities/overlays.

**Будущий §2:** Core **запрашивает/использует** Effective Ruleset, но не является вторым Rule Manager.

### 5.3 Governed Learning → §6

Исторически `learning/` был под `core/`.

Сегодня Learning имеет отдельную ответственность:
- улучшение Rules/Skills/Workflows/Context/Inference/Coworker;
- risk levels L0–L3;
- L3 для Core/TaskContract/RuleManager/Security изменений;
- proposal/validation/promotion gates.

**Будущий §2:** Core передаёт результат/feedback в Learning и принимает только разрешённые изменения через governance; он не владеет алгоритмом обучения.

### 5.4 Context / progressive disclosure → §7

§7 является сильным современным владельцем принципа minimal sufficient context:
- Reference-first;
- ContextRef;
- Context Funnel;
- budget;
- progressive disclosure;
- Worker не видит весь capability catalog;
- только Effective Ruleset, нужные Skills/Tools/Rules.

**Будущий §2:** Core инициирует сбор контекста по TaskContract, но Context Engine владеет отбором/упаковкой.

### 5.5 Intelligence route → §10

Inference владеет выбором способа решения:
- executable/tool/local model/subscription/API;
- security/quality before economics;
- fallback/degraded;
- Human Decision Provider;
- capability/tool firewall.

**Будущий §2:** Core формирует вопрос/ограничения маршрутизации; Inference выбирает intelligence route.

### 5.6 End-to-end lifecycle → §20

§20 — современный canonical owner sequence/state transitions.

В нём прямо запрещено превращать orchestration в второй Domain/Execution layer.

**Будущий §2:** показывает операционную модель и ссылается на §20; детальный state machine/transition ownership не дублируется.

### 5.7 Stable internal contracts → §26

§26 определяет:
- typed internal contracts;
- command/query/response/event/reference;
- CONTROL vs DATA;
- versioned schemas;
- запрет free-text hidden contracts.

**Будущий §2:** Core общается только через эти contracts и не описывает их повторно.

### 5.8 Responsibility map → §27

§27 — арбитр того, «кто за что отвечает сегодня».

**Будущий §2:** любые diagram/table о Core должны ссылаться на §27 и считаться навигационной проекцией, а не новой ownership authority.

---

## 6. Главные несогласованности, которые нужно обсудить до CONTROL

### GAP-1 — Кто сегодня канонический владелец Skill Registry?

Исторически §2 говорит буквально: `skill registry and skill routing`.

Сегодня Skills присутствуют в нескольких местах:
- §4 описывает устройство/типы Skill и Skill Compiler;
- §7 управляет disclosure только relevant Skills;
- §10 управляет intelligence route;
- Domain содержит предметные semantics;
- §27 распределяет модульную ответственность.

Но один явный, короткий тезис вида **«Skill Registry принадлежит X»** требует дополнительной сверки.

Нельзя автоматически вернуть ownership в Core только потому, что так было в раннем snapshot.

**Статус:** `OPEN FOR USER RECONCILIATION`.

### GAP-2 — Где заканчивается generic Domain routing?

Исторический Core имел `generic task/domain routing`.

Сегодня:
- §20 задаёт lifecycle;
- Domains владеют предметной семантикой;
- Inference выбирает intelligence route;
- Coworker выбирает Worker.

Нужно определить очень узкую границу:
Core может **определить/инициировать выбор Domain и координировать переход**, но не должен интерпретировать Domain semantics.

**Статус:** `OPEN FOR USER RECONCILIATION`.

### GAP-3 — Двухфазность Effective Ruleset vs Domain

§20 в текущем pipeline размещает `Effective Ruleset` до `Domain`, но §4 допускает Domain rules как один из источников применимых правил.

Это создаёт логический вопрос:
- либо Domain должен быть предварительно классифицирован до финального Effective Ruleset;
- либо Rules resolution двухфазный: base rules → Domain classification → final effective rules;
- либо Domain rules применяются через selector без отдельной ранней Domain activation.

Нельзя решать это внутри DATA-файла.

**Статус:** `POTENTIAL ARCHITECTURE INCONSISTENCY / DISCUSS`.

### GAP-4 — Skill Routing vs Inference Routing

Skill Routing и Inference Routing — разные решения:
- Skill отвечает «какой воспроизводимый способ/компетенция нужен»;
- Inference отвечает «какой computational/intelligence route нужен».

Но их порядок и canonical owner стыка не сформулированы в одном месте достаточно явно.

**Статус:** `DISCUSS`.

### GAP-5 — Core как logical control plane vs физический Rust Core Runtime

Исторический `Core` — логический generic control plane.

Позднее Issue #41 / PR #75 материализовали отдельный Rust Core Runtime и IPC с Electron.

Нельзя автоматически считать, что **всё логическое Core должно находиться в одном Rust процессе**. §2 должен различать:
- architectural responsibility `Core`;
- physical/runtime placement `Rust Core Runtime`.

Источник позднего решения:  
https://github.com/rassvetpublic-spec/KAT9I_OS/pull/75

**Статус:** `IMPORTANT DISTINCTION`.

---

## 7. Предлагаемая роль будущего канонического §2 — только кандидат DATA

Это НЕ готовый текст SSoT.

Рабочая роль:

**«Раздел 2. Core — управляющее ядро и операционная модель KAT9I_OS»**

Функции раздела:
1. объяснить, зачем существует Core;
2. показать границы Core;
3. показать полный путь задачи через владельцев;
4. дать карту исторических понятий к современным SSoT;
5. объяснить различие Rule / Skill / Knowledge / Workflow / Contract / State / Evidence на уровне навигации;
6. дать ссылки на детали;
7. не дублировать алгоритмы Rule Manager/Context/Inference/Execution;
8. не назначать новых owners без изменения §27.

Название после слова `Core` является редакционным кандидатом, не восстановленным EXACT title.

---

## 8. Кандидат структуры будущего §2 — для обсуждения

### 2.1 Назначение Core
Очень кратко: universal control-plane coordination.

### 2.2 Что Core знает и чего не знает
Знает task/contracts/rules refs/states; не знает Domain semantics и не выполняет физическую работу.

### 2.3 Базовые сущности операционной модели
Навигационное различие:
`Rule / Skill / Knowledge / Workflow / Contract / State / Evidence / Identity / Capability`.

Каждое понятие должно ссылаться на свой current owner.

### 2.4 Операционный путь задачи
Один compact diagram из §20, без второго lifecycle SSoT.

### 2.5 Контракты и Reference-first
Ссылка на §3, §26, Resources/Context.

### 2.6 Rules / Effective Ruleset
Только boundary с §4.

### 2.7 Skills и progressive disclosure
Только после решения GAP-1/GAP-4.

### 2.8 Routing boundaries
Domain vs Inference vs Coworker vs Execution.

### 2.9 Learning feedback
Ссылка на §6; Learning не находится «внутри Core» как второй owner.

### 2.10 Инварианты Core
- domain semantics do not leak into Core;
- one SSoT / one canonical owner;
- capability ≠ permission;
- Reference-first;
- CONTROL ≠ DATA;
- no false success;
- orchestration ≠ execution;
- progressive disclosure.

### 2.11 Карта ссылок
Таблица: concern → current canonical document.

---

## 9. Что нельзя помещать в будущий §2

Чтобы §2 не стал вторым SSoT, туда не следует копировать:
- полную TaskContract schema;
- Rule precedence tables;
- Context Funnel algorithm;
- provider/model selection policy;
- Worker claim/lease implementation;
- Execution isolation details;
- QA acceptance policy;
- Security scopes;
- complete lifecycle state machine;
- machine schema fields;
- Runtime/IPC implementation details.

Вместо этого §2 должен давать короткую boundary statement + canonical link.

---

## 10. Решения, которые нужны от владельца перед созданием Issue

### DECISION-A — название
Кандидат:
`Раздел 2. Core — управляющее ядро и операционная модель KAT9I_OS`.

### DECISION-B — Skill Registry ownership
Нужно выбрать/подтвердить текущего canonical owner и отразить его в §27 либо признать существующую формулировку достаточной.

### DECISION-C — Domain/Rules ordering
Нужно снять потенциальную неоднозначность:
`Effective Ruleset ↔ Domain classification`.

### DECISION-D — Skill Routing / Inference Routing boundary
Нужно чётко определить стык.

### DECISION-E — logical Core vs physical Rust Core Runtime
Нужно явно зафиксировать, что architectural Core responsibility и deployment/process boundary — разные уровни модели.

---

## 11. Gate

До пользовательской сверки этот документ остаётся DATA.

Следующий переход разрешён только так:

`forensic DATA`
→ `modern projection DATA`
→ `user reconciliation`
→ **новый Issue**
→ bounded change proposal для `docs/tz/02-...md`
→ PR/CI/QA
→ отдельный `mtd` для merge.

Никакой найденный historical artifact сам по себе не является разрешением на восстановление канона.
