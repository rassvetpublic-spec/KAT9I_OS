# Architecture Forensics Checkpoint — 2026-09-17

Status: **DATA ONLY / NON-CANONICAL / INTERMEDIATE CHECKPOINT**  
Governing Issue: **#233**  
Implementation Worker: **ChatGPT**  
Independent QA Executor: **Antigravity (AGY)**

## 0. SSoT preflight

Этот файл **не является вторым SSoT** и не меняет действующую архитектуру.

GitHub остаётся единым источником истины проекта. Действующие канонические владельцы остаются в профильных `docs/`, `schemas/`, ADR, Issue/PR и других явно назначенных SSoT.

Назначение этого файла — сохранить промежуточный результат исторической реконструкции так, чтобы дальнейший чат или donor-аудит не переписал происхождение решений задним числом.

Правило каждого следующего прогона:

`current SSoT → exact evidence → historical reconstruction → lost-idea registry → classification → synthesis`

Запрещён обратный маршрут, где donor-идея сначала объявляется правильной, а затем под неё переписывается история.

---

## 1. Зачем вообще начата эта работа

Исходная задача до поиска доноров была не в том, чтобы найти ещё один набор функций для KAT9I_OS.

Задача была восстановить **собственную архитектурную ДНК системы**:

- какие проблемы KAT9I изначально должна была решать;
- какие архитектурные инварианты появились раньше конкретных реализаций;
- какие функции существовали, но исчезли при очистках, переносах или смене репозиториев;
- какие идеи были отвергнуты осознанно, а какие потерялись случайно;
- где возник ownership drift — размывание владельца ответственности;
- где один смысл оказался размножен между Engine, Knowledge, Rules, runtime и GitHub;
- что является минимальным ядром, без которого система перестаёт быть KAT9I;
- что можно оставить сменным модулем, адаптером или внешним исполнителем.

#178 формализовал это как Architecture Tournament: текущая архитектура — только один кандидат, а не автоматически оптимальный вариант. Там же отдельно требуется выписать настоящие invariants, сравнить альтернативы и сохранить superseded-историю вместо её уничтожения.

Поэтому donor-поиск должен идти **после** реконструкции своей линии либо храниться отдельно как внешнее Evidence до завершения этой реконструкции.

---

## 2. Главная методологическая ошибка, от которой защищаемся

Опасный сценарий:

1. найти сильную идею в доноре;
2. принять её за «то, что мы всегда хотели»;
3. подогнать старую историю под новую модель;
4. потерять оригинальные ограничения и причины решений;
5. получить красивую, но исторически ложную архитектуру.

Правильный сценарий:

1. закончить историю собственных commit/PR/Issue;
2. собрать реестр потерянных идей;
3. доказать, что найдено, потеряно, перенесено или superseded;
4. провести ABC/XYZ;
5. только после этого сравнивать собственный Genome с донорами;
6. только затем формировать целевое ядро.

---

## 3. Уже подтверждённые опорные точки текущего SSoT

### 3.1. Контекст и управление

`docs/context/KAT9I_CONTEXT_SSOT.md` закрепляет:

- GitHub — SSoT;
- ChatGPT — Controller/Dispatcher;
- WORKER — исполнитель ChangeSet;
- AGY — независимый QA;
- Codex — анализ/ревью;
- человек владеет `mtd`;
- merge требует QA PASS, обязательные проверки и свежий `mtd` на exact HEAD.

### 3.2. Владение ответственностями

`docs/architecture/27_MODULE_REGISTRY_AND_RESPONSIBILITY_MAP.md` закрепляет принцип одного канонического владельца каждой архитектурной ответственности.

Особенно важно для дальнейшей реконструкции:

- Core не должен становиться Execution, Knowledge, Security или Inference;
- Rule Manager владеет обязательными правилами и Effective Ruleset;
- Knowledge хранит проверенные знания и provenance, но не заменяет Rules, Task State или Cache;
- Execution владеет фактическим исполнением и Evidence;
- Integrations владеют транспортом, а не разрешениями;
- QA проверяет ChangeSet относительно точной revision, scope и применимых правил.

### 3.3. Машинные контракты

`schemas/` является отдельным физическим SSoT машинных контрактов KAT9I_OS. Любая будущая интеграция внешней схемы обязана явно решить ownership, а не создавать вторую равноправную копию.

### 3.4. Knowledge

`docs/architecture/08_KNOWLEDGE_BASE.md` закрепляет, что не всё увиденное моделью становится знанием; полный чат и каждый Worker output не являются автоматически canonical Knowledge. Knowledge Candidate должен пройти классификацию, provenance, trust/freshness и проверку.

---

## 4. Историческая линия, уже найденная до продолжения donor-аудита

