# KAT9I_OS Context SSOT

## Назначение
Этот документ сохраняет операционные знания проекта KAT9I_OS.

## Главный принцип
GitHub является источником истины (SSoT).
Чат используется для планирования, но знания должны переноситься в репозиторий.

## Модель ролей

- ChatGPT — архитектура, анализ, координация и Controller/Dispatcher.
- WORKER — выполнение ChangeSet.
- AGY (Antigravity) — независимый QA.
- Codex — анализ кода и ревью.
- Human — владелец mtd и финального разрешения.

## QA canonical routing

- `QA_PROTOCOL.md` — единственный CONTROL-протокол Controller ↔ QA Executor.
- `WORKER_QA.md` — единственная корневая точка входа для команды `WORKER QA` и runtime/discovery/token policy.
- `config/qa_worker.json` — machine-readable polling/token budget.
- Issue #171 — audit/history задачи, не runtime inbox.

## Правило mtd

Merge разрешается только после QA PASS и явной команды владельца проекта mtd.
