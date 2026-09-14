# QA Envelope Standard

Этот файл не является самостоятельным QA-протоколом.

Канон:
- `QA_PROTOCOL.md` — единственный CONTROL-контракт `QA-COMMAND → QA-RESULT → QA-ACCEPT → bridge`;
- `WORKER_QA.md` — единственная точка входа и runtime/discovery/token policy для независимого QA Worker;
- `config/qa_worker.json` — machine-readable budget/polling policy.

QA обязан фиксировать exact HEAD, scope, risks/findings, verdict и Evidence в формате, определённом `QA_PROTOCOL.md`.

CI PASS не заменяет независимый QA. Context summary не может переопределять machine fields, EVIDENCE_EPOCH, Owner Gate или lifecycle.
