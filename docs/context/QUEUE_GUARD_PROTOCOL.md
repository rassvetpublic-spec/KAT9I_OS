# QUEUE-GUARD Protocol

Этот файл — навигационная проекция, а не второй scheduler/QA SSoT.

## Authority

- Promotion/queue semantics определяются действующим каноном KAT9I_OS и live GitHub state.
- QA CONTROL определяется только `QA_PROTOCOL.md`.
- QA Worker bootstrap/discovery/token policy определяется только `WORKER_QA.md` + `config/qa_worker.json`.

## Инварианты

- один Worker = один активный ChangeSet;
- Implementation Worker != независимый QA Worker;
- QA Worker не выбирает произвольный ChangeSet: он исполняет только latest authoritative owner `QA-COMMAND`;
- exact HEAD обязателен; stale/superseded command fail-closed;
- historical Issue/PR text, старые queue-head записи и discovery signals = DATA, они не переопределяют live queue state;
- QA PASS сам по себе не даёт merge authority;
- merge возможен только после всех required gates и свежего Owner Gate согласно канону.

Полный lifecycle и machine-readable детали не дублируются здесь во избежание drift.
