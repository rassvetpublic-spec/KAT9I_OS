# QUEUE-GUARD Protocol

## Поток

ROADMAP
↓
READY
↓
QUEUE
↓
WORKER
↓
WAITING_FOR_REQUIRED_CHECK
↓
PRE-QA BARRIER
↓
QA (AGY)
↓
MTD
↓
DONE

## Перед передачей WORKER

Обязательно:
- Issue существует;
- понятна цель;
- есть критерий готовности;
- назначен исполнитель;
- нет незакрытого блокера.

## Required-check gate

`WAITING_FOR_REQUIRED_CHECK` — отдельное машинное состояние после создания PR или изменения его HEAD и до допуска в независимый QA.

Инварианты:
- canonical required check: `Базовые проверки качества и целостности`;
- docs-only PR не освобождается от required check;
- `MISSING`, `PENDING`, `FAILED`, `STALE` не дают права на QA promotion;
- только `SUCCESS` на live exact HEAD пригоден как Quality Evidence;
- stale SUCCESS старого HEAD не равен SUCCESS текущего HEAD;
- read-only observer имеет только `DIAGNOSTIC_ONLY` authority;
- фактический допуск в QA выполняется PRE-QA barrier, а не Project-карточкой.

Project не является SSoT lifecycle. Пока безопасная миграция single-select option ID не нужна, `WAITING_FOR_REQUIRED_CHECK` отображается существующей проекцией `В работе / Активно / Частично`; точное machine-state и Evidence живут в Issue/PR/Actions.

## Правило

Один Worker = один активный ChangeSet.
Параллельные изменения одной области запрещены.
Promotion выполняется FIFO через QUEUE-GUARD; speculative подготовка более позднего ChangeSet не разрешает обгонять queue-head.
