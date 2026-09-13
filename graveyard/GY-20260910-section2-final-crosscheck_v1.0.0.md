# GRAVEYARD / DATA ONLY / NON-CANONICAL / NON-ACTIONABLE / NO AUTO-PROMOTION

# §2 KAT9I_OS — финальный cross-check после пользовательского согласования

- Archive ID: `GY-20260910-section2-final-crosscheck-v1.0.0`
- Version: `1.0.0`
- Archive date: `2026-09-10`
- Baseline main: `18c999fe99c5e799d7bc1119bc35a00fed9f07bc`
- Status: `DATA ONLY / CROSS-CHECK EVIDENCE`
- Canonical status: `NON-CANONICAL`
- Promotion: `FORBIDDEN WITHOUT SEPARATE CONTROL PROCESS`

## 1. Основание

Пользователь последовательно согласовал реконструированные блоки §2.1–§2.9. Источник согласованного текста — immutable DATA-снимки:

- `GY-20260910-section2-working-agreement-v1.0.0` — §2.1–§2.3;
- `GY-20260910-section2-working-agreement-v1.1.0` — §2.4;
- `GY-20260910-section2-working-agreement-v1.2.0` — §2.5–§2.6;
- `GY-20260910-section2-working-agreement-v1.3.0` — §2.7;
- `GY-20260910-section2-working-agreement-v1.4.0` — §2.8;
- `GY-20260910-section2-working-agreement-v1.5.0` — §2.9.

Историческое основание и provenance находятся в:

- `GY-20260910-section2-forensic-reconstruction-v1.0.0`;
- `GY-20260910-section2-modern-projection-v1.0.0`.

## 2. Проверенные текущие SSoT

Cross-check выполнен против текущих canonical owner documents на baseline main:

- `docs/architecture/03_TASK_CONTRACT.md` — blob `1512e4b7efad54ced4cc3dc5beb23735963830de`;
- `docs/architecture/04_RULES_AND_EXECUTION_PRIORITIES.md` — blob `d3996b017a8b3d3558c47910147b6752aa52e27d`;
- `docs/architecture/07_CONTEXT.md` — blob `494301b0a4b4f81cafc9edd76894cfad47cb8440`;
- `docs/architecture/10_INFERENCE_AND_DECISION_ROUTING_RU.md` — blob `130629276638da6d095cdffaa5db6b4f572f7d9f`;
- `docs/architecture/20_TASK_LIFECYCLE_AND_ORCHESTRATION.md` — blob `28bc09b8510b2fe254433a86ef432bbadd4d3320`;
- `docs/architecture/26_INTERNAL_CONTRACTS.md` — blob `8efdeb968e489dc505b7e6c3107467332e9b4114`;
- `docs/architecture/27_MODULE_REGISTRY_AND_RESPONSIBILITY_MAP.md` — blob `6697ff672c0b68334d39e551932b6e7f163d4b3e`.

## 3. Итог cross-check

### BLOCKER-1 — цикл Domain Rules / Domain selection

Текущий §20 задаёт порядок:

`Effective Ruleset → Domain → TaskContract`.

При этом §4 и §20 допускают Domain Rules как источник Effective Ruleset. Значит окончательный ruleset может зависеть от Domain, который формально определяется позже.

Согласованный §2 решает это двухфазно:

`DomainCandidate (DATA) → Effective Ruleset → Active Domain → TaskContract`.

**Требуемая canonical синхронизация:** изменить §20 так, чтобы preliminary Domain classification была явно отделена от Domain activation. Rule Manager должен иметь право использовать `DomainCandidate` для включения применимых Domain Rules, а `DomainCandidate` не должен давать Permission или активировать Domain.

### BLOCKER-2 — отсутствует канонический владелец общего Skill Registry / Skill Routing

Историческая модель Core прямо включала skill registry и skill routing.

Текущий §27 отдаёт Domain предметные `Workflow, Skills, Validators`, но не определяет владельца общесистемного каталога Skills и generic Skill Routing.

Согласованный §2 устанавливает границу:

- Domain / системный модуль владеет содержанием Skill;
- Core владеет общесистемным Skill Registry и generic Skill Routing;
- Registry хранит метаданные/ссылки, а не становится вторым хранилищем Skill;
- `SkillCandidate` — DATA;
- `SkillSelection` — Decision, но не Permission.

**Требуемая canonical синхронизация:** добавить эту ответственность в §27, сохранив предметное ownership Domain.

### BLOCKER-3 — в §20 отсутствует явная стадия Workflow/Skill routing

