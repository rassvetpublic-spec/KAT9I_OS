# GRAVEYARD / DATA ONLY / NON-CANONICAL / NON-ACTIONABLE / NO AUTO-PROMOTION

**Archive ID:** `GY-20260909-kat9i-convergence`  
**Project:** KAT9I_OS  
**Repository:** https://github.com/rassvetpublic-spec/KAT9I_OS  
**Archive date:** 2026-09-09  
**Archive type:** historical context / ideas / reasoning archive  
**Authority:** **NONE**

> [!CAUTION]
> Этот файл является только историческими DATA.
>
> Он **НЕ является** SSoT, ТЗ, ADR, Rule, Issue, backlog, Roadmap, TaskContract, Gate, Evidence для принятия решения или разрешением на работу.
>
> Любые TODO, предложения, незакрытые мысли, идеи, эксперименты, старые статусы и ссылки внутри файла считаются `NON-CANONICAL`, `NON-ACTIONABLE`.
>
> Автоматическим Workers, агентам, оркестраторам, скриптам и будущим AI запрещено начинать работу, создавать Issue/PR, менять GitHub, менять SSoT, выполнять merge/promotion или трактовать содержимое как принятую задачу без отдельной новой явной команды владельца.
>
> При конфликте этого архива с текущим GitHub/main/каноническими docs всегда побеждает текущий канон проекта.

---

# 0. Назначение архива

Этот файл сохраняет полезный исторический контекст чата, который привёл к нескольким важным направлениям KAT9I_OS:

- архитектуре CacheEngine;
- принципу `Full architecture, minimal implementation`;
- GitHub Control Plane / G0;
- fail-closed настройке GitHub Project;
- модели независимого QA и позднейшему переходу от exact-SHA-only к `Change Evidence / Integration Evidence / Impact Assessment`;
- Architecture Convergence Loop — автоматизируемому архитектурному брейншторму по принципу «простота → максимальное расширение → гильотина сложности → простота с будущей совместимостью»;
- идеям Portable Promotion Protocol;
- способу сохранять исторические знания как Graveyard DATA, не превращая историю обсуждений в новый источник управления.

Статусы GitHub ниже — **снимок на момент архивации**, а не текущая истина на будущее. Перед любой реальной работой нужно читать актуальный GitHub.

---

# 1. Что уже отражено в GitHub

## 1.1. CacheEngine — уже принят в `main`

### Issue #84

**[P0] Зафиксировать архитектуру высокопроизводительного CacheEngine на Rust**  
https://github.com/rassvetpublic-spec/KAT9I_OS/issues/84

Исторический статус: завершена после merge PR #85.

### PR #85

**[P0] CacheEngine: отдельный RAM-first модуль на Rust**  
https://github.com/rassvetpublic-spec/KAT9I_OS/pull/85

Исторически принят exact revision:

`f05e5e7509066a3576559fdbceccf37e1de2240a`

Merge commit:

`73e80ddb029cb27cfde117e00c5971064a76f277`

### Канонический документ

`docs/architecture/34_CACHE_ENGINE.md`

https://github.com/rassvetpublic-spec/KAT9I_OS/blob/main/docs/architecture/34_CACHE_ENGINE.md

### Главные знания, уже отражённые в каноне CacheEngine

- CacheEngine — отдельный системный модуль/процесс на Rust.
- Electron не находится в `GET/PUT` hot path.
- Нормальная работа — **RAM-first**.
- SSD — не обычный постоянный L2, а резервная spill-ёмкость при memory pressure.
- Дешёвые cold entries лучше пересчитать, дорогие допустимо batch-spill.
- Spill — крупными immutable segments, а не мелкой записью каждого объекта.
- Startup — без eager restore гигабайт; только manifest/index + lazy GET.
- Cache не является SSoT.
- Полная потеря cache должна сделать систему медленнее, но не неправильной.
- Recovery производного состояния должен быть простым: purge/rebuild, а не сложный repair.
- `CACHE_SESSION_ONLY` не spill'ится в v1.
- `CACHE_LIMITED` spill'ится только после Cache Policy + Security gate.
- Структурный CacheKey должен учитывать source revision/hash и, когда релевантно, Rules/Context/Skill/Workflow semantics.
- TTL — вспомогательный механизм, а не замена известной revision/hash.
- Versioned binary protocol + capability negotiation.
- Будущие `SHARED_MEMORY`, `ZERO_COPY`, `MMAP`, `DISTRIBUTED_CACHE`, `LEARNING_TUNED_POLICY` и т. п. могут быть `SUPPORTED`, не будучи `IMPLEMENTED` или `ENABLED`.
- `PayloadRef` и backend abstraction предусматривают развитие без обязательной реализации будущих механизмов.
- Первая версия использует простые deterministic policies; AI не должен сидеть в hot path.
- SingleFlight/request coalescing признан полезным уже в первой версии.
- Tool-result cache допустим для pure/idempotent reads; side-effect writes не должны кэшироваться как результат выполнения.
- Любая сложная оптимизация требует benchmark evidence.
- Приоритеты: Correctness → Simplicity → Recoverability → Predictability → Speed.
- Системный тест качества: удалить весь cache и подтвердить корректную работу системы.
- Принцип: **Full architecture, minimal implementation.**
- Принцип: **будущая функция обеспечивается контрактом, а не заранее написанным неиспользуемым кодом.**

