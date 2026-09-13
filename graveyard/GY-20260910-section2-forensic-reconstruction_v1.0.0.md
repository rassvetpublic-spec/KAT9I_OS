# GRAVEYARD / DATA ONLY / NON-CANONICAL / NON-ACTIONABLE / NO AUTO-PROMOTION

# Forensic-реконструкция утраченного/невыделенного Раздела 2 KAT9I_OS

- Archive ID: `GY-20260910-section2-forensic-reconstruction-v1.0.0`
- Version: `1.0.0`
- Archive date: `2026-09-10`
- Project: `KAT9I_OS`
- Research canon snapshot: `d76bd056b317bbbcd786eea8357579b03dc7e238`
- Status: `DATA ONLY / FORENSIC RECONSTRUCTION`
- Purpose: сохранить доказательства, происхождение и реконструкцию обсуждения, из которого вырос невыделенный самостоятельным файлом Раздел 2.

> Этот файл не является архитектурным SSoT, не создаёт требований и не меняет принятые решения. При конфликте всегда побеждает актуальный канон проекта.

## 1. Маркировка происхождения

Каждый содержательный блок ниже относится к одному из классов:

- `EXACT` — содержание прямо подтверждено surviving GitHub artifact/commit/file/Issue/PR;
- `RECOVERED` — содержание восстановлено из сохранившегося индекса/сводки удалённого обсуждения, но исходный чат больше недоступен;
- `PREDECESSOR` — решение существовало в KAT9I/AG25/KAT9I_IIIJIIOXA непосредственно перед объединением в KAT9I_OS и является архитектурным предком, но не автоматически каноном KAT9I_OS;
- `INFERRED` — вывод по совокупности источников; не выдаётся за историческую цитату или принятое решение.

## 2. Основной surviving artifact

### [EXACT] Commit, сохранивший большую архитектурную дискуссию

Commit:
https://github.com/rassvetpublic-spec/KAT9I_OS/commit/18273a719749f8f9997ecdfe447cef60e53ba5ee

- SHA: `18273a719749f8f9997ecdfe447cef60e53ba5ee`
- Date: `2026-09-07T12:52:09Z`
- Message: `docs: add initial KAT9I OS architecture context`
- Added file: `docs/architecture/KAT9I_OS_ARCHITECTURE_CONTEXT.md`
- Size of initial addition: 1833 lines.

В самом diff commit зафиксировано, что документ является первоначальным архитектурным снимком, дистиллированным из обсуждения, начавшегося с предложения modular monolith.

Следовательно, этот commit — главный surviving GitHub artifact большой дискуссии до формализации отдельных разделов ТЗ.

### [EXACT] В этом artifact существует буквальный `## 2. Core`

Источник:
https://github.com/rassvetpublic-spec/KAT9I_OS/blob/18273a719749f8f9997ecdfe447cef60e53ba5ee/docs/architecture/KAT9I_OS_ARCHITECTURE_CONTEXT.md

В первоначальном architecture snapshot раздел 2 называется `Core`.

Core определён как generic control plane — универсальный управляющий контур.

Предлагаемая внутренняя структура Core:

- `tasks/`
- `contracts/`
- `rules/`
- `skills/`
- `routing/`
- `policy/`
- `learning/`

Прямо указанные ответственности Core:

- generic Task Contracts;
- Skill Registry;
- Skill Routing;
- Rule Manager;
- Effective Ruleset;
- policy conflict resolution;
- generic task/domain routing;
- governed learning/proposals;
- stable internal contracts.

Прямой архитектурный запрет: Domain-specific semantics не должны проникать в generic Core.

### [EXACT] Первоначальное разделение ответственности вокруг Core

В том же snapshot было зафиксировано смысловое разделение:

- Domain — что предметно нужно сделать;
- Core — какие rules/policies/contracts применяются;
- Context — что нужно знать для выполнения;
- Inference — какой интеллект/маршрут использовать;
- Coworker — кто выполняет;
- Execution — как физически выполнить;
- Integrations — взаимодействие с внешними системами;
- Personal — пользовательский слой;
- Resources — ссылки, артефакты и ресурсы.

