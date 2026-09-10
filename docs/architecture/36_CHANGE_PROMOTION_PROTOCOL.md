# 36. Portable Promotion Protocol — безопасное продвижение изменений

## 36.1. Назначение

Portable Promotion Protocol — канонический механизм KAT9I_OS для безопасного продвижения уже подготовленного изменения в целевое состояние.

Главная абстракция — **Promotion**, а не GitHub Merge Queue и не конкретный Pull Request.

GitHub PR → `main` является первой рабочей вертикалью. Та же семантика должна переноситься на GitLab Merge Request, локальную Git-ветку, release branch и другой ResultSink через адаптеры.

Ключевой принцип:

> внешний QA проверяет ChangeSet; детерминированные проверки подтверждают интеграцию этого же ChangeSet с текущим target; Authorization Evidence разрешает точное финальное Promotion-действие.

Native platform queue может ускорять реализацию, но никогда не является обязательной частью Core-поведения.

## 36.2. Пользовательские команды

Команда `мерж` означает: создать или продолжить PromotionRequest и продвинуть его настолько далеко, насколько разрешает текущая policy.

Команда `mtd` / `MTD` / `мтд` означает: выдать Human Approval для **точного sealed PromotionTicket**, а не общее разрешение «слить этот PR когда-нибудь».

Служебные пользовательские команды будущего интерфейса:

- `очередь` — показать Promotion Queue и причины ожидания;
- `пауза` — не выдавать новые финальные кандидаты;
- `продолжить` — возобновить выдачу финальных кандидатов.

Эти команды являются UI-контрактом. Конкретный transport не является частью архитектурного инварианта.

## 36.3. Три независимых слоя Evidence

### Change Evidence

Доказывает приемлемость самого ChangeSet. Всегда хранит точную source revision как Provenance, ChangeSetDigest, Scope и Rules/Policy проверки.

Change Evidence не инвалидируется автоматически только из-за изменения target/base или нового эквивалентного SHA. Повторное использование определяется §23 через Impact Assessment и **не создаёт новый ChangeEvidence с переписанной source revision**: сохраняется ссылка на прежний immutable proof.

### Integration Evidence

Доказывает, что тот же проверенный ChangeSet совместим с конкретным target/candidate.

Сюда относятся merge/conflict check, tests, schemas, build, lint и другие детерминированные проверки точной комбинации checked change + current target.

Изменился target или candidate — Integration Evidence становится stale и пересчитывается. Это само по себе не означает новый FULL QA ChangeSet.

### Authorization Evidence

Доказывает право выполнить конкретное финальное действие.

Для Human Approval используется существующий `schemas/v1/ApprovalRecord.json`. Поле `ApprovalRecord.action_hash` равно `sha256:` + lowercase hex SHA-256 от UTF-8 JSON Canonicalization Scheme (RFC 8785) всего sealed PromotionTicket.

ApprovalRecord создаётся **после** seal ticket и поэтому не входит внутрь PromotionTicket: это исключает циклический hash. Ссылка на Authorization Evidence хранится в mutable PromotionRequest. Изменился PromotionTicket или истёк срок ApprovalRecord — прежнее `mtd` не действует.

## 36.4. ChangeSetDigest и Impact Assessment

Первичная идентичность изменения — детерминированный `ChangeSetDigest`, а не AI semantic fingerprint.

`ChangeSetDigest` вычисляется как SHA-256 нормализованного фактического набора изменений: paths, operations, normalized content changes и значимые deterministic metadata.

Оценка влияния отделена от идентичности и выполняется слоями:

1. L0 — Git paths и delta;
2. L1 — Module Registry, canonical ownership и contracts;
3. L2 — dependency/overlap graph и blast radius;
4. L3 — AI-анализ только при неоднозначности предыдущих уровней.

AI не определяет математическую идентичность ChangeSet и не может единолично понижать риск до SAFE.

## 36.5. Один Promotion Queue

KAT9I_OS имеет один логический Promotion Queue для target.

Не создаются отдельные очереди SAFE, SOLO, TEAM или TURBO. Эти свойства описываются policy и требованиями Evidence конкретного PromotionRequest.

Пример policy:

| Класс | Минимальное требование |
|---|---|
| SAFE | Integration Evidence + policy auto-authorization, если она явно включена |
| NORMAL | Change Evidence + Integration Evidence + Human Approval |
| STRICT | FULL Change Evidence + Integration Evidence + Human Approval |
| TEAM_STRICT | независимый review + FULL Change Evidence + Integration Evidence + Human Approval |

