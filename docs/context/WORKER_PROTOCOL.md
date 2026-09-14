# Worker Protocol

Этот файл — короткая карта ролей. Он не определяет отдельный QA lifecycle.

- `WORKER` — implementation/execution role для одного активного ChangeSet.
- `WORKER QA` — специальная независимая QA role. Единственная точка входа: `/WORKER_QA.md`.
- `QA_PROTOCOL.md` — единственный CONTROL-протокол обмена Controller ↔ QA Executor.

Команда `WORKER QA` требует прочитать `WORKER_QA.md` и `QA_PROTOCOL.md`, зарегистрировать presence, перейти в `AUTO_LISTEN` и использовать deterministic polling 10 s без LLM-токенов в idle.

Implementation Worker не может считать свою проверку независимым QA. QA Worker не меняет проверяемый ChangeSet, не мержит и не управляет Project lifecycle.