Это показывает, что исторический Core уже задумывался не как «всё внутри ядра», а как управляющий слой между специализированными владельцами.

## 3. Временная шкала непосредственно перед Разделом 3

### [EXACT] Рождение репозитория и архитектурного snapshot

- `2026-09-07T12:27:41Z` — ранний commit `84b8fe10187650aa657ac2447970f31aaa2fb383`, первоначальная база репозитория;
- `2026-09-07T12:52:09Z` — `18273a7`, большой architecture snapshot с `## 2. Core`;
- `2026-09-07T13:30:51Z` — `87351bc...`, главная страница репозитория;
- `2026-09-07T14:01:05Z` — `ee8d553...`, отдельно фиксируется раздел Metrics/Telemetry;
- `2026-09-07T14:17:08Z` — `a58971b424eb70d651959a8e88836f22185d69d2`, отдельно фиксируется `03_TASK_CONTRACT.md`.

Commit §3:
https://github.com/rassvetpublic-spec/KAT9I_OS/commit/a58971b424eb70d651959a8e88836f22185d69d2

### [EXACT] До §3 не существовало KAT9I_OS Issue/PR-процесса в нынешнем виде

Первый Issue KAT9I_OS создан только `2026-09-07T17:54:50Z`, то есть более чем через 3,5 часа после commit §3.

Первый surviving PR KAT9I_OS создан вечером того же дня, уже после §3.

Следствие: большое обсуждение §2 непосредственно перед появлением §3 не могло находиться в KAT9I_OS Issues/PR, потому что этот процесс ещё не использовался. Тогда GitHub использовался прежде всего как место прямого сохранения архитектурных документов и контекста.

### [EXACT] Issue #2 — ложный след

GitHub Issue #2 KAT9I_OS относится к генератору HTML-документации и был создан после §3. Он не является «Разделом 2» и не должен использоваться как источник реконструкции §2.

Источник:
https://github.com/rassvetpublic-spec/KAT9I_OS/issues/2

## 4. Что architecture snapshot сохранил помимо короткого блока Core

### [EXACT] Progressive Disclosure и Skill Routing

В architecture snapshot присутствует более подробная цепочка:

`Task -> Domain Router -> Skill Router -> relevant skills only -> Tool Broker -> relevant tools only -> Context Compiler -> Worker`

Смысл:

- Worker не получает весь каталог Skills;
- Worker не получает весь каталог Tools;
- сначала выполняется маршрутизация и фильтрация;
- Context Compiler получает уже ограниченный набор релевантных ресурсов.

Это является прямым surviving evidence того, что `Skill Registry` и `Skill Routing` в коротком блоке Core были частью более широкой операционной модели, а не случайной строкой структуры каталогов.

### [EXACT] Reference-first вокруг задачи

В последующем §3 TaskContract прямо запрещено помещать весь репозиторий, весь чат, всю Knowledge, полный Skill catalog и всю Metrics history в сам контракт задачи.

Источник:
https://github.com/rassvetpublic-spec/KAT9I_OS/blob/main/docs/architecture/03_TASK_CONTRACT.md

Это согласуется с более ранней моделью Core и progressive disclosure: управляющие сущности должны ссылаться на контекст/навыки/правила, а не поглощать их полностью.

## 5. Восстановленный слой удалённого обсуждения

### [RECOVERED] Объединение KAT9I и AG25

По surviving conversation summary восстановлено, что 7 сентября непосредственно перед рождением KAT9I_OS обсуждалось объединение KAT9I и AG25 в один продукт.

В обсуждении существовала граница:

- KAT9I — policy/rules/capability/skill plane;
- AG25 — execution/orchestration plane;
- KAT9I_IIIJIIOXA — knowledge plane.

После обсуждения было принято рабочее направление `KAT9I_OS` как единого продукта.

Исходный удалённый чат больше не доступен как адресуемый artifact. Этот блок поэтому имеет статус `RECOVERED`, а не `EXACT`.

### [RECOVERED] Операционная модель KAT9I перед объединением

