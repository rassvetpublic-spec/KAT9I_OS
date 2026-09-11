# GRAVEYARD / DATA ONLY / NON-CANONICAL / NON-ACTIONABLE / NO AUTO-PROMOTION

# Раздел 2 KAT9I_OS — согласованный рабочий DATA-снимок v1.1.0

- Archive ID: `GY-20260910-section2-working-agreement-v1.1.0`
- Version: `1.1.0`
- Archive date: `2026-09-10`
- Project: `KAT9I_OS`
- Status: `DATA ONLY / USER-AGREED WORKING TEXT`
- Canonical status: `NON-CANONICAL`
- Promotion: `FORBIDDEN WITHOUT SEPARATE CONTROL PROCESS`
- Base snapshot: `GY-20260910-section2-working-agreement-v1.0.0`
- Related forensic archive: `GY-20260910-section2-forensic-reconstruction-v1.0.0`
- Related projection archive: `GY-20260910-section2-modern-projection-v1.0.0`

> Версия 1.1.0 является immutable продолжением v1.0.0. Содержательно согласованные §2.1–§2.3 остаются в базовом snapshot без изменений; этот файл добавляет согласованный §2.4. Совокупный рабочий текст = v1.0.0 + v1.1.0. Документ остаётся DATA и не создаёт `docs/tz/02-*`.

## 2.4. Skills, Workflows и маршрутизация способа выполнения

KAT9I_OS должна разделять владение содержанием Skill или Workflow и общесистемный механизм их регистрации, обнаружения и выбора. Это разные архитектурные ответственности.

### 2.4.1. Skill

`Skill` отвечает на вопрос: **«Как воспроизводимо выполнить определённый тип работы?»**

Skill может содержать или ссылаться на:
- исполняемый код;
- алгоритм;
- модельную часть;
- необходимые Tools;
- требования к входу и результату;
- Validators и Tests;
- связанные Rules;
- необходимые Capability;
- версию и Provenance.

Skill не является Rule, Workflow, Worker или Permission.

Наличие Skill означает, что система знает определённый способ выполнения работы. Оно не означает, что этот способ разрешено использовать в конкретной задаче.

### 2.4.2. Владение содержанием Skill

Содержание Skill принадлежит тому модулю или Domain, который владеет соответствующей семантикой.

Например, предметный Skill музыкального анализа принадлежит музыкальному Domain. Системный Skill проверки JSON может принадлежать системному модулю, реализующему эту функцию.

Core не становится владельцем предметного содержания всех Skills.

### 2.4.3. Skill Registry

KAT9I_OS должна иметь один общесистемный `Skill Registry`.

Skill Registry является каталогом ссылок и метаданных о доступных Skills, но не вторым хранилищем их полного содержания.

Для каждого Skill Registry должен позволять определить как минимум:
- устойчивую идентичность Skill;
- версию или revision;
- канонического владельца;
- Domain или системный модуль;
- класс выполнения `CODE / HYBRID / MODEL`;
- входы и выходы;
- необходимые Tools и Capability;
- связанные Rules и Validators;
- статус и доступность;
- ссылку на каноническое определение.

Используется принцип **Reference-first**.

Skill Registry не копирует код, инструкции, Domain Knowledge и полный текст Skill, если они уже имеют канонического владельца.

### 2.4.4. Каноническое владение Skill Registry

Общесистемный Skill Registry относится к ответственности Core как системного координатора.

Это не означает, что Core владеет всеми Skills.

Разделение:

**Domain / системный модуль**
→ владеет содержанием Skill;

**Core / Skill Registry**
→ знает, какие Skills существуют и где находится их каноническое определение.

**Registry ownership ≠ Skill semantic ownership.**

### 2.4.5. Skill Routing

Skill Routing отвечает на вопрос: **«Какие из зарегистрированных Skills подходят для конкретного этапа этой задачи?»**

Маршрутизация выполняется на основании:
- TaskContract;
- активного Domain;
- Effective Ruleset;
- текущего узла TaskGraph;
- требуемого результата;
- доступных Resources;
- доступных Capability;
- совместимости версий;
- требований к качеству;
- ограничений Scope и Security.

Результатом первоначального поиска является один или несколько `SkillCandidate`.

### 2.4.6. SkillCandidate является DATA

`SkillCandidate` означает: **«этот Skill потенциально подходит для данного этапа»**.

Он не является Permission и не запускает Skill.

Путь:
`SkillCandidate` → `SkillSelection` → проверка Rules / Security / Capability / Scope → разрешённое выполнение.

`SkillSelection` является Decision о подходящем способе работы.

Но **Decision ≠ Permission**.

Даже выбранный Skill не может выполнить запрещённое действие.

### 2.4.7. Skill Routing не является Inference Routing

Skill Routing и Inference Routing решают разные задачи.

**Skill Routing:** «какой способ работы нужен?»

**Inference Routing:** «каким вычислительным или интеллектуальным маршрутом выполнить часть этой работы?»

Например Skill может быть `HYBRID`. Тогда его детерминированная часть выполняется кодом, а только оставшаяся интеллектуальная часть передаётся Inference.

