# Project credential preflight

## Назначение

Перед записью lifecycle-состояния в GitHub Project #2 workflow выполняет отдельную read-only проверку credential, доступа, права записи и схемы Project. Проверка ничего не меняет в Project.

## Коды результата

| Код | Когда используется |
| --- | --- |
| `SECRET_MISSING` | `KAT9I_PROJECT_TOKEN` не передан в workflow. |
| `TOKEN_INVALID` | GitHub явно подтвердил отказ credential, например HTTP 401 / Bad credentials. |
| `PROJECT_ACCESS_DENIED` | Credential аутентифицирован, но чтение Project #2 явно запрещено или Project недоступен. |
| `PROJECT_WRITE_DENIED` | Project читается, но `viewerCanUpdate=false`. |
| `PROJECT_SCHEMA_MISMATCH` | Обязательное поле или option для требуемого lifecycle-состояния отсутствует либо неоднозначно. |
| `PROJECT_SYNC_FAILED` | Иной API/runtime failure или ошибка, которую нельзя безопасно классифицировать точнее. |

Успешная проверка выдаёт `KAT9I_PROJECT_PREFLIGHT=OK`.

## Правило fail-closed

Точный код ошибки ставится только при подтверждаемом сигнале. Сетевой сбой, timeout или неизвестная ошибка не должны называться `TOKEN_INVALID` или `PROJECT_ACCESS_DENIED`; для них используется `PROJECT_SYNC_FAILED`.

Preflight проверяет только чтением: наличие secret, аутентификацию GitHub, доступ к Project, `viewerCanUpdate`, существование карточки и необходимые field/option IDs. `project item-edit` в preflight запрещён.

## Безопасность

- значение secret/token никогда не печатается в logs или Evidence;
- `GITHUB_TOKEN` не используется как скрытый fallback для user Project #2;
- fork/untrusted context не должен получать secret path;
- реальная запись выполняется только после успешного preflight;
- в основном sync `Статус` остаётся последним commit-marker стадии.

## Восстановление

Исправить указанный credential/access/schema defect и повторить тот же lifecycle event или recovery sync. Preflight read-only, поэтому повторный запуск безопасен; основной Project sync остаётся идемпотентным по уже существующей карточке и значениям.