Авторство и identity агента влияют на policy, но не создают другой механизм Promotion.

## 36.6. SAFE

SAFE — только результат детерминированной allowlist-policy.

AI может повысить риск, но не является единственным источником разрешения SAFE. Неопределённость означает STRICT или BLOCKED.

SAFE не определяется расширением файла. `.md` не означает SAFE автоматически.

Всегда STRICT как минимум:

- архитектура;
- contracts/interfaces;
- schemas;
- Security;
- Rules/Policy;
- системный Context, prompts и agent rules;
- QA/Gate;
- permissions;
- `.github/workflows/**`;
- CI, scripts и dependencies;
- Promotion/merge policy;
- release/versioning;
- migrations;
- любое изменение с неопределённым влиянием.

SAFE может auto-promote только когда он является фактической головой очереди, построен свежий candidate для текущего target, все обязательные final checks зелёные и trusted gate не устарел.

## 36.7. Канонический жизненный цикл Promotion

Логический поток:

`INTENT → CLASSIFY → QUEUE → PRECHECK → CHANGE_VERIFIED → WAITING → HEAD → CANDIDATE_BUILD → INTEGRATION_VERIFIED → TICKET_SEALED → AUTO или mtd → COMMIT → VERIFY_COMMIT → DONE`.

Ошибки и неопределённость → `BLOCKED`.

Отмена → `CANCELLED`.

Изменился target → `CANDIDATE_STALE`, пересборка candidate и Integration Evidence.

Изменился ChangeSet → Impact Assessment → `QA_REUSE`, `DELTA_QA`, `FULL_QA` или `BLOCKED` согласно §23.

Подробное runtime-состояние PromotionRequest не должно перегружать TaskRuntimeState. PromotionRequest хранит ссылки на актуальные Change Evidence, Integration Evidence, sealed PromotionTicket и появившееся после seal Authorization Evidence; сами Evidence остаются отдельными объектами.

## 36.8. Change Freeze и Candidate Seal

Это два разных вида неизменяемости.

**Change Freeze** фиксирует то, что проверял содержательный QA, и позволяет переиспользовать Change Evidence.

**Candidate Seal** фиксирует фактическую финальную комбинацию checked change + target + evidence + policy + method + authorization.

Новый candidate не означает новый ChangeSet.

## 36.9. PromotionTicket

Перед финальным side effect формируется sealed `PromotionTicket`.

Он связывает как минимум:

- promotion_id;
- task_id;
- change_ref;
- change_digest;
- target_ref;
- target_revision;
- candidate_revision;
- risk_class;
- Change Evidence ref (`null` допустим только для SAFE согласно policy);
- Integration Evidence ref;
- Security Decision ref;
- `action_hash`;
- policy ref/version;
- promotion method;
- lease_generation;
- issued_at/expires_at.

`PromotionTicket.action_hash` вычисляется как `sha256:` + lowercase hex SHA-256 от RFC 8785 JCS-объекта с точными side-effect параметрами: `change_digest`, `target_ref`, `target_revision`, `candidate_revision`, `promotion_method`, `policy_ref`, `policy_version`, `lease_generation`. `SecurityDecision` с `operation = PROMOTE_CHANGE` обязан содержать тот же `action_hash`.

После `TICKET_SEALED` изменение любого поля делает прежний ticket недействительным и требует нового ticket. Reusable Change Evidence при этом сохраняется, если §23 считает его применимым. Human Approval создаётся поверх уже sealed ticket и связывается с hash **всего** ticket, а не только `action_hash`.

## 36.10. Promotion Lease и fencing

Новый mutex subsystem не создаётся.

Promotion переиспользует существующие Lease, `lease_generation`, fencing и Recovery semantics §21.

Инвариант:

> один target имеет не более одного активного владельца финального Promotion side effect.

Когда PromotionRequest становится HEAD, Core получает Promotion Lease для target. После смены generation старый executor не имеет права выполнить side effect даже если вернулся после сбоя.

GitHub Actions `concurrency` или аналог платформы может быть дополнительным mutex/safety belt, но не является FIFO SSoT очереди.

## 36.11. Atomic stale-candidate protection

Непосредственно перед физическим Promotion Execution повторно читает реальный target и проверяет:

- current target revision совпадает с `PromotionTicket.target_revision`;
- текущий ChangeSetDigest совпадает с ticket;
- candidate revision не изменился;
- policy и Evidence действительны;
- Security Decision действителен, имеет `operation = PROMOTE_CHANGE` и его `action_hash` совпадает с `PromotionTicket.action_hash`;
- Human Approval или policy auto-authorization действительны; для Human Approval `ApprovalRecord.action_hash` совпадает с SHA-256 RFC 8785 JCS всего sealed PromotionTicket;
- lease_generation является текущим.