В удалённом обсуждении KAT9I описывалась как диспетчер policy/rules:

`request -> scope -> applicable rules -> conflict resolution -> Effective Ruleset -> prompt_hints + enforcement_plan -> Evidence`

Отдельно проговаривалось, что KAT9I в той модели не должен владеть запуском Worker, claim/lease/worktree и физическим исполнением — это относилось к AG25.

Это хорошо объясняет, почему после объединения в KAT9I_OS Core сохранил policy/contracts/routing, а Coworker/Execution получили отдельные зоны ответственности.

### [RECOVERED] Разделение фундаментальных сущностей

Непосредственно перед/вокруг рождения KAT9I_OS обсуждалось, что следующие сущности нельзя смешивать:

`Rule ≠ Skill ≠ Knowledge ≠ Workflow ≠ Contract ≠ Role/Profile ≠ State/Evidence`.

Смысл восстановленного решения:

- Rule — нормативное «надо / нельзя»;
- Skill — воспроизводимое «как выполнить»;
- Knowledge — «что известно»;
- Workflow — последовательность/граф работы;
- Contract — формализованная граница/обязательство взаимодействия;
- Role/Profile — субъектная конфигурация/роль;
- State — текущее состояние процесса;
- Evidence — доказательство факта выполнения/проверки.

Также восстанавливается принцип: одна семантическая сущность должна иметь одного канонического владельца, а остальные слои должны ссылаться на неё, а не создавать параллельные копии.

### [RECOVERED] Непосредственно перед commit §3 обсуждение ещё шло

Сохранившийся индекс разговора указывает, что примерно в `14:04 UTC`, около 13 минут до commit `a58971b` §3, продолжалось обсуждение целевой архитектуры разделения `Rules / Skills / Knowledge / Workflow / Contract / Profile / State` для связки AG25 + KAT9I + KAT9I_IIIJIIOXA.

Исходный текст разговора удалён, поэтому точные формулировки считать каноном нельзя. Но временная близость является сильным evidence, что formal TaskContract §3 появился сразу после этого пласта проектирования сущностей/ответственностей.

## 6. Предшественники в исходных репозиториях

### [PREDECESSOR] KAT9I Rule Manager Audit #107

Источник:
https://github.com/NewDeep67/kat9i_skills/issues/107

Audit comment:
https://github.com/NewDeep67/kat9i_skills/issues/107#issuecomment-5554991785

До создания KAT9I_OS была проведена инвентаризация instruction/policy pipeline.

Найдено:

- специализированная policy логика;
- Teamwork role/action/write policy;
- Issue -> bounded Teamwork brief;
- QA gate;
- legacy `.agent/rules/*`, где смешивались ENGINE-like invariants, PROJECT governance, USER-style preferences и workflow-поведение;
- `.agent/workflows/*` как отдельный workflow слой;
- отсутствие generic USER profile и generic Effective Ruleset.

Решение audit: Policy Resolution Layer должен выдавать:

1. Enforcement Plan;
2. Prompt Hints;
3. Resolution Metadata.

Machine-enforced ограничения должны оставаться вне prompt, если их можно детерминированно применять кодом.

WORKFLOW не должен становиться generic Rule type. CAPABILITY является observed runtime state, а не Rule.

### [PREDECESSOR] Rule Manager MVP #108

Источник:
https://github.com/NewDeep67/kat9i_skills/issues/108

До KAT9I_OS зафиксирована модель:

`ENGINE + USER + PROJECT + TASK -> deterministic Effective Ruleset`.

Требования:

- lower-level configuration не может ослаблять locked Engine invariant;
- Task scope не может расширять authoritative project/Issue constraints;
- User state остаётся local/external, а не product source;
- Task rules выводятся из текущей задачи и не создают второй persistent task store;
- Enforcement и prompt hints разделяются.

### [PREDECESSOR] Rule taxonomy #109

Источник:
https://github.com/NewDeep67/kat9i_skills/issues/109

До KAT9I_OS зафиксированы типы:

- `INVARIANT`;
- `CONSTRAINT`;
- `PREFERENCE`.

