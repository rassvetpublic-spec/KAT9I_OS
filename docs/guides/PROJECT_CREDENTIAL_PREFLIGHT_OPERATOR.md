# Операторский порядок Project credential preflight

Этот файл дополняет `PROJECT_CREDENTIAL_PREFLIGHT.md` практическим порядком реакции.

1. Считать `KAT9I_PROJECT_PREFLIGHT=<CODE>` источником диагностического класса только для текущего запуска.
2. Не копировать credential, secret или token в Issue, PR, комментарии или логи.
3. Для `SECRET_MISSING` исправить передачу `KAT9I_PROJECT_TOKEN`; для `TOKEN_INVALID` заменить отклонённый credential; для access/write/schema кодов исправить соответствующее право или схему Project.
4. Для `PROJECT_SYNC_FAILED` сначала устранить API/runtime причину; не переклассифицировать её вручную без подтверждения.
5. После исправления повторить recovery/lifecycle sync и проверить фактическую карточку Project.

Preflight остаётся read-only. Реальный lifecycle write выполняет отдельный sync-контур, где `Статус` записывается последним.
