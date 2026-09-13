# Runtime Antigravity ONE

Этот каталог содержит переносимый Windows-runtime для Issues #187 и #190.

Единая пользовательская точка входа после установки:

```text
C:\Antigravity\ANTIGRAVITY.cmd
```

Команды:

```text
ANTIGRAVITY.cmd status
ANTIGRAVITY.cmd dryrun
ANTIGRAVITY.cmd install
ANTIGRAVITY.cmd repair
ANTIGRAVITY.cmd fallback
```

`status` ничего не меняет в приложении или профиле и только пишет обезличенный локальный receipt.

`dryrun` — явный read-only alias к `status`: он проверяет discovery/compatibility и формирует диагностический receipt, но не запускает patch, fallback или state backup.

`install` и `repair` сначала создают проверяемую резервную копию переносимого состояния, затем вызывают native patch engine. Неизвестная версия, SHA-256 или неоднозначная сигнатура дают `PATCH_INCOMPATIBLE / BLOCKED`; эвристический патч запрещён.

`fallback` — только явный ручной резервный сценарий. Он скачивает latest release `AvenCores/open-antigravity-patcher`, проверяет digest GitHub при наличии и после работы снова запускает native `status`.

Manifest совместимости разделяет байтовые signatures и разрешённые exact `product_version + architecture + source_sha256` строки. Новый hash остаётся заблокированным до review и обновления manifest.

## Zero-state smoke

Windows CI устанавливает bootstrap в пустой временный root и проверяет fail-closed поведение: runtime-файлы должны установиться, отсутствие `language_server.exe` не должно считаться успехом, а `Standalone\Profile`, `_Manager\Data`, `_Manager\State` и `patch-state.json` не должны появляться. После этого CI запускает `dryrun` и повторно проверяет отсутствие mutation.

Этот smoke доказывает безопасность запуска с пустого bootstrap-root. Он не подменяет end-to-end smoke на реальной установленной версии Antigravity: такой запуск остаётся отдельным host evidence для полного acceptance #190.