И отдельно:

- Rule type != Rule level/source;
- Capability — не Rule;
- Workflow — не generic Rule type;
- hard conflicts должны быть explicit/fail-closed.

### [PREDECESSOR] KAT9I ↔ AG25 bridge #118

Источник:
https://github.com/NewDeep67/kat9i_skills/issues/118

До появления KAT9I_OS была сформулирована граница:

`KAT9I Rule Manager -> Effective Ruleset -> AG25 task/worker adapter -> AG25 execution`

Запрещён вариант с независимым вторым generic Rule Manager в AG25.

KAT9I ownership:

- rule schema/taxonomy;
- conflict/override semantics;
- Effective Ruleset;
- Enforcement Plan vs Prompt Hints;
- rule provenance;
- user/project policy resolution.

AG25 ownership:

- Issue/task discovery;
- scheduling;
- atomic claim;
- worker selection/orchestration;
- worktree/branch lifecycle;
- process execution;
- runtime truth;
- cleanup/PR mechanics.

Knowledge repository отдельно запрещено использовать как Rule Registry/runtime truth.

### [PREDECESSOR] Skill routing до KAT9I_OS

Связанные commits:

- https://github.com/NewDeep67/KAT9I_IIIJIIOXA/commit/5c98102e674bf84a8d9bfb280b9022b80118fccc — трёхступенчатый routing trigger -> ondemand -> skill pool -> subagent;
- https://github.com/NewDeep67/KAT9I_IIIJIIOXA/commit/1012c0fe4b2ca76b8605e3e37949f0b9d2a03137 — skill-on-demand как единый skill router;
- https://github.com/NewDeep67/KAT9I_IIIJIIOXA/commit/4db89acf157af087f45356d0540b26a32f9ac5d2 — документирование skill router/concurrency pool;
- https://github.com/NewDeep67/kat9i_skills/commit/39b597dfab64e3279705bacdb5808b3adf105038 — Agent Skills standard, provenance sidecars и Routing v2.

Эти источники подтверждают, что тема Skill Registry/Skill Routing была активно проработана до KAT9I_OS. Но конкретные реализации исходных репозиториев не переносятся автоматически в новый канон.

### [PREDECESSOR] AG25 Federated Agent Platform

В историческом сохранённом ТЗ AG25 были отдельно определены:

- Control Plane;
- Task Contract;
- Runner Registry/Capabilities;
- Scheduler;
- claims/leases/fencing;
- task state/events;
- recovery;
- final gates;
- observability;
- Rule Resolver / Effective Policy Snapshot;
- Knowledge Plane;
- Evidence.

Task Contract включал goal/role/priority/dependencies/capabilities/scope/acceptance/tests/tools/prohibitions/base/timeouts/retry/knowledge refs/rule profile/required KAT9I skill/QA.

Rule Resolver должен был собирать Effective Policy Snapshot из разных уровней policy, причём lower-level rule не мог ослабить security invariant.

Knowledge отделялась от Control, а Evidence — от скрытого reasoning.

Этот документ является архитектурным предшественником, но не каноном KAT9I_OS. Его значение для forensic-реконструкции — показать, какие orchestration responsibilities существовали в AG25 до объединения и затем были перераспределены между Core/Coworker/Execution/Security/Recovery.

Artifact source: historical File Library record `AG25 Federated Agent Platform` (public URL отсутствует).

### [PREDECESSOR] AG25 Policy RFC #160

Источник:
https://github.com/rassvetpublic-spec/AG25/issues/160

Issue #160 фиксировал до KAT9I_OS:

- deterministic Control Plane;
- Task Contract;
- capability matching;
- atomic claim;
- isolated branch/worktree;
- scope guard;
- exact-head evidence;
- fail-closed state machine;
- предлагаемую модель `Effective Policy Snapshot = Enforcement Plan + Prompt Hints + Provenance + policy_hash`.

В Issue прямо сказано, что цель — не копировать KAT9I Rule Manager и не создавать второй executor/orchestrator.

## 7. Повторный поиск по KAT9I_OS: что проверено