## 1.2. GitHub Control Plane / G0

### Issue #1

**[G0][P0] Настроить GitHub Project как центр управления разработкой KAT9I_OS**  
https://github.com/rassvetpublic-spec/KAT9I_OS/issues/1

На момент архивации Issue открыта.

Из обсуждения и текущего тела Issue зафиксированы:

- Project `KAT9I_OS — разработка`;
- русские пользовательские поля;
- 3-дневная итерация;
- отдельные `Исполнитель`, `Проверяющий`, `Исполнение`;
- канонический статус review: `Проверка QA`;
- ровно 5 основных рабочих Views:
  - `00 — Все задачи`;
  - `01 — Готово к работе`;
  - `02 — В работе`;
  - `03 — Проверка`;
  - `04 — Заблокировано`;
- архитектура, Security, Evidence, roadmap и unclassified должны быть фильтрами/полями, а не отдельными постоянными вкладками;
- Project — UI/control plane, но не второй SSoT требований;
- фактическая инфраструктура Project/Ruleset/Milestones должна подтверждаться Evidence.

### PR #83

**[G0][P0] chore(github): закрепить mtd, AGENTS и русские Issue Forms (#1)**  
https://github.com/rassvetpublic-spec/KAT9I_OS/pull/83

На момент последних чтений в этом чате:

- PR открыт;
- branch: `chore/issue-1-github-control-plane`;
- HEAD в конце истории чата дошёл до `1bdebc45da4e81657d1ad18894e7dc39f99966db`;
- CI #171 был PASS на этом HEAD;
- PR многократно проходил независимый Codex review;
- после `1bdebc45...` появились новые P2 findings про неоднозначные alias-поля и alias-options;
- PR не был merged в рамках этого чата;
- описание PR местами отставало от фактического HEAD, поэтому future worker обязан читать текущий diff/reviews, а не этот архив.

В PR/ветке исторически отражались:

- `AGENTS.md`;
- русские Issue Forms;
- русский PR template;
- `docs/GITHUB_WORKFLOW.md`;
- `scripts/configure_project.ps1`;
- единый triage helper;
- production/test parity triage;
- PowerShell behavioral tests;
- fail-closed миграции Project;
- запрет безопасно «угадывать» при неизвестных/дублирующих Views/aliases;
- preflight до mutation;
- запрет автоматического merge/QA PASS/Gate PASS.

### Важный исторический QA вывод по PR #83

Через несколько итераций review сформировался общий принцип:

> Административный настройщик должен работать как `Plan / Preflight → Validate → Apply`, причём неизвестное/неоднозначное состояние обязано блокировать mutation, а не исправляться эвристически.

Конкретные выявлявшиеся классы дефектов:

- boilerplate формы ошибочно превращал обычную Issue в Security/P0;
- classifier сначала дублировался в workflow и helper;
- canonical View мог проверяться только по имени, а filter/layout оставаться старым;
- case-variant View мог быть ошибочно принят;
- unknown View мог обнаруживаться уже после части mutations;
- существующая 7-дневная итерация могла быть небезопасно сброшена;
- option ID нельзя было безопасно «пересоздавать» без доказательства сохранения привязок Items;
- `gh issue/pr list` ошибки нельзя маскировать;
- alias field/value ambiguity должна быть fail-closed.

## 1.3. Ruleset blocker

### Issue #87

**[G0][P0] Довести Ruleset main до обязательного Quality Gate**  
https://github.com/rassvetpublic-spec/KAT9I_OS/issues/87

На момент архивации открыта.

Зафиксированный исторический факт:

Ruleset `main-protection`, ID `22520270`, был активен и подтверждал:

- PR-only;
- запрет удаления main;
- запрет non-fast-forward/force push;
- обязательное разрешение review threads;
- отсутствие bypass actors.

При этом на момент проверки не были обеспечены/подтверждены:

- required GitHub Actions / Quality Gate;
- требование актуальной ветки перед merge;
- платформенно выраженный независимый QA.

Ограничение было вынесено в отдельную Issue вместо ложного объявления G0 завершённым.

## 1.4. QA Evidence: REUSE / DELTA / FULL — уже принят в `main`

### Issue #91

**[P0] Bootstrap QA Evidence: убрать автоматический FULL QA при каждом изменении revision**  
https://github.com/rassvetpublic-spec/KAT9I_OS/issues/91

Исторически закрыта как completed.

### PR #92

**[P0] Bootstrap QA Evidence: REUSE / DELTA / FULL вместо повторного QA по SHA (#91)**  
https://github.com/rassvetpublic-spec/KAT9I_OS/pull/92

PR merged.

На момент архивации current `main` был:

`2a63d0e4b20095e3a0983dcff7cb1066dfb02cfa`

Это merge #92.

### Смысл принятой модели

Вместо старого универсального:

`новый SHA → предыдущий QA недействителен → новый FULL QA`

принят более точный подход:

- **Change Evidence** — доказательство корректности ChangeSet;
- **Integration Evidence** — совместимость проверенного изменения с конкретным target/base;
- **Impact Assessment** — определяет применимость Evidence и необходимость REUSE/DELTA/FULL;
- `QA REUSE`;
- `DELTA QA`;
- `FULL QA` с явной причиной.

Новый SHA/rebase/движение target сами по себе больше не считаются достаточной причиной дорогого FULL QA.

При этом сохраняются:

- provenance точной source revision;
- запрет self-QA;
- fail-closed при неопределённости;
- невозможность превратить FAIL в PASS через REUSE;
- совместимость Rules/Policy/Scope/Evidence как условие reuse.

### Документы, затронутые #92

Среди указанных в PR:

- `docs/spec/23_TESTING_QA_AND_READINESS.md`;
- `docs/architecture/20_TASK_LIFECYCLE_AND_ORCHESTRATION.md`;
- `docs/spec/24_GITHUB_PROJECT_MANAGEMENT.md`;
- `docs/architecture/27_MODULE_REGISTRY_AND_RESPONSIBILITY_MAP.md`;
- `docs/spec/13_CACHE_POLICY.md`;
- `docs/architecture/11_COWORKER.md`;
- `docs/architecture/32_ARCHITECTURAL_DECISIONS_AND_OPEN_QUESTIONS.md`;
- `docs/GLOSSARY.md`;
- производный `index.html`.

### ADR / numbering nuance

Описание merged PR #92 исторически говорило о:

- ADR-009 → `SUPERSEDED`;
- новом ADR для применимости QA Evidence.

Позже PR #93 выявил коллизию номера ADR-040 с существующим TraceContext и предложил:

- существующий ADR-040 TraceContext сохранить;
- QA Evidence ADR перенумеровать в ADR-045;
- Portable Promotion зафиксировать как ADR-046.

Следовательно, **точный номер ADR нельзя восстанавливать из этого архива** — его нужно читать из текущего `main`.

## 1.5. Architecture Convergence Loop

### Issue #88

**[G1][P0] Ввести Architecture Convergence Loop для автоматического прогона всего ТЗ**  
https://github.com/rassvetpublic-spec/KAT9I_OS/issues/88

На момент архивации открыта.

Issue хранит сам принцип:

1. простые исходные законы;
2. Minimal Baseline;
3. Maximal Brainstorm без ранней отсечки;
4. карточка каждой идеи;
5. атака на максимальную архитектуру;
6. Complexity Guillotine;
7. возврат к исходным законам;
8. Full Architecture / Minimal Implementation;
9. проверка соседних SSoT;
10. независимый Critic;
11. финальный PASS/FAIL/BLOCKED.

Классы:

- `REQUIRED_NOW`;
- `USEFUL_NOW`;
- `CONTRACT_ONLY`;
- `DEFERRED`;
- `REJECTED`.

### PR #89

**[G1][P0] Architecture Convergence Loop для автоматического прогона ТЗ (#88)**  
https://github.com/rassvetpublic-spec/KAT9I_OS/pull/89

Snapshot на момент архивации:

- открыт;
- Ready for review (`draft=false`);
- branch: `docs/p0-architecture-convergence-loop`;
- HEAD: `5b257e21be8d23878a2eeec75a8c6216be3bccd5`;
- 6 changed files;
- branch был создан от старого main `73e80ddb...`;
- после merge #92 main стал `2a63d0e4...`, поэтому применимость старого QA/Integration Evidence должна оцениваться по новому канону, а не автоматически через FULL QA.

### Файлы PR #89

- `docs/architecture/35_ARCHITECTURE_CONVERGENCE_LOOP.md`;
- `config/architecture_convergence_policy.json`;
- `scripts/architecture_convergence.py`;
- `tests/test_architecture_convergence.py`;
- `.github/workflows/quality.yml`;
- производный `index.html`.

### Важная граница

PR #89 намеренно не должен:

- автоматически менять SSoT;
- автоматически принимать архитектурные решения;
- ставить QA PASS/Gate PASS;
- закрывать Issue;
- выполнять merge;
- реализовывать собственный AI orchestration runtime.

Pass A — только Analysis/Data.

Pass B — отдельные изменения через обычный контролируемый процесс.

## 1.6. Portable Promotion Protocol — открытая архитектурная работа

### Issue #90

**[G0][P0] Portable Promotion Protocol: универсальное безопасное продвижение изменений**  
https://github.com/rassvetpublic-spec/KAT9I_OS/issues/90

На момент архивации открыта.

### PR #93

**[P0] Architecture: Portable Promotion Protocol (#90)**  
https://github.com/rassvetpublic-spec/KAT9I_OS/pull/93

Snapshot на момент архивации:

- открыт;
- `draft=false`;
- branch: `architecture/p0-portable-promotion-protocol`;
- base SHA: `2a63d0e4b20095e3a0983dcff7cb1066dfb02cfa`;
- HEAD: `186c0cdafdb2a188c523f7ffd256abbb45c0ed19`;
- 25 changed files.

PR заявляет архитектуру, но не runtime promotion implementation.

### Идеи/контракты в #90/#93, которые нельзя считать принятыми до merge

- Change Evidence / Integration Evidence / Authorization Evidence как три слоя Promotion;
- PromotionRequest;
- ChangeSetDigest;
- ImpactAssessment;
- PromotionTicket;
- один Promotion Queue;
- SAFE/NORMAL/STRICT/TEAM STRICT policy classes;
- Turbo как speculative preparation scheduler, а не отдельная очередь;
- Promotion Lease + fencing;
- stale-candidate protection;
- capability negotiation;
- один PromotionStore SSoT;
- optional native GitHub Merge Queue adapter;
- personal GitHub account как базовый сценарий;
- graceful degradation при отсутствии capability.

## 1.7. Исторический Gate #62 и Issue #94

### Issue #62

**[GATE][P0] KAT9I_OS: G0→G4, Architecture Baseline раньше Runtime-кода**  
https://github.com/rassvetpublic-spec/KAT9I_OS/issues/62

Исторически закрыта, но в ходе финального аудита этого чата обнаружено, что её тело содержит устаревшие правила:

- старые 10 Project Views;
- старую универсальную семантику `new commit after QA => QA invalid`.

Это конфликтует с #1 и merged #92.

### Issue #94

**[G0][P0] Актуализировать исторический Gate #62 после #1 и #92**  
https://github.com/rassvetpublic-spec/KAT9I_OS/issues/94

Создана до запроса на этот Graveyard archive, в ходе предыдущего аудита чата.

На момент архивации открыта.

Она фиксирует, что будущий Worker не должен восстанавливать текущий процесс из устаревшего тела #62.

## 1.8. Возможный stale/duplicate PR #86

В ходе работы отмечался открытый PR #86:

`docs(architecture): зафиксировать высокопроизводительный CacheEngine на Rust (#84)`

Он выглядел как потенциальный stale/duplicate после уже merged #85/#84.

Это наблюдение историческое. Перед любым действием нужно заново проверить актуальный GitHub.

---

# 2. Знания, которых может не быть в GitHub

> [!IMPORTANT]
> Этот раздел — исторический контекст взаимодействия и причин решений. Он не является текущими Rules.

## 2.1. Как пользователь хочет работать с проектом

- Язык проекта и пользовательских объяснений — русский.
- Объяснения желательно делать простыми, без лишнего усложнения.
- Пользователь учится GitHub и хочет использовать его возможности полноценно как учебный и рабочий control plane.
- В чат **не выдавать большие листинги кода**; изменения лучше выполнять непосредственно в репозитории/артефактах.
- Роль помощника: эксперт по контексту и системам, работающим под управлением AI.
- При системном разборе полезна структура:
  1. что сломалось;
  2. причина;
  3. как починить;
  4. 2–3 предложения улучшения/развития.
- Donor-репозитории идей:
  - `https://github.com/rassvetpublic-spec/AG25`
  - `https://github.com/NewDeep67/kat9i_skills`

## 2.2. Локальная инфраструктурная граница

В локальных установках пользователь сформулировал жёсткое предпочтение:

> всё не должно выползать за пределы папки GIT: установщики, настройки, кэши и логи.

В истории использовался корень вроде:

`C:\Irvis-UPG\GIT`

Это полезно для будущих локальных инструментов, но перед применением нужно снова получить явную задачу пользователя.

## 2.3. Историческая merge-авторизация

До введения/развития Promotion Protocol использовалось правило:

- слово «мерж» само по себе не считалось достаточной авторизацией;
- принятые токены: `mtd`, `MTD`, `мтд`;
- QA/CI не заменяют пользовательскую авторизацию;
- после изменения QA-relevant content требовалась новая авторизация.

Позднее #90/#93 начали проектировать более общую семантику Promotion, где пользовательское намерение «мерж» может означать «продвинь изменение настолько далеко, насколько policy безопасно разрешает», а точный `mtd` связывается с PromotionTicket.

Следовательно, **не использовать старое правило из этого архива как текущий канон**. Читать актуальные Rules/Promotion docs.

## 2.4. Независимый QA

Историческая договорённость:

- self-review Implementation Worker не должен называться независимым QA;
- старый QA нельзя автоматически приклеивать к изменившемуся смыслу ChangeSet;
- при новом reviewer verdict нужно проверять, к чему именно он относится;
- CI PASS — Evidence автопроверок, но не сам по себе independent QA PASS.

После #92 эти идеи стали точнее выражаться через Change/Integration Evidence и Impact Assessment.

## 2.5. Причина рождения Architecture Convergence Loop

Ключевое наблюдение пользователя:

При обсуждении CacheEngine сначала декларировались простота и надёжность, затем брейншторм намеренно расширил архитектуру почти «всё, что можно добавить», после чего лишнее было жёстко отброшено и система вернулась к первоначальному принципу.

Пользователь захотел **сделать именно этот ход мысли повторяемым сценарием для всех разделов ТЗ**.

Это важнее конкретных CacheEngine-фич.

Суть метода:

> Чтобы хорошо упростить архитектуру, сначала нужно честно исследовать максимально широкое пространство решений, а затем осознанно удалить недоказанную сложность.

## 2.6. Почему «максималистская стадия» обязательна

Без неё команда рискует:

- принять первое простое решение как единственно возможное;
- не увидеть более сильный контракт;
- не заметить будущий breaking change;
- спутать «простоту» с недостаточной архитектурой.

Но максималистская стадия **не является разрешением реализовать всё найденное**.

## 2.7. Почему «гильотина сложности» обязательна

Без неё brainstorm превращается в feature accumulation.

Для каждого элемента полезный вопрос:

> Что реально сломается, если полностью удалить эту возможность?

Если ответ только:

- станет медленнее;
- станет менее удобно;
- потеряется гипотетическая оптимизация;

то это сильный кандидат на `CONTRACT_ONLY`, `DEFERRED` или `REJECTED`, а не `REQUIRED_NOW`.

## 2.8. Важная формула развития

Историческая формула, пришедшая из CacheEngine:

> **Full architecture, minimal implementation.**

И:

> **Будущая совместимость должна обеспечиваться контрактом, а не заранее написанным неиспользуемым кодом.**

## 2.9. Историческое ограничение коннекторов

В нескольких сессиях GitHub connector позволял читать Ruleset, но не изменять его, а Project v2 write-actions были недоступны.

Это **не постоянное свойство GitHub/KAT9I_OS**, а историческое ограничение доступного tool surface. Нельзя считать его актуальным без новой проверки.

## 2.10. Codex cloud environment

В PR #89 попытка поручить Codex сделать commit получила ответ:

`To use Codex here, create an environment for this repo.`

Это исторический operational detail, а не архитектурное ограничение проекта.

---

# 3. Идеи — НЕ ПРИНЯТЫЕ К РЕАЛИЗАЦИИ

> [!WARNING]
> **ВСЕ ПУНКТЫ ЭТОГО РАЗДЕЛА — НЕ ПРИНЯТЫЕ К РЕАЛИЗАЦИИ ИДЕИ.**
>
> Они не являются backlog и не разрешают никакие действия.

## 3.1. Полный автоматический Pass A всего ТЗ

Идея:

- обнаружить все канонические архитектурные/spec разделы;
- для каждого сформировать Explorer + Critic контекст;
- прогнать Architecture Convergence Loop;
- не менять SSoT;
- сформировать сводную карту:
  - оставить;
  - упростить;
  - расширить только контракт;
  - требуется исследование;
  - потенциальный Issue candidate.

Даже если механизм в PR #89 предусматривает manifest, фактический массовый AI-прогон всех разделов в этом чате не был выполнен и не является разрешённой задачей.

## 3.2. Complexity Budget как постоянная метрика архитектуры

Предлагалось считать минимум:

- Processes;
- Persistent State;
- Public Contracts;
- Mandatory Dependencies;
- Background Jobs;
- Recovery Paths;
- Security Boundaries;
- Configuration Surface.

Рост сам по себе не FAIL, но должен требовать объяснения.

PR #89 отражает эту идею, но до merge это не текущий канон.

## 3.3. Deletion Test

Для каждого компонента автоматически спрашивать:

> Если удалить это полностью, нарушится корректность или только производительность/удобство?

Использовать для борьбы с premature complexity.

## 3.4. Future Without Implementation Test

Для будущей функции спрашивать:

> Можно ли обеспечить её будущую совместимость контрактом/enum/capability/interface без реализации механизма сейчас?

## 3.5. Расширенная автоматизация Architecture Convergence

Возможное будущее:

- отдельный orchestrator;
- параллельные Explorer/Critic Workers;
- автоматическая dependency/blast-radius карта;
- external donor scan;
- ranking architectural debt.

**НЕ ПРИНЯТО:** отдельный собственный AI orchestration runtime только ради первой версии Convergence Loop.

## 3.6. CacheEngine future capabilities

Рассматривались, но не должны автоматически становиться текущей реализацией:

- shared memory;
- zero-copy;
- mmap;
- content deduplication;
- namespace quotas;
- negative cache;
- compression;
- encryption backend;
- distributed cache;
- learning-tuned policy;
- NUMA awareness;
- huge pages;
- custom allocator;
- GPU-oriented cache;
- remote cache nodes.

Часть из них архитектурно `SUPPORTED`, но это **не запрос на IMPLEMENTED/ENABLED**.

## 3.7. Promotion runtime

На базе #90/#93 обсуждаются:

- Promotion Bridge;
- durable PromotionStore;
- GitHub Actions adapter;
- GitHub App;
- native Merge Queue integration;
- SAFE auto-promotion;
- Turbo speculative preparation;
- batch/multi-PR promotion;
- local/manual fallback по sealed PromotionTicket.

Пока соответствующий канон/реализация не приняты, эти пункты — только предложения/архитектурные кандидаты.

## 3.8. Автоматическая выдача Issues из brainstorm

Идея: Pass A может предлагать Issue candidates.

Жёсткая историческая граница:

> Analysis может предложить кандидата, но не должен автоматически превращать его в backlog или создавать Issue без отдельной управляющей команды/политики.

## 3.9. Graveyard как отдельный слой истории

Идея этого запроса:

- сохранять удаляемые чаты в DATA-only graveyard;
- явно исключать auto-promotion;
- разделять историю идей и текущий Control Plane;
- future Workers могут читать graveyard только как контекст, но не как task source.

Эта идея сама по себе не считается внедрённой в KAT9I_OS.

---

# 4. Отвергнутые или заменённые решения

## 4.1. CacheEngine: SSD как обычный постоянный второй уровень

**Рассматривалось:** регулярное хранение cache на SSD.  
**Почему отказались:** лишние writes, latency, compaction/maintenance, износ SSD, сложнее recovery.  
**Заменено:** RAM-primary; SSD только spill при memory pressure.

## 4.2. CacheEngine: запись каждого entry на диск

**Рассматривалось:** per-entry spill/write.  
**Почему отказались:** много мелких I/O и metadata operations.  
**Заменено:** batch immutable spill segments.

## 4.3. CacheEngine: сложный repair производного состояния

**Рассматривалось:** восстанавливать/чинить cache storage как важные данные.  
**Почему отказались:** cache не SSoT.  
**Заменено:** delete/rebuild/purge/lazy reconstruction.

## 4.4. CacheEngine: реализовать все будущие оптимизации заранее

**Рассматривалось:** shared memory, zero-copy, distributed cache, dedup, mmap, learning policy и т. п. сразу.  
**Почему отказались:** недоказанная сложность.  
**Заменено:** capability/versioned contracts + `SUPPORTED / IMPLEMENTED / ENABLED`.

## 4.5. CacheEngine: Electron/HTTP JSON в hot path

**Рассматривались более простые интеграционные варианты.**  
**Почему отказались:** latency/coupling/UI lifecycle.  
**Заменено:** отдельный Rust process, low-level local IPC; Windows Named Pipes как предпочтительное направление.

## 4.6. GitHub Project: 10 постоянных Views

**Рассматривалось/было реализовано в раннем PR #83:** отдельные вкладки для архитектуры, безопасности, evidence, roadmap и т. д.  
**Почему отказались:** Project становился перегруженным и противоречил принципу простоты.  
**Заменено в Issue #1:** ровно 5 основных рабочих Views, остальные измерения через поля/фильтры.

## 4.7. Project configurator: «починить по пути»

**Рассматривалось фактически:** создавать/менять часть Project, затем обнаруживать конфликт.  
**Почему отказались:** partial mutation оставляет неоднозначное состояние.  
**Заменено:** полный preflight/fail-closed до first write.

## 4.8. Автоматически удалять неизвестные Views

**Почему отказались:** неизвестный View может быть пользовательским.  
**Заменено:** delete only known legacy set; unknown → fail-closed/manual analysis.

## 4.9. Автоматически сбрасывать существующую Iteration до 3 дней

**Почему отказались:** риск потери periods/item bindings.  
**Заменено:** несовместимая существующая iteration → fail-closed, явная миграция.

## 4.10. Статические строковые тесты вместо поведения

**Рассматривалось:** тест проверяет, что нужные строки присутствуют в скрипте.  
**Почему отказались:** не доказывает runtime fail-closed.  
**Заменено:** PowerShell behavioral mocks и позднее AST-проверки фактического production Apply path.

## 4.11. Дублирование triage classifier

**Рассматривалось/существовало:** логика и в workflow, и в helper.  
**Почему отказались:** divergence production/test.  
**Заменено:** единый helper, который вызывает production workflow и тестирует CI.

## 4.12. Exact-SHA-only QA invalidation

**Старое правило:** любой новый commit/SHA после QA автоматически инвалидирует QA целиком.  
**Почему заменено:** дорогой повторный FULL QA даже при неизменном ChangeSet.  
**Заменено merged #92:** Change Evidence + Integration Evidence + Impact Assessment → REUSE / DELTA / FULL.

## 4.13. Несколько отдельных Promotion queues

В #90 рассматривалась потребность различать SAFE/SOLO/TEAM/TURBO.

**Предложенная замена в текущей архитектурной работе:** один Promotion Queue; policy/risk различаются метаданными, Turbo — scheduler, а не отдельная безопасность/очередь.

До merge #93 это не канон.

## 4.14. AI semantic fingerprint как основная identity изменения

В Promotion brainstorming более надёжным вариантом признан deterministic `ChangeSetDigest`.

AI предлагается использовать только как слой impact-analysis при неоднозначности, но не как единственный источник identity.

До принятия #93 — не канон.

---

# 5. Нерешённые мысли — НЕ BACKLOG

> [!WARNING]
> Этот список не является backlog, TODO или очередью работ.

## 5.1. PR #83

На конец истории чата:

- PR всё ещё открыт;
- после HEAD `1bdebc45...` Codex нашёл новые P2:
  - одновременно canonical field + alias field;
  - одновременно canonical option + legacy alias option;
- нужен актуальный Impact Assessment относительно merged #92;
- #93 также меняет связанный GitHub/Promotion канон;
- body PR местами не соответствовал фактическому HEAD.

Любая будущая работа должна начинаться с текущего PR state, а не этого архива.

## 5.2. PR #89

- independent QA на старом base был запрошен;
- после merge #92 `main` изменился;
- по новой QA модели нужно определить применимость Change Evidence и новый Integration Evidence;
- не следует автоматически запускать FULL QA только из-за нового base;
- фактическая дальнейшая судьба PR должна решаться по текущему GitHub.

## 5.3. Issue #87

Нужно ли/как технически выразить:

- required Quality status check;
- up-to-date branch;
- independent QA constraint;
- ruleset compatibility с реальными возможностями тарифа/репозитория.

## 5.4. Issue #94 / исторический #62

Остаётся вопрос:

- оставить #62 как historical/superseded Gate pointer;
- или актуализировать его как живой Gate index.

Главный риск: future Workers могут прочитать старые 10 Views и старое SHA-only QA правило.

## 5.5. Project v2 и Milestones

В чате не было подтверждено фактическое выполнение всех критериев #1:

- реальные поля/Views;
- Milestones;
- полная Project automation;
- independent QA фактических platform settings.

## 5.6. Promotion Protocol

PR #93 — открытая архитектурная работа.

Нерешённые направления включают:

- runtime PromotionStore;
- Promotion Bridge;
- capability matrix;
- SAFE policy;
- fencing/lease implementation;
- manual fallback;
- native queue adapter;
- cost/QA economics.

Они не backlog из этого архива.

## 5.7. CacheEngine implementation

Архитектура принята, но сам этот чат в основном обсуждал архитектуру, а не runtime implementation CacheEngine.

Не считать перечисленные future capabilities разрешением на реализацию.

## 5.8. Codex environment

В определённый момент Codex не мог делать commits без cloud environment для repo.

Неясно, актуально ли это сейчас.

## 5.9. Google Drive public sharing

Коннектор смог загрузить QA ZIP, но не мог включить `anyone with the link`; файл исторически показывался как `shared=false`.

Текущий доступ неизвестен.

---

# 6. Файлы и артефакты чата

## 6.1. `KAT9I_OS_PR83_QA_f097d60e.zip`

**Назначение:** автономный QA snapshot PR #83 на старой revision  
`f097d60e4511c1fddf47cb7329f7555f399c5dbc`.

Содержал snapshot изменённых файлов, Issue #1/#62, PR metadata, QA task, CI status, manifest.

**Статус сейчас:** устаревший historical Evidence package.

**Сохранять отдельно?** Только если нужна история QA. Для текущего merge использовать нельзя.

**Связь с GitHub:** snapshot старого PR #83.

Исторический sandbox path:

`/mnt/data/KAT9I_OS_PR83_QA_f097d60e.zip`

Sandbox paths живут только в соответствующей ChatGPT-среде и не являются надёжным внешним архивом.

## 6.2. `KAT9I_OS_PR83_QA_05ffce13.zip`

**Назначение:** обновлённый автономный QA snapshot PR #83 на более позднем HEAD.

Позднее QA-пакеты ещё обновлялись в ходе развития PR, включая revisions после `05ffce13`.

**Статус сейчас:** также устаревший относительно позднего HEAD `1bdebc45...`.

**Сохранять отдельно?** Только как historical QA trail.

## 6.3. Google Drive QA file

Исторический Drive ID:

`1ksD75963I3RQJk8Do05VYOSr_DsigoQs`

Использовавшиеся ссылки:

`https://drive.google.com/file/d/1ksD75963I3RQJk8Do05VYOSr_DsigoQs/view?usp=drivesdk`

`https://drive.google.com/uc?export=download&id=1ksD75963I3RQJk8Do05VYOSr_DsigoQs`

Особенность: содержимое файла под тем же Drive ID несколько раз заменялось более новым QA ZIP.

Следовательно:

- URL **не является immutable Evidence**;
- нельзя по одному ID доказать, какой SHA лежит там сейчас;
- historical QA provenance нужно брать из GitHub/manifest, а не из mutable Drive link.

На момент одной из проверок `shared=false`.

**Сохранять отдельно?** Только если нужен старый внешний пакет; не использовать как канон.

## 6.4. Производный `index.html`

Несколько PR меняли канонический Markdown и обязаны были регенерировать `index.html`.

В PR #89 временно использовался GitHub Actions workaround для генерации/commit большого `index.html`, затем временные write-permissions/workflow были удалены.

**Сохранять отдельно?** Нет. Это derived artifact; источник истины — Markdown docs.

## 6.5. Временные GitHub Actions workflows

В ходе PR #89 создавались временные механизмы для получения/коммита generated `index.html`.

Они были намеренно удалены из итогового diff.

**Сохранять отдельно?** Нет. Это troubleshooting history, не проектный контракт.

## 6.6. Этот Graveyard archive

Файл:

`GY-20260909-kat9i-convergence.md`

**Назначение:** сохранить историю чата как DATA-only.

**Сохранять отдельно?** Да, если пользователь хочет иметь архив после удаления чата.

**Связь с GitHub:** ссылки на GitHub есть, но сам файл не должен автоматически импортироваться в GitHub/SSoT.

---

# 7. Внешние источники

## 7.1. Канонический проект

KAT9I_OS  
https://github.com/rassvetpublic-spec/KAT9I_OS

## 7.2. Donor / comparison repositories

AG25  
https://github.com/rassvetpublic-spec/AG25

kat9i_skills  
https://github.com/NewDeep67/kat9i_skills

Они использовались/предлагались как источники идей и сравнения, но их решения не должны автоматически импортироваться.

## 7.3. Учебный GitHub-проект пользователя

local-listener-android  
https://github.com/rassvetpublic-spec/local-listener-android

Он использовался как пример того, как пользователь хочет организовать GitHub:

- Project как control center;
- простой русский язык;
- обучение GitHub через реальную структуру проекта.

## 7.4. Google Drive historical QA asset

См. раздел 6.3.

Это transient external artifact, не источник истины.

## 7.5. Codex environment page

В ответе GitHub bot появлялась ссылка настройки Codex environment:

`https://chatgpt.com/codex/cloud/settings/environments`

Это operational link, не архитектурный источник.

---

# 8. Краткая хронология

## Этап 1. GitHub как Control Plane

Началась глубокая настройка PR #83 / Issue #1:

- русский GitHub workflow;
- формы;
- mtd gate;
- Project configurator;
- triage;
- 3-дневные итерации;
- Views;
- fail-closed поведение.

В процессе независимый QA многократно находил реальные дефекты, и правило настройки постепенно стало строже: сначала проверка формы, затем preflight, затем behavioral/AST verification.

## Этап 2. CacheEngine — исходная простота

Базовая идея:

- Cache — только ускорение;
- не SSoT;
- простота и надёжность;
- потеря cache не должна ломать корректность.

## Этап 3. CacheEngine — максималистский brainstorm

Были рассмотрены:

- RAM/SSD tiers;
- spill;
- immutable segments;
- shared memory;
- zero-copy;
- dedup;
- quotas;
- mmap;
- compression;
- distributed cache;
- AI/learning policies;
- protocol capabilities;
- future backends;
- metrics/benchmarks;
- complex performance optimizations.

## Этап 4. CacheEngine — отсечение сложности

Произошёл сознательный возврат к исходным законам:

- RAM-primary;
- SSD только spill;
- simple recovery;
- deterministic policy;
- SingleFlight;
- future mechanisms только через contracts/capabilities;
- benchmark-first;
- no AI in hot path.

Этот результат был принят через #84/#85 и стал каноническим §34.

## Этап 5. Выделение общего метода мышления

Пользователь явно сформулировал наблюдение:

> сначала простота → потом добавить почти всё → затем обрубить лишнее и вернуться к первому принципу.

Возникло требование превратить это в повторяемый сценарий для каждого раздела ТЗ.

## Этап 6. Architecture Convergence Loop

Созданы #88 и PR #89.

Сценарий формализован как:

`laws → minimal → maximal → classify → attack → guillotine → return → contracts → blast radius → critic → report`

Добавлены идеи:

- Complexity Budget;
- Deletion Test;
- Future Without Implementation Test;
- Explorer/Critic roles;
- deterministic manifest;
- CacheEngine calibration case.

Первая реализация намеренно не стала отдельным AI runtime.

## Этап 7. Развитие QA semantics

Старый exact-SHA-only подход оказался слишком дорогим.

Созданы #91/#92.

После независимого QA и исправлений в `main` принята модель:

`Change Evidence + Integration Evidence + Impact Assessment → REUSE / DELTA / FULL`

Current main на момент архивации стал `2a63d0e4...`.

## Этап 8. Promotion brainstorming

Созданы #90/#93.

Появилась более общая модель Promotion вместо узкой «merge queue»:

- Change/Integration/Authorization evidence;
- PromotionTicket;
- one queue;
- SAFE/STRICT policy;
- Turbo preparation;
- lease/fencing;
- stale target checks;
- capability negotiation;
- personal GitHub support;
- graceful degradation.

На момент архивации это открытая работа, не принятый runtime.

## Этап 9. Финальный аудит перед удалением чата

Проверка показала:

- CacheEngine knowledge уже в main;
- QA reuse model уже в main;
- GitHub Control Plane и Convergence Loop всё ещё в open PR;
- historical Issue #62 конфликтует с #1/#92.

До текущего Graveyard-запроса была создана Issue #94, чтобы этот конфликт не потерялся после удаления чата.

## Этап 10. Graveyard archive

Пользователь потребовал сохранить чат как:

`DATA ONLY / NON-CANONICAL / NON-ACTIONABLE / NO AUTO-PROMOTION`

без каких-либо новых изменений GitHub.

---

# 9. Исторические принципы, которые объясняют развитие проекта

Этот раздел нужен не как Rule, а как объяснение, почему решения эволюционировали именно так.

## 9.1. Простота — не отсутствие архитектуры

Простота должна быть результатом понимания пространства решений, а не отсутствия исследования.

## 9.2. Надёжная система должна уметь потерять производное состояние

Если cache/index/derived data требует сложного disaster recovery, возможно, он незаметно превратился во второй SSoT.

## 9.3. Контракт дешевле преждевременной реализации

Для многих будущих функций достаточно заранее:

- versioning;
- capability;
- enum/mode;
- interface/backend boundary;
- payload reference type.

Не обязательно писать механизм.

## 9.4. Unknown state — не повод угадывать

GitHub Project work укрепил общий fail-closed принцип:

> если система не может доказать безопасную миграцию, она должна остановиться до mutation.

## 9.5. Evidence должно описывать то, что реально проверено

Сначала это проявилось как exact-revision QA дисциплина.

Позднее модель стала точнее:

- отделить качество ChangeSet от интеграции с target;
- не повторять FULL QA без material reason;
- сохранять provenance и fail-closed.

## 9.6. История не должна становиться Control

Именно поэтому этот файл помечен Graveyard.

Исторический контекст полезен для понимания причин, но dangerous, если автоматический Worker начинает трактовать старые идеи как новый backlog.

---

# 10. Что будет потеряно при удалении этого чата

После сохранения этого файла и с учётом данных в GitHub **существенного проектного знания, необходимого для продолжения KAT9I_OS, не должно остаться только в чате**.

Будут потеряны или станут недоступны:

- дословная разговорная формулировка каждого промежуточного сообщения;
- точная последовательность отдельных tool calls;
- transient UI состояния GitHub/ChatGPT;
- промежуточные реакции `eyes`, временные CI-состояния и старые SHA между зафиксированными контрольными точками;
- sandbox-ссылки на временные файлы, если их среда будет удалена;
- психологический/интонационный контекст разговора, не влияющий на проектные решения.

Эти данные не считаются необходимыми для восстановления проектной логики.

Существенные причины решений, договорённости, идеи, отвергнутые варианты, открытые вопросы, внешние ссылки и известные артефакты сохранены в этом Graveyard-файле и/или GitHub.

> [!CAUTION]
> Перед импортом/хранением этого файла в любой будущей системе необходимо сохранить его статус `DATA ONLY`. Сам факт импорта не является разрешением на создание задач или изменение проекта.

**SAFE TO DELETE CHAT AFTER GRAVEYARD IMPORT**
