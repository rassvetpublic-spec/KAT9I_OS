# QUEUE-GUARD Protocol

## Поток

`ROADMAP → READY → QUEUE → WORKER → QA (AGY) → QUEUED/WAIT MTD → MERGE → DONE`

Project показывает этот lifecycle, но не является отдельным SSoT.

## Перед передачей Worker

Обязательно:

- Issue существует;
- цель и Scope понятны;
- есть критерий готовности;
- назначен Implementation Worker;
- нет незакрытого blocking predecessor;
- нет конфликтующего active ChangeSet.

## Queue head и параллельность

- Promotion/merge сериализованы: следующий queue head не обгоняет predecessor.
- Параллельная подготовка разрешена для непересекающихся ChangeSet, но сама по себе не переводит задачу в promotion.
- Один конфликтующий ChangeSet одновременно изменяет только один Worker.
- Speculative/Draft работа остаётся вне активного promotion, пока QUEUE-GUARD явно не сделал её head.

## QA

QA выполняется отдельным Executor согласно `QA_PROTOCOL.md`.

`CI PASS`, `QA PASS`, `QA-ACCEPT`, `FAST-QA-PASS` и состояние `QUEUED` не являются merge authorization.

## Owner Gate

`mtd` / `MTD` / `мтд` используется один раз для конкретного promotion/merge и после использования считается потреблённым. Для следующего PR/merge нужен новый Owner Gate.

## Fail-closed

Если Worker, QA, Stage, Evidence, Head или состояние predecessor неоднозначны, система не угадывает значения и не двигает lifecycle.

## Terminal state

`DONE` допускается только по фактическому успешному outcome и read-back Evidence. Закрытие `not_planned`, unmerged PR или устаревшая Project-карточка не должны притворяться успешным release.
