# Chat Context Migration — 2026-09-11

## Назначение

Evidence того, что перед удалением рабочего чата выполнен dedupe и уникальные операционные решения материализованы в GitHub.

## Уже было в GitHub до этой миграции

Не дублировалось повторно:

- независимый QA, exact revision, Change Evidence / Integration Evidence / Impact Assessment — `docs/spec/23_TESTING_QA_AND_READINESS.md`;
- Project как производное представление Issues/PR/Evidence и Owner Gate — `docs/spec/24_GITHUB_PROJECT_MANAGEMENT.md`;
- Controller ↔ AGY, QA-COMMAND, QA-RESULT, QA-ACCEPT, machine bridge, FOLLOW_UP_CANDIDATES, 40-секундный quiet window — `QA_PROTOCOL.md`;
- FAST-CLAIM, AGY default QA, русский язык, merge только по `mtd` — `AGENTS.md`;
- базовый roadmap FIFO/KPI/Agent Registry/Chat→GitHub — #146;
- Context Bridge / Drift Detector / Worker Handoff / Project UX — #147/#148/#149/#150;
- Evidence Epoch / Worker KPI / Pre-QA barrier / QA envelope hardening — #135/#136/#137/#145;
- восемь Project views как новая принятая цель — #150 / PR #153.

## Уникальное знание, материализованное этой миграцией

1. **Autonomy mode:** Worker делает безопасные обратимые шаги автоматически; владелец нужен только для доступа, конфликта правил, изменения Scope/Gate, destructive риска и `mtd`.
2. **Exclusive claim semantics:** один активный Worker мутирует claimed ChangeSet; другие могут анализировать, но не менять ветку и не создавать дубль той же работы.
3. **Parallel prep vs promotion:** непересекающиеся ChangeSet можно готовить параллельно, но promotion/merge сериализованы QUEUE-GUARD.
4. **Single-use mtd:** Owner Gate привязан к конкретному актуальному merge и не переносится на следующий PR/merge; уже выполненный merge не повторяется.
5. **Final merge CAS guard:** перед merge повторно читаются main/base/HEAD/CI/QA/threads/drift и используется expected-head guard.
6. **Idea/code donors:** AG25 и NewDeep67/kat9i_skills разрешены как доноры, но не как SSoT.
7. **Local Project v2 fallback:** если connector не экспонирует Project actions, используется локальный `gh` + GraphQL, audit-first, без передачи токена в чат/репозиторий.
8. **Stable Project locator:** KAT9I_OS Project number 2, node ID `PVT_kwHODnXDgM4Bi0YJ`; динамические item counts не канонизируются.
9. **Chat deletion rule:** уникальные Decision/Requirement/Follow-up сначала dedupe и materialize в GitHub, только затем рабочий чат можно считать необязательным для продолжения проекта.

## Не канонизировано намеренно

Не сохранялись как постоянные правила:

- временное имя конкретного чата/Worker (`Worker2` и подобные session labels);
- промежуточные SHA, уже находящиеся в PR/Actions Evidence;
- одноразовые очереди, которые уже superseded текущим GitHub state;
- токены, секреты и OAuth values;
- динамические counts Project items/fields как постоянная истина.

## Итог

После merge этого ChangeSet уникальный долговечный контекст данного чата будет представлен в GitHub. Сам чат не должен считаться SSoT.
