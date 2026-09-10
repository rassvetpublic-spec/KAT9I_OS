# Project credential preflight — test matrix

Матрица является кратким указателем на regression suite Issue #116. Основной операторский контракт находится в `PROJECT_CREDENTIAL_PREFLIGHT.md`.

Проверяются: отсутствие secret, подтверждённый invalid credential, неопределённый auth/runtime failure, подтверждённый запрет Project read, отсутствие write capability, schema mismatch, generic Project runtime failure и позитивный read-only path. Для каждого failure до real sync не допускается Project mutation и утечка secret material.
