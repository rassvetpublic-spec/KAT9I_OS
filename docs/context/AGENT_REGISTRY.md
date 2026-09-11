# Agent Registry

## OWNER / Human

- принимает финальные решения;
- задаёт/меняет Scope и архитектурные Gate;
- выдаёт одноразовый `mtd` для конкретного merge.

## ChatGPT / Controller / Dispatcher

- эксперт по контексту и AI-operated systems;
- управляет QUEUE-GUARD;
- выбирает target и exact HEAD;
- принимает и проверяет Evidence;
- выпускает QA-COMMAND / QA-ACCEPT согласно `QA_PROTOCOL.md`;
- управляет lifecycle, но не подменяет независимый QA;
- безопасные обратимые действия выполняет автоматически в разрешённом Scope.

## Implementation Worker

Логическая роль исполнителя ChangeSet. Конкретным Worker может быть ChatGPT, Codex, человек или другой разрешённый исполнитель.

- имеет эксклюзивное mutation-право на claimed ChangeSet;
- не выполняет самоквалифицирующий QA;
- не создаёт параллельный дубль claimed работы.

## AGY / Antigravity / Антигравити / Agy

Одна логическая QA identity. Каноническое Project storage value: `AGY`.

В QA-профиле:

- независимо проверяет exact target;
- возвращает QA Evidence;
- не merge-ит;
- не меняет код;
- не управляет Project lifecycle;
- не пишет trusted FAST transitions.

Общий GitHub owner credential не является криптографическим доказательством личности AGY; это operational trust boundary до появления отдельной machine identity.

## Codex

Используется для анализа кода, автоматического review и выполнения задач, когда он явно назначен Worker. Сам факт Codex review не делает его квалифицирующим AGY QA.

## Research / Architect

Целевые специализированные роли дальнейшего Agent Registry. Их права и контракты развиваются в #146 и не должны подразумеваться до явного определения.

## Доноры

`AG25` и `NewDeep67/kat9i_skills` могут использоваться как доноры идей/паттернов. Они не являются агентами или источником истины KAT9I_OS.
