# KAT9I_OS Context SSOT

## Назначение
Этот документ сохраняет операционные знания проекта KAT9I_OS.

## Главный принцип
GitHub является источником истины (SSoT).
Чат используется для планирования, но знания должны переноситься в репозиторий.

## Модель ролей

- ChatGPT — архитектура, анализ, координация.
- WORKER — выполнение ChangeSet.
- AGY (Antigravity) — независимый QA.
- Codex — анализ кода и ревью.
- Human — владелец mtd и финального разрешения.

## Правило mtd

Merge разрешается только после QA PASS и явной команды владельца проекта mtd.

## Donor knowledge / code

Внешний donor никогда не становится вторым SSoT автоматически.
Любое заимствование проходит `DONOR_PROMOTION_PROTOCOL.md`: exact source pin, semantic diff, явная классификация каждого ценного элемента, KAT9I-native verification и сохранение более сильных действующих controls.

Machine-readable результаты donor-аудитов хранятся в `docs/context/donors/`. Для завершённой классификации обязательно `unclassified_count = 0`.
