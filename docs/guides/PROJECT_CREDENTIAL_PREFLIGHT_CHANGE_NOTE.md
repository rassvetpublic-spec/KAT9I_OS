# Issue #116 — change note

Основной `project_queue_sync.ps1` не является местом диагностики credential. Его proven lifecycle semantics из #117/#119 сохраняются без изменений.

Диагностика выполняется отдельным read-only `project_credential_preflight.ps1` перед реальным sync. Это отделяет проверку доступа от mutation-кода и не меняет порядок записи lifecycle-полей.

Если причина отказа не подтверждена однозначно, используется `PROJECT_SYNC_FAILED`, а не более точный код по догадке.