Ниже — checkpoint, а не окончательная история. Статус `VERIFIED_REF` означает, что в текущей реконструкции уже найден конкретный Issue/PR/commit reference. `NEEDS_REVERIFY` означает, что знание восстановлено из предыдущего forensic-прохода/чата, но exact GitHub Evidence должно быть повторно поднято перед финальным Genome.

| Epoch / ref | Что было найдено | Значение | Статус |
|---|---|---|---|
| #178 | Architecture Tournament / Discovery Kat9I v1 | Текущий канон не считается автоматически оптимумом; сначала invariants, alternatives, experiments, then accepted decisions | VERIFIED_REF |
| PR #127 | T0→T5 requirements/ABC/XYZ/convergence/baseline pipeline | Синтез архитектуры уже был формализован как последовательность, а не brainstorm→implementation | VERIFIED_REF |
| PR #131 | Requirements Registry | Полнота требований отделена от оценки; незакрытые gaps должны быть видимыми | VERIFIED_REF |
| PR #109 → PR #120 | Потерянный/размытый §2 Core → bounded restoration | Уже был реальный случай, когда core-смысл пришлось восстанавливать forensic-путём | VERIFIED_REF |
| PR #89 | Architecture Convergence Loop | Принцип «полная архитектура — минимальная реализация», Complexity Guillotine | VERIFIED_REF |
| PR #92/#93/#97/#102 | Evidence / promotion / Graveyard / PR salvage | Потерянные варианты должны сохраняться как DATA, но не auto-promote в CONTROL | VERIFIED_REF |
| PR #70–#82 | Контракты, module ownership, identity/approval, journal/recovery, IPC, Scope Guard, vertical slice, tracing, semantic recovery, migration, evals | Ранний плотный слой будущего Core Kernel | NEEDS_REVERIFY exact diff |
| ранний Rules Hub | authority/governance, skills/source-pack/bootstrap, MCP/Obsidian integration line | Возможный источник исходной модели Rule authority | NEEDS_REVERIFY |
| ранний Engine/Knowledge split | Engine отдельно от Knowledge; read-only/provider boundaries; SQLite WAL; registry/routing/privacy | Возможный фундамент разделения control/knowledge/runtime | NEEDS_REVERIFY |
| KAT9I_IIIJIIOXA pre-cleanup | удалённые runtime/prompt/SUNO/agent-role артефакты и старые роли | Возможный массив потерянных функций и semantic role knowledge | NEEDS_REVERIFY |

---

## 5. Seed реестра потерянных идей

Это **не итоговый реестр**. Здесь запрещено окончательно назначать A/X, A/Y, B, C до завершения F1.

| ID | Кандидат | Почему попал в реестр | Текущее состояние | Evidence status | ABC/XYZ |
|---|---|---|---|---|---|
| LOST-001 | Единая authority-линия Rules/Rules Hub | В ранних итерациях governance мог иметь более жёсткого владельца, позднее ownership размылся между документами/модулями | частично отражено Rule Manager | NEEDS_REVERIFY | UNASSESSED |
| LOST-002 | Жёсткая граница Engine ↔ Knowledge ↔ Derived State | Несколько поколений репозиториев меняли роли Engine/Knowledge; риск split-brain SSoT | частично восстановлено текущей responsibility map | NEEDS_REVERIFY | UNASSESSED |
| LOST-003 | Immutable Evidence + idempotency + lease/fencing | Ранние KAT9I-2 PR сформировали системный механизм доказуемого исполнения | отдельные части присутствуют в текущих контрактах | NEEDS_REVERIFY exact coverage | UNASSESSED |
| LOST-004 | Удалённые prompt/SUNO/agent-role assets из KAT9I_IIIJIIOXA | Найдены следы массовой очистки и pre-cleanup архива | часть могла быть сознательно вынесена, часть потеряна | NEEDS_REVERIFY | UNASSESSED |
| LOST-005 | Историческая цепочка ролей LUNA/SUI/KRONOS и другие runtime roles | Поздние документы изменили семантику/порядок ролей | неизвестно, что является историческим invariant, а что UI/implementation detail | NEEDS_REVERIFY | UNASSESSED |
| LOST-006 | Negotiation / consensus / FTS5 идеи | Ранее отмечались как незавершённые архитектурные функции | не доказано, нужны ли в Core | NEEDS_REVERIFY | UNASSESSED |
| LOST-007 | Полная privacy orchestration / split storage | Privacy manifest/split storage были частью старой линии, но полная оркестрация оставалась незавершённой | частично присутствует современная sensitivity/security модель | NEEDS_REVERIFY | UNASSESSED |
| LOST-008 | Rules Hub integration как отдельный контур | Интеграция оставалась incomplete в одном из старых baselines | нужно решить: отдельный контур или современный Rule Manager уже полностью поглотил смысл | NEEDS_REVERIFY | UNASSESSED |
| LOST-009 | CacheEngine альтернативы из закрытых веток | Уникальные требования были salvaged в Graveyard после закрытого PR | сохранено как DATA, не canon | VERIFIED_REF PR #100/#102 family | UNASSESSED |
| LOST-010 | Core §2 responsibilities | Часть смыслов Core была потеряна/размыта и позже восстановлена forensic-проходом | восстановлено bounded-путём | VERIFIED_REF PR #109/#120 | UNASSESSED |
| LOST-011 | Portable bootstrap «КАТЯ-ВХОД» | Возник как способ переносимого входа без второго SSoT | остаётся Discovery/Hypothesis, связан с #180 | VERIFIED_REF | UNASSESSED |
| LOST-012 | Capability-based roles вместо жёстких ролей | #178 поставил под сомнение фиксированный список ролей и постоянный Controller | Discovery, решение не финализировано | VERIFIED_REF #178 | UNASSESSED |
| LOST-013 | Compact Worker Output + minimal metrics + context tags | Дешёвые эксперименты должны были уменьшать token/tool cost без потери Evidence | Discovery/experiment line | VERIFIED_REF #178 | UNASSESSED |
| LOST-014 | MODEL != PLATFORM | Kat9I должна владеть устойчивыми control-функциями, а модели/провайдеры быть сменными execution engines | зафиксировано как проверяемая гипотеза в #178 | VERIFIED_REF | UNASSESSED |
| LOST-015 | Memory hit → refs → current-canon verification → Decision | Memory/retrieval запрещено становиться вторым источником истины | зафиксировано как Discovery guard | VERIFIED_REF #178 | UNASSESSED |