Поэтому сначала определяется требуемая работа и подходящий Skill, а затем для тех частей Skill, которым действительно нужен интеллект, вызывается Inference.

Inference не является каталогом Skills. Skill Router не выбирает конкретную LLM-модель.

### 2.4.8. Executable-first внутри Skill

После выбора Skill система не должна автоматически обращаться к ИИ.

Каждый Skill рассматривается как композиция:
**детерминированная часть + остаточная интеллектуальная часть**.

Сначала выполняется всё, что можно надёжно выполнить исполняемым кодом или обычным инструментом. Только остаток передаётся Inference.

### 2.4.9. Workflow

`Workflow` отвечает на вопрос: **«В какой последовательности должны быть организованы несколько действий, Skills, решений или проверок?»**

Skill является повторно используемым способом выполнения отдельной работы. Workflow связывает несколько таких работ в процесс.

**Skill ≠ Workflow.**

Workflow может использовать несколько Skills. Один Skill может использоваться во множестве Workflows.

### 2.4.10. Владение Workflow

Предметное определение Workflow принадлежит Domain или системному модулю, владеющему соответствующим процессом.

Core не должен становиться владельцем содержания всех Workflows. Но Core отвечает за включение выбранного Workflow в общий жизненный цикл задачи.

### 2.4.11. Workflow и TaskGraph

Workflow и TaskGraph не являются одним объектом.

`Workflow` — повторно используемое определение процесса.

`TaskGraph` — конкретная runtime-структура конкретной задачи.

При необходимости выбранный Workflow используется как шаблон или источник структуры для построения части TaskGraph.

**WorkflowDefinition → конкретная задача → TaskGraph**, но не **Workflow = TaskGraph**.

TaskGraph может содержать этапы, которых не было в заранее определённом Workflow: Human Decision, Retry, Recovery, дополнительный QA, Context Request и другие runtime-ветви.

### 2.4.12. WorkflowCandidate

Как и Skill, Workflow сначала может быть обнаружен как кандидат.

`WorkflowCandidate` является DATA. Выбор Workflow является Decision. Сам выбор Workflow не выдаёт Permission на выполнение содержащихся в нём действий.

Каждый фактический side effect по-прежнему проходит действующие Rules, Security, Scope и необходимые разрешения.

### 2.4.13. Порядок маршрутизации

Для типового этапа задача проходит путь:

**Active Domain + TaskContract + Effective Ruleset**
→ определить применимый Workflow или построить TaskGraph без готового Workflow
→ определить требуемые Skills для узлов TaskGraph
→ получить `SkillCandidate`
→ выполнить `SkillSelection`
→ определить детерминированные и интеллектуальные части Skill
→ Executable-first
→ при необходимости Inference Route
→ Coworker выбирает конкретного Worker
→ Security подтверждает Permission для конкретного субъекта, действия и ресурса
→ Execution выполняет
→ Evidence и Validators подтверждают результат.

### 2.4.14. Progressive Disclosure

Worker не должен получать весь Skill Registry.

После Skill Routing ему передаются только:
- выбранные Skills;
- необходимые части Workflow;
- релевантные Tools;
- Effective Ruleset;
- минимальный Context;
- необходимые ResourceRefs.

Сам полный Registry остаётся системным механизмом Core.

### 2.4.15. Skill Registry не является Worker Registry

`Skill Registry` отвечает: **«какие способы работы существуют?»**

`Worker Registry` отвечает: **«какие исполнители существуют и что они способны выполнить?»**

Это разные реестры.

Связь возникает только при назначении:

**Skill requirements → required capabilities → Coworker → подходящий Worker.**

Нельзя выбирать Skill только потому, что конкретный Worker его умеет. И нельзя выбирать Worker до понимания того, какая работа и какие Capability действительно требуются.

### 2.4.16. Главные инварианты

1. Skill ≠ Workflow ≠ Worker.
2. SkillCandidate является DATA.
3. SkillSelection является Decision, но не Permission.
4. Наличие Capability не означает разрешение.
5. Skill Registry не владеет содержанием Skills.
6. Domain не создаёт отдельный общесистемный Skill Router.
7. Inference не является Skill Router.
8. Coworker не выбирает смысл Skill.
9. Execution не решает, какой Skill использовать.
10. Worker получает только необходимые Skills через Progressive Disclosure.
11. Повторяемая детерминируемая часть Skill должна стремиться к Executable-first.
12. Для каждой ответственности существует один канонический владелец.

## Зафиксированные последствия для будущей синхронизации

Эти пункты остаются DATA-кандидатами до отдельного CONTROL-процесса:

1. §27 потребуется уточнить: Core владеет generic Skill Registry / Skill Routing; Domain и системные модули владеют содержанием соответствующих Skills.
2. §20 потребуется уточнить место Workflow/Skill routing в lifecycle.
3. §4 остаётся владельцем принципов `CODE/HYBRID/MODEL`, Executable-first и Skill Compiler и не становится владельцем Skill Registry.
