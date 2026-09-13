# GRAVEYARD / DATA ONLY / NON-CANONICAL / NON-ACTIONABLE / NO AUTO-PROMOTION

# Раздел 2 KAT9I_OS — согласованный рабочий DATA-снимок v1.2.0

- Archive ID: `GY-20260910-section2-working-agreement-v1.2.0`
- Version: `1.2.0`
- Archive date: `2026-09-10`
- Project: `KAT9I_OS`
- Status: `DATA ONLY / USER-AGREED WORKING TEXT`
- Canonical status: `NON-CANONICAL`
- Promotion: `FORBIDDEN WITHOUT SEPARATE CONTROL PROCESS`
- Base snapshot: `GY-20260910-section2-working-agreement-v1.1.0`
- Adds accepted sections: `§2.5`, `§2.6`

> Этот immutable DATA-снимок фиксирует принятые пользователем §2.5 и §2.6 поверх v1.1.0. Он не создаёт `docs/tz/02-*`, не меняет SSoT и не является разрешением на Issue/ADR/PR/merge.

## 2.5. Contracts, State, Evidence, Decision и переходы управления

Core связывает модули через типизированные контракты, состояние и проверяемые переходы.

Главный принцип:

**значимое управление системой должно быть представлено структурированной сущностью с известным типом, владельцем, версией, Scope и Provenance.**

Принятые инварианты:
1. `Contract ≠ State`.
2. `Command ≠ Event`.
3. `Result ≠ Evidence`.
4. `Evidence ≠ Decision`.
5. `Decision ≠ Permission`.
6. `Capability ≠ Permission`.
7. DATA не становится CONTROL через пересылку.
8. Свободный текст не заменяет обязательный Contract.
9. State transition требует структурированного основания.
10. Critical Gate работает fail-closed.
11. Один тип управляющего решения имеет одного канонического владельца.
12. Core координирует переход, но не подменяет владельца решения.

`TaskContract` отвечает, что должно быть сделано; `TaskRuntimeState` — что происходит сейчас.

Значимое межмодульное взаимодействие использует явные типы: Command, Query, Response, Event, Reference, Decision и State.

Command означает «сделай». Event означает «это уже произошло». Event не используется как скрытая команда.

Типовой переход:

**Current State → условия → Decisions → Permissions → действие → Evidence → Validation/QA → Event → Next State.**

`Result` отвечает «что получилось?». `Evidence` отвечает «чем доказано?». `Decision` фиксирует выбранный вывод. Evidence само по себе не выдаёт полномочий.

Каждый тип Decision имеет канонического владельца. Core получает структурированный Decision и использует его для перехода, но не создаёт альтернативное решение того же типа.

Capability отвечает, может ли субъект технически выполнить действие. Permission отвечает, разрешено ли выполнить его в конкретном Task/Scope/Resource/времени. Для фактического действия нужны обе стороны.

Gate — условие, которое должно быть доказано выполнено до перехода. Critical Gate не считается пройденным по текстовой декларации модели.

Контракты по возможности используют versioned References: RulesRef, ContextRef, KnowledgeRef, ResourceRef, ResultRef, EvidenceRef.

Prompt не должен быть единственным местом, где определены Scope, Permission, State, обязательные Rules, OutputContract, Lease, Security Decision или QA requirement.

**Core управляет графом разрешённых переходов между типизированными состояниями и владельцами.**

## 2.6. Границы Core и матрица владения

Core — системный координатор, но не универсальный владелец всех функций.

**Core может организовать действие, но не должен подменять канонического владельца решения или исполнения.**

Core самостоятельно владеет системной координацией Task, TaskContract, TaskGraph, TaskRuntimeState, допустимыми переходами lifecycle, передачей Contracts/References, проверкой обязательных Gate, общесистемным Skill Registry и generic Skill Routing.

Канонические владельцы профильных функций:
- Rule Manager — Rules, Effective Ruleset, RulesRef;
- Security — Security Decision и граница разрешений;
- Domain — предметная семантика, предметные Skills/Workflows/Validators/Domain Rules;
- Context — минимально достаточный рабочий контекст;
- Knowledge — подтверждённые знания и Provenance;
- Resources — логическая модель ресурсов;
- CacheEngine — Cache Policy;
- Planning & Forecasting — оценки ресурсов;
- Inference — вычислительный/интеллектуальный маршрут;
- Coworker — Worker Registry, выбор Worker, Claim/Lease;
- Execution — физическое выполнение и технические Evidence;
- Integrations — транспорт и внешние адаптеры;
- QA — независимый verdict;
- Recovery — безопасное восстановление;
- Telemetry — факты произошедшего;
- Metrics — оценка эффективности;
- Learning — предложения улучшения;
- Personal Layer — пользовательская специфика.

Core не создаёт параллельные реализации этих решений.

`Registry ownership ≠ Skill semantic ownership`: Core владеет общесистемным Skill Registry и generic Skill Routing, но содержание предметных Skills остаётся у Domain/профильного модуля.

Core не переопределяет решения канонических владельцев. Допустимы только предусмотренные Escalation, Human Decision, Recovery или новое официальное Decision.

Escalation не является обходом. Security DENY нельзя обойти сменой Worker, Provider или Skill.

**One owner → many references / many clients.**

Архитектурная ответственность не означает обязательное размещение всей логики в одном физическом Rust binary/process; Runtime и Deployment определяются отдельно.

Core не имеет права:
- создавать второй Rule Manager;
- хранить всю Knowledge;
- выполнять Domain semantics;
- выбирать Provider вместо Inference;
- выбирать Worker вместо Coworker;
- выдавать Permission вместо Security;
- выполнять side effects вместо Execution;
- объявлять QA PASS вместо QA;
- считать DATA управляющей инструкцией;
- обходить BLOCKED;
- скрыто расширять Scope;
- считать Capability разрешением;
- автоматически применять высокоуровневые Learning changes;
- превращать Graveyard в CONTROL;
- подменять типизированный Contract свободным prompt;
- считать отсутствие Evidence доказательством успеха.

**Core — канонический координатор системного жизненного цикла, который связывает Task, State, Contracts, Decisions, References и Gates между специализированными владельцами ответственности.**

Главный инвариант:

**Координация не даёт владение. Владение не даёт Permission. Capability не даёт Permission. Decision одного модуля не может быть тихо переопределён другим модулем того же уровня ответственности.**