### [EXACT] Surviving branches

На снимке `d76bd056b317bbbcd786eea8357579b03dc7e238` GitHub API перечислял 17 surviving branches:

1. `architecture/p0-bootstrap-qa-evidence`
2. `architecture/p0-portable-promotion-protocol`
3. `chore/issue-1-github-control-plane`
4. `docs/graveyard-bootstrap`
5. `docs/graveyard-pr86-cacheengine-audit`
6. `docs/issue-18-technology-stack`
7. `docs/issue-34-remove-duplicate-oq-refs`
8. `docs/p0-architecture-convergence-loop`
9. `docs/p0-cache-engine-architecture`
10. `feat/graveyard-pr-salvage-audit`
11. `feat/issue-84-cache-engine-architecture`
12. `fix/issue-37-38-ssot-traceability`
13. `fix/issue-99-graveyard-hardening`
14. `fix/issue-104-empty-project-items`
15. `fix/issue-106-malformed-item-url`
16. `main`
17. `test/issue-101-fail-closed-regressions`

Branch collection:
https://api.github.com/repos/rassvetpublic-spec/KAT9I_OS/branches?per_page=100

Все 17 surviving branches дополнительно проверены прямым чтением каталога `docs/tz/` на каждой ветке. На каждой ветке каталог содержал только `01-naznachenie-i-bazovaya-arhitektura.md` с одним и тем же blob SHA `de5700593a46f1336724eed376393f5602d3df28`. Отдельный `02_*`, альтернативный файл §2 или вторая версия `docs/tz` не обнаружены.

Проверенные ветки: `architecture/p0-bootstrap-qa-evidence`, `architecture/p0-portable-promotion-protocol`, `chore/issue-1-github-control-plane`, `docs/graveyard-bootstrap`, `docs/graveyard-pr86-cacheengine-audit`, `docs/issue-18-technology-stack`, `docs/issue-34-remove-duplicate-oq-refs`, `docs/p0-architecture-convergence-loop`, `docs/p0-cache-engine-architecture`, `feat/graveyard-pr-salvage-audit`, `feat/issue-84-cache-engine-architecture`, `fix/issue-37-38-ssot-traceability`, `fix/issue-99-graveyard-hardening`, `fix/issue-104-empty-project-items`, `fix/issue-106-malformed-item-url`, `main`, `test/issue-101-fail-closed-regressions`.

Search по именам веток `core`, `skill`, `rule`, `policy`, `tz` также не обнаружил surviving branch, созданной специально для старого §2.

Ограничение: полностью удалённая ветка без surviving PR/tag/ref GitHub API как branch уже не перечислит.

### [EXACT] Tags / Releases

- surviving `refs/tags/*` не обнаружены;
- GitHub Releases: пусто.

Следовательно, альтернативная копия §2 не сохранилась через tag/release.

### [EXACT] Issues — включая закрытые

Проверена коллекция Issues/PR state=all и отдельные searches `Core`, `Skill`, `TaskContract`.

Результат:

- нет раннего Issue, являющегося исходным §2;
- первый Issue создан после §3;
- более поздние Issues содержат развитие Core, но не являются первичным discussion artifact.

Особенно важно:

- Issue #2 = HTML generator, не §2;
- Issue #41 и PR #75 позже формализуют отдельный Rust Core Runtime/IPC;
- Issue #47 / PR #71 позже формализуют Module Registry и включают Core как самостоятельный модуль;
- Issue #10 / PR #21 позже создают карту архитектурной ответственности.

### [EXACT] Pull Requests — включая закрытые/merged

Проверены all-state PR и отдельный поиск `Core`.

Результат:

- PR до §3 отсутствуют;
- первый surviving PR появляется только вечером после §3;
- поздние PR дают evolution evidence, но не заменяют первичное обсуждение.

Особенно полезные поздние PR:

- PR #21 — карта ответственности модулей;
- PR #24 — Glossary с Rule Manager/Effective Ruleset/Inference Routing;
- PR #65 — перевод architecture context на русский с сохранением технической семантики;
- PR #71 — machine Module Registry;
- PR #75 — физический Rust Core Runtime и Electron IPC;
- PR #78 — deterministic vertical slice;
- PR #80 — Execution Semantic Snapshot;
- PR #81 — Workflow Versioning;
- PR #82 — Reproducible Evals.