При любом несовпадении действует Fail-Closed.

Если target изменился: `CANDIDATE_STALE`; side effect запрещён; строится новый candidate и новый Integration Evidence.

Если transport поддерживает CAS, expected-SHA или защиту non-fast-forward, она используется как последний atomic guard.

Нельзя сознательно продвигать candidate, отличный от финально проверенного.

## 36.12. Turbo

Turbo — speculative preparation scheduler, а не отдельный тип очереди и не ослабленная policy.

Пока HEAD ожидает дорогой QA или другое Evidence, следующие до трёх PromotionRequest могут выполнять дешёвую подготовку:

- CLASSIFY;
- PRECHECK;
- dependency/impact analysis;
- preliminary CI;
- подготовку Context/Evidence refs.

Turbo не может:

- менять target;
- получать финальный Promotion Lease;
- выполнять Promotion side effect;
- считать preliminary CI финальным Integration Evidence.

Параллельная подготовка разрешена. Параллельный финальный Promotion одного target запрещён.

## 36.13. QA merge barrier

Консервативная policy может включать `qa_merge_barrier` на время дорогого FULL QA: target временно не изменяется, SAFE ждут, а Turbo продолжает PRECHECK.

Это operational policy для снижения context drift и стоимости Impact Assessment, а не correctness invariant.

Архитектура остаётся корректной и при отключённом barrier: движение target не инвалидирует Change Evidence автоматически, но всегда инвалидирует старый Integration Evidence/candidate.

## 36.14. QA Delta Context

Для повторной проверки Context передаёт минимальный пакет:

`PreviousChangeEvidence + PreviousFindings + ChangedDelta + ImpactAssessment + AffectedContracts + QuestionToRevalidate`.

Не следует пересылать весь PR, весь repository или полный старый чат, если они не нужны для конкретного вывода.

Это применение Reference-first и Context Funnel §7.

## 36.15. QA economics

External FULL QA является ограниченным ресурсом времени, токенов и стоимости.

После ранее принятого PASS повторный FULL QA допускается только с machine-readable reason из §23.

Planning перед повторным FULL QA учитывает стоимость FULL QA и альтернативу Impact Assessment + DELTA QA.

Целевой показатель:

`QA Amplification Factor = FULL external QA runs / accepted change`.

Ориентир: около 1 для STRICT и 0 для SAFE.

## 36.16. Capability Negotiation

При подключении repository/platform Integration Adapter сообщает фактические technical capabilities отдельно от Security permissions.

Минимально полезные capability flags:

- read change;
- build synthetic candidate;
- read/run CI;
- auto promote/merge;
- CAS/expected-SHA atomic guard;
- native queue;
- rulesets/protection;
- reviews;
- write refs;
- workflow dispatch.

Core выбирает backend на основании capabilities, но safety semantics не меняются.

## 36.17. Graceful degradation

Отсутствующая capability не должна останавливать универсальный продукт и не должна ослаблять Gate.

Примеры:

- native queue доступен → optional acceleration backend;
- native queue отсутствует → KAT9I Promotion Queue + portable candidate;
- нет auto-merge permission → `READY_FOR_MANUAL_MERGE`;
- нет GitHub Actions → local Runner/CI adapter;
- нет API write → sealed verified PromotionTicket для ручного действия.

Personal GitHub account является поддерживаемой базовой средой. Organization и Enterprise не обязательны.

## 36.18. PromotionStore и SSoT

В каждый момент существует ровно один authoritative PromotionStore/QueueStore для конкретного target scope.

Предпочтительные backend:

- Desktop/local controller → SQLite;
- CI-only/unattended → dedicated Git ledger/ref с CAS/optimistic concurrency;
- native platform queue → optional backend/adapter, если он способен сохранить требуемые semantics.

GitHub Project является control plane и представлением, но не runtime SSoT очереди.

Переключение backend требует явной reconciliation/migration. Два равноправных SSoT запрещены.

## 36.19. Владение модулей

Новый top-level `MergeQueue` или `Promotion` supermodule не создаётся.

- Core — Promotion workflow, order и state orchestration;
- Rule Manager — classification и policy;
- Security — capability grants, SAFE auto-authorization policy и проверка Human Approval;
- QA — Change Evidence / QA Result и содержательная применимость verdict;
- Execution — candidate materialization и физический Promotion side effect;
- Integrations — GitHub/GitLab/local Git transport adapters;
- Storage — физический PromotionStore backend;
- Recovery — Lease/fencing/reconciliation/retry;
- Context — QA Delta Context;
- Metrics — Promotion/QA metrics;
- Planning — QA budget и cost decision.