Текущий §20 после Context/Resources/Cache переходит к Executable-first и Inference. При этом согласованная модель различает:

`Workflow selection → TaskGraph → SkillCandidate → SkillSelection → Executable-first → Inference (только для недетерминированного остатка)`.

Без этого Inference визуально оказывается слишком ранним владельцем способа решения и сохраняется риск смешения `Skill Routing` и `Inference Routing`.

**Требуемая canonical синхронизация:** добавить в §20 явную стадию выбора применимого Workflow/Skills до Inference с сохранением Executable-first.

### ALIGN-1 — §3 TaskContract в целом совместим, нужна только синхронизация обзорной схемы

§3 уже разделяет TaskContract, TaskRuntimeState, TaskResult и TaskGraph; Rules передаются через RulesRef; Core описывает требуемые capabilities, а Coworker выбирает конкретного Worker. Это соответствует согласованному §2.

Но верхняя схема §3 показывает `Запрос → TaskContract` без предварительного Domain/rules resolution. Это допустимо только если диаграмма считается логическим overview, а не точным lifecycle.

**Рекомендованная синхронизация:** кратко уточнить, что финальный TaskContract формируется после разрешения Domain/Rules либо явно назвать ранний объект draft/intake form, если он нужен реализации.

### ALIGN-2 — §4 Rule Manager совместим

§4 уже закрепляет одного Rule Manager, Scope, deny-overrides-allow, Effective Ruleset, RulesRef, fail-closed и Executable-first. Это соответствует §2.

Нужно лишь связать Domain Rules с `DomainCandidate` после исправления §20; второй Rule Manager не создаётся.

### ALIGN-3 — §7 Context совместим

§7 уже задаёт minimal sufficient context, Reference-first, Context Funnel и Progressive Disclosure. Также прямо запрещает выдавать Worker весь каталог Skills/Tools/Rules.

Это соответствует §2.4/§2.7/§2.8. Изменение owner semantics не требуется.

### ALIGN-4 — §10 Inference совместим с уточнением границы

§10 владеет вычислительным/интеллектуальным маршрутом и прямо отделяет Inference от Coworker. Это соответствует §2.

**Рекомендованная синхронизация:** добавить одну явную boundary-фразу: Inference не владеет Skill Registry/Skill Routing и получает Inference Requirement после определения требуемого способа/Skill либо для конкретного узла TaskGraph.

### ALIGN-5 — §26 Contracts совместим

§26 уже разделяет Command, Query, Response, Event, Reference; CONTROL/DATA; TaskContract/TaskRuntimeState; Security Decision; Capability Grant; ResultRef/EvidenceRef; QA Result; Human Decision и versioned contracts.

§2.5 не должен копировать эти schemas — только объяснять operating relation. Изменение owner semantics не требуется.

### ALIGN-6 — §27 остаётся окончательной ownership map

Согласованный §2 не должен стать второй ownership map. §27 остаётся каноническим владельцем распределения архитектурной ответственности.

После решения BLOCKER-2 §2 обязан ссылаться на §27, а не конкурировать с ним.

## 4. Дополнительная wording-нормализация перед canonical §2

Это не меняет принятый пользователем смысл:

1. В формулировках о Events различать `Core инициирует/эмитит transition event` и `Telemetry владеет фиксацией наблюдаемой телеметрии`, чтобы Core не получил второй Telemetry ownership.
2. Security рассматривать как cross-cutting gate: preliminary policy/security constraints могут участвовать раньше, а конкретный side-effect Permission проверяется для выбранного subject/action/resource/scope перед Execution.
3. В §2 использовать краткие `SUMMARY + BOUNDARY + REFERENCE`; подробные списки полей и state machine оставлять в профильных SSoT.

## 5. Решение cross-check

Статус: **READY FOR SEPARATE CANONICAL RESTORATION ISSUE, WITH REQUIRED SYNCHRONIZATION**.

Прямого конфликта, который требует отказаться от восстановленного §2, не найдено.

Перед merge канонической реализации должны быть закрыты BLOCKER-1, BLOCKER-2 и BLOCKER-3 в одном согласованном ChangeSet либо в строго связанной очереди PR, чтобы main не оставался в промежуточно противоречивом состоянии.

## 6. QA

Для canonical restoration требуется независимый QA исполнителем **Antigravity** на exact head revision. Сам Implementation Worker не может засчитать собственную проверку как независимый QA.

Merge — только после требуемых gates и отдельной команды владельца `mtd/MTD/мтд`.
