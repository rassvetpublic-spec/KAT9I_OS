# Project Operating Model

## Каноническая граница

GitHub Project — control-plane (панель управления) и визуализация, но не отдельный источник истины состояния работы.

- состояние работы: Issues / PR / Evidence;
- архитектура и правила: `docs/`;
- автоматические проверки: GitHub Actions;
- Project: производное удобное представление этих данных.

При рассинхронизации Project восстанавливается из GitHub SSoT, а не наоборот.

## Операционная модель

- Queue — сериализация продвижения работы через QUEUE-GUARD;
- Worker — исполнитель ChangeSet;
- QA — независимый контроль качества;
- Controller — проверка Evidence и lifecycle transition;
- Owner Gate `mtd` — отдельное разрешение merge;
- Merge — изменение репозитория, а не синоним QA PASS/Gate PASS;
- DONE — terminal state только после фактического outcome и read-back.

## Mutations Project

Project mutation должна быть:

1. предварительно проверена fail-closed;
2. привязана к конкретной Issue/PR/событию;
3. выполнена без угадывания неизвестных полей/ролей;
4. подтверждена read-back Evidence.

Частичный write/read-back failure считается ошибкой, а не успешной синхронизацией.

## UX

Текущее развитие представлений, Board и card layout отслеживается в #150. Принятая цель восьми специализированных views реализуется через PR #153; до его merge каноном остаётся default branch.

Project UX не меняет QUEUE-GUARD, независимый QA или правило `mtd`.