Orchestration остаётся ответственностью Core согласно §27.

## 36.20. Машинные контракты

Минимальные новые схемы v1:

1. `PromotionRequest.json` — durable Promotion/queue state;
2. `ChangeEvidence.json` — структурированный QA proof конкретного ChangeSet;
3. `ImpactAssessment.json` — оценка применимости/влияния и решение REUSE/DELTA/FULL/BLOCKED;
4. `PromotionTicket.json` — sealed final bundle точного Promotion.

Переиспользуются:

- `Evidence.json` — техническое Evidence, включая Integration Evidence;
- `ApprovalRecord.json` — Human Approval (`mtd`);
- `SecurityDecision.json` — разрешение Security; версия 1.1 добавляет `PROMOTE_CHANGE` и обязательный для него `action_hash`;
- `JournalEvent.json` — audit/recovery events;
- `Checkpoint.json` — Recovery state.

Не создаются отдельные `MtdApproval`, `MergeSecurity` или `QueueEvidence`.

## 36.21. Journal и Recovery

Критические переходы Promotion фиксируются Event Journal.

Канонические event types включают:

- `PROMOTION_ENQUEUED`;
- `PROMOTION_CLASSIFIED`;
- `CHANGE_EVIDENCE_ACCEPTED`;
- `PROMOTION_HEAD_ACQUIRED`;
- `CANDIDATE_CREATED`;
- `INTEGRATION_PASSED`;
- `PROMOTION_TICKET_SEALED`;
- `PROMOTION_APPROVED`;
- `PROMOTION_COMMITTED`;
- `PROMOTION_BLOCKED`;
- `QA_REUSED`;
- `QA_INVALIDATED`;
- `DELTA_QA_REQUIRED`;
- `CANDIDATE_STALE`.

Recovery восстанавливает очередь и side-effect ownership из SSoT + Journal + Checkpoint + внешнего фактического состояния, а не из догадки модели.

## 36.22. Метрики

Минимальный архитектурный набор:

- `full_qa_runs`;
- `delta_qa_runs`;
- `qa_reuse_count`;
- `qa_reuse_rate`;
- `qa_invalidation_reason`;
- `saved_full_qa_runs`;
- `external_qa_tokens`;
- `external_qa_cost`;
- `queue_wait_time`;
- `candidate_rebuild_count`;
- `integration_retry_count`;
- `promotion_block_reason`;
- `promotion_lead_time`;
- `qa_amplification_factor`.

Обычный сбор и визуализация этих чисел не требуют LLM.

## 36.23. Системные инварианты

P1. Один target → максимум один активный Promotion Lease.

P2. SAFE не обходит фактическую голову Promotion Queue.

P3. FULL QA может включать временный merge barrier по policy, но barrier не является correctness invariant.

P4. Изменение target не инвалидирует Change Evidence автоматически.

P5. Изменение ChangeSet требует Impact Assessment.

P6. AI не может единолично понизить риск до SAFE.

P7. Promotion разрешён только по sealed PromotionTicket.

P8. Human Approval связывается с hash точного PromotionTicket.

P9. Target сравнивается непосредственно перед side effect.

P10. Старый executor блокируется fencing generation.

P11. Native platform feature не является обязательным для Core behavior.

P12. Missing capability вызывает safe degradation, а не rule bypass.

P13. Повторный FULL QA требует machine-readable reason.

P14. Promotion state имеет ровно один SSoT.

P15. Turbo ускоряет подготовку, но не нарушает serialized Promotion.

## 36.24. GitHub vertical

Для GitHub:

- ChangeRef обычно указывает на PR/head;
- target_ref обычно `main` или release branch;
- synthetic candidate строится из current target + checked ChangeSet;
- final CI выполняется на synthetic candidate;
- expected head SHA/CAS/non-fast-forward guard используется при возможности;
- native Merge Queue используется только как optional acceleration adapter.

GitHub Actions `concurrency` не является FIFO SSoT и не заменяет PromotionStore.

## 36.25. Что не входит в этот архитектурный этап

Этот раздел не реализует:

- GitHub Actions Promotion Bridge;
- GitHub App;
- runtime PromotionStore;
- реальный auto-merge;
- native Merge Queue integration;
- batch/multi-PR merge.

Следующий implementation PR должен dogfood этот протокол на GitHub Actions, сохраняя те же контракты и пользовательские команды.