PR #65 особенно важен: после появления детальных разделов проект продолжил поддерживать `KAT9I_OS_ARCHITECTURE_CONTEXT.md` как значимый архитектурный context artifact, а не удалил его как случайный черновик.

### [EXACT] Commit history вокруг §2/§3

Проверено временное окно перед §3 и ранняя история репозитория.

Не обнаружено commit, который создавал бы отдельный `docs/tz/02_*` или `docs/architecture/02_*` перед §3.

Обнаружена другая модель работы: сначала большой architecture snapshot, затем отдельное извлечение и принятие специализированных разделов.

### [EXACT] GitHub search по ключевым словам

Проверялись следы:

- `Core`;
- `Skill` / Skill Registry / Skill Router;
- `TaskContract`;
- Rule Manager;
- Effective Ruleset;
- routing/policy.

Search подтверждает наличие этих понятий в architecture snapshot и поздней архитектуре, но отдельный исходный файл §2 не обнаружен.

## 8. Forensic-реконструкция содержания §2

Ниже — не новый канон. Это карта того, что с разной уверенностью относится к исчезнувшему/невыделенному разделу.

### [EXACT] 2.A. Core как generic control plane

Core должен быть универсальным управляющим контуром, а не предметным модулем и не физическим исполнителем всех действий.

Источник: commit `18273a7`, `## 2. Core`.

### [EXACT] 2.B. Task/Contract coordination

Исторический Core включал `tasks/` и `contracts/`, generic Task Contracts и stable internal contracts.

Позже эти обязанности получили самостоятельные спецификации, прежде всего §3 TaskContract и §26 Internal Contracts.

### [EXACT] 2.C. Rules / Policy / Effective Ruleset

Исторический Core включал `rules/`, `policy/`, Rule Manager, Effective Ruleset и policy conflict resolution.

Позже Rule Manager получил отдельного канонического владельца, поэтому это не основание возвращать Rule semantics внутрь будущего §2.

### [EXACT] 2.D. Skill Registry и Skill Routing

Исторический Core прямо владел Skill Registry/Skill Routing на уровне исходного snapshot.

Отдельная chain progressive disclosure показывает, что routing Skills выполнялся до формирования Worker context.

### [RECOVERED] 2.E. Разделение типов сущностей

Большая дискуссия вокруг §2 различала Rule / Skill / Knowledge / Workflow / Contract / Profile/Role / State/Evidence.

Это объясняет архитектурную задачу раздела: не просто перечислить модули, а определить, какие типы объектов существуют и кто ими владеет.

### [PREDECESSOR] 2.F. Policy plane vs Execution plane

До объединения KAT9I владел policy/skills, AG25 — orchestration/execution. При создании KAT9I_OS это разделение не исчезло, а было перераспределено между Core, Rule Manager, Coworker, Execution, Security и другими модулями.

### [EXACT] 2.G. Generic Domain routing без Domain semantics

Исторический Core отвечал за generic task/domain routing, но Domain-specific semantics были запрещены внутри Core.

Это означает: Core может координировать вызов/результат Domain routing, но не становится владельцем предметной логики.

### [EXACT] 2.H. Governed Learning

Исторический Core включал `learning/` и governed learning/proposals.

Позже Learning получил отдельную архитектурную спецификацию. Поэтому будущий §2 должен лишь показывать место Learning в цикле управления, а не копировать его политику.

### [EXACT] 2.I. Progressive Disclosure

Полный каталог Skills/Tools не передаётся Worker. Отбор делается до Context Compiler/Worker.

Это одна из важных операционных функций исходной схемы и связь §2 с современной Context architecture.

### [RECOVERED] 2.J. Операционный цикл

По удалённому обсуждению и surviving architecture snapshot восстанавливается общий смысловой цикл:

`user goal/request -> scope/task -> applicable rules -> effective ruleset -> task/contract -> skill/domain routing -> bounded context/tools -> worker/execution -> validation/evidence -> result/state -> metrics/learning`

Точная историческая последовательность внутри этой реконструкции не считается доказанной. Современная последовательность должна браться из актуального §20.

### [INFERRED] 2.K. Раздел 2 был «зонтичным», а потом распался на SSoT

Совокупность evidence показывает наиболее вероятный процесс:

1. большая дискуссия сохранена единым architecture snapshot;
2. §2 Core в snapshot содержит широкий набор responsibilities;
3. затем последовательно появляются специализированные документы TaskContract, Rules, Metrics, Learning, Context, Knowledge, Resources, Inference, Coworker, Execution и т.д.;
4. отдельный `02_*` не материализуется;
5. позже Module Registry сужает Core до более чёткой coordinating responsibility.

Поэтому потерян, прежде всего, **контейнер/карта исходного раздела**, а не вся информация.

### [INFERRED] 2.L. Будущий §2 не должен возвращать старое широкое владение Core

Исторический snapshot важен для понимания происхождения, но современные SSoT уже распределили владение.

Восстанавливать §2 как копию старого широкого Core означало бы создать conflicts/duplicate SSoT.

Безопасный вариант — будущий §2 как архитектурная карта и operating model, которая ссылается на текущих канонических владельцев.

## 9. Что пока не восстановлено

### [EXACT] Не найден исходный самостоятельный файл `02_*`

Ни в current main, ни в 17 surviving branches отдельного `docs/tz/02_*` не найдено.

### [RECOVERED] Нет полного raw transcript удалённой дискуссии

Сохранились индексы/сводки и итоговый distilled architecture snapshot, но не полный адресуемый текст удалённого чата.

### [INFERRED] Точное историческое название полного раздела неизвестно

Буквально подтверждён только заголовок `## 2. Core` внутри architecture snapshot.

Любое расширенное русское название вроде «Core — управляющее ядро и операционная модель» является современной редакционной реконструкцией и должно быть отдельно согласовано.

### [INFERRED] Не доказана точная внутренняя нумерация 2.1...2.N

Содержательные темы восстанавливаются, но присваивать им исторические номера без источника нельзя.

## 10. Forensic verdict

### [EXACT]

- §2 как понятие `Core` существует в первоначальном architecture snapshot;
- snapshot был сохранён в GitHub до самостоятельного §3;
- отдельный `02_*` в surviving Git history/branches не найден;
- Issues/PR появились позже §3;
- поздний проект продолжал поддерживать architecture snapshot, а не выбросил его;
- большая часть исторических Core responsibilities позднее получила самостоятельных канонических владельцев.

### [RECOVERED]

- непосредственно до/вокруг рождения KAT9I_OS подробно обсуждалась сущностная модель Rules/Skills/Knowledge/Workflow/Contract/Profile/State/Evidence;
- обсуждалось объединение KAT9I policy/capability plane и AG25 orchestration/execution plane;
- это обсуждение продолжалось непосредственно перед commit §3.

### [PREDECESSOR]

- KAT9I Rule Manager, Effective Ruleset, Skill routing и AG25 Task Contract/Control Plane были реально проработаны до KAT9I_OS;
- они являются сильным источником происхождения, но не автоматическим современным каноном.

### [INFERRED]

Наиболее вероятный дефект процесса: при переходе `big design discussion -> architecture snapshot -> specialized SSoT sections` не был создан самостоятельный индексный/операционный документ §2. Из-за этого его обязанности сохранились распределённо, а сам смысловой контейнер исчез из `docs/tz/`.

## 11. Правило дальнейшей работы

Этот DATA archive разрешено использовать только как provenance/reference для обсуждения.

Он не разрешает автоматически:

- создавать `docs/tz/02-*`;
- менять §3/§4/§7/§10/§20/§27;
- создавать Issue/ADR/TaskContract;
- менять Module Registry;
- выполнять merge.

Переход от этой реконструкции к CONTROL допускается только после отдельной сверки с актуальным SSoT и явного решения владельца.