---

## 6. Что уже видно, но пока нельзя превращать в Genome

Даже до завершения реестра повторяются несколько мотивов:

- один канонический владелец ответственности;
- разделение DATA и CONTROL;
- provenance и exact revision важнее «памяти модели»;
- фактическое исполнение должно быть отделено от разрешения и от QA;
- knowledge/memory не имеют права сами создавать authoritative truth;
- сложная архитектура допустима как полная карта, но исполняемое ядро должно быть минимальным;
- сменные модели и runtimes не должны владеть устойчивой системной семантикой;
- исторические варианты нельзя уничтожать, но архив не получает право исполнения.

Это **повторяющиеся сигналы**, а не финальный список Core Kernel invariants. Для финала требуется закончить F0/F1 и проверить происхождение каждого сигнала.

---

## 7. Граница donor-материала

Внешние репозитории и поздние архитектурные решения могут дать сильные идеи, но до F3 они хранятся в отдельной корзине:

`DONOR_EVIDENCE / NOT_OWN_GENOME / NO_AUTO_PROMOTION`.

Отдельно это относится к:

- `NewDeep67/kat9i_skills`;
- `rassvetpublic-spec/AG25`;
- поздним CKS-паттернам, появившимся после исходной линии KAT9I;
- любым внешним agent/runtime системам.

После F3 donor-идея может быть сопоставлена с собственным Genome как:

- подтверждение уже существующего принципа;
- более сильная реализация собственного принципа;
- новый extension;
- конфликт;
- нерелевантный donor artifact.

Но donor никогда не должен ретроспективно становиться источником происхождения собственной идеи.

---

## 8. Обязательный порядок продолжения

### F0 — History completeness

Закончить commit/PR историю до donor boundary для KAT9I_OS, predecessor/Knowledge lineage, Rules Hub и CKS origin line.

### F1 — Lost Ideas Registry completeness

Для каждого элемента получить:

`idea → origin → exact evidence → historical status → loss/supersession reason → current owner → transfer target → proof of no loss`.

### F2 — ABC/XYZ

Только после F1 назначить:

- `A/X` — фундамент;
- `A/Y` — развитие;
- `B` — полезное;
- `C` — архив.

### F3 — Completeness Gate

Требования:

- `UNCLASSIFIED = 0`;
- фундаментальные выводы не имеют `NEEDS_REVERIFY`;
- donor-содержимое отделено от own-lineage;
- для «сохранено» есть доказательство фактического переноса;
- для `OWNER_GAP` создано явное архитектурное решение, а не молчаливое предположение.

### F4 — Architecture synthesis

Только после F3 создавать:

1. `KAT9I_ARCHITECTURE_GENOME.md`;
2. `CKS_ARCHITECTURE_GENOME.md`;
3. `CORE_KERNEL_CONTRACT_v1`.

До этого любые файлы с такими именами были бы преждевременным новым SSoT и создавали бы ровно тот конфликт, от которого защищает forensic-процесс.

---

## 9. Критерий завершения этого checkpoint

Этот checkpoint считается полезным, если новый рабочий чат может начать с #233 и не повторять ошибку «сначала доноры, потом собственная история».

Он **не считается доказательством полноты истории**.

Следующий проход обязан снова начать с SSoT preflight и продолжить F0, а не с разработки Genome.