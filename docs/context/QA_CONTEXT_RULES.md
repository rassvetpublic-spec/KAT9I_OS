# QA Context Rules

## QA_CONTEXT

`QA_CONTEXT = PR_HEAD + BASE_REFERENCE`

QA Worker рассматривает открытый PR как отдельный рабочий контекст до merge.

- PR_HEAD — текущая ветка и commit SHA проверяемого PR.
- BASE_REFERENCE — базовая ветка для сравнения и оценки diff.

## Поиск файлов

Если QA-COMMAND ссылается на файл, которого нет в BASE_REFERENCE, Worker обязан искать его в PR_HEAD.

Отсутствие файла в base не является ошибкой само по себе, если файл создаётся или изменяется текущим PR.

## Base drift

Перед final gate Worker обязан проверить base drift.

Если базовая ветка изменилась после формирования проверенного контекста:

1. текущий exact HEAD считается требующим повторной проверки;
2. старый QA verdict не переносится автоматически;
3. требуется новый exact-head validation перед merge.

## Приоритет проверки

QA проверяет diff PR относительно BASE_REFERENCE, а не состояние base-ветки как готового продукта.
