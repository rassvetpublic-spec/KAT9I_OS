# Runtime Antigravity ONE

Этот каталог содержит переносимый Windows-runtime для Issue #187.

Единая пользовательская точка входа после установки:

```text
C:\Antigravity\ANTIGRAVITY.cmd
```

Команды:

```text
ANTIGRAVITY.cmd status
ANTIGRAVITY.cmd install
ANTIGRAVITY.cmd repair
ANTIGRAVITY.cmd fallback
```

`status` ничего не меняет в приложении или профиле и только пишет обезличенный локальный receipt.

`install` и `repair` сначала создают проверяемую резервную копию переносимого состояния, затем вызывают native patch engine. Неизвестная версия, SHA-256 или неоднозначная сигнатура дают `PATCH_INCOMPATIBLE / BLOCKED`; эвристический патч запрещён.

`fallback` — только явный ручной резервный сценарий. Он скачивает latest release `AvenCores/open-antigravity-patcher`, проверяет digest GitHub при наличии и после работы снова запускает native `status`.

Manifest совместимости разделяет байтовые signatures и разрешённые exact `product_version + architecture + source_sha256` строки. Новый hash остаётся заблокированным до review и обновления manifest.
