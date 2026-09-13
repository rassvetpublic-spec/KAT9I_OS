# Antigravity ONE: контракт Windows bootstrap

Статус: implementation contract для Issue #187. Документ не является разрешением на merge.

## Цель

Одна пользовательская точка входа:

```text
C:\Antigravity\ANTIGRAVITY.cmd
```

Bootstrap управляет установкой, проверкой, восстановлением и совместимым patch Antigravity. Профиль и рабочее состояние нельзя менять без проверенного backup.

## Порядок patch

1. Найти все копии standalone `resources\bin\language_server.exe` в каноническом каталоге, пользовательских и системных путях.
2. Заблокировать работу при запущенном Antigravity.
3. Для каждой копии отдельно определить версию, архитектуру, SHA-256 и состояние.
4. Native `Patch-Antigravity.ps1` — primary.
5. Разрешён только точный version/hash-bound контракт и ровно одна известная сигнатура.
6. Перед записью создать и проверить отдельный backup.
7. После записи проверить патч и сохранить receipt без credential/token material.
8. `Open_AG_Patcher` — fallback только по явной команде оператора; он не заменяет native primary.

Неизвестная версия, новая защита, неоднозначный путь или неизвестная сигнатура не исправляются эвристически.

## Автоматическая эскалация

При обнаружении новой/неизвестной версии bootstrap:

- завершает patch со статусом `PATCH_INCOMPATIBLE / BLOCKED`;
- создаёт или переиспользует открытую Issue в `rassvetpublic-spec/KAT9I_OS`;
- записывает путь, версию, SHA-256 и причину без секретов;
- формулирует задачу для первого свободного worker: сверить механизм защиты с upstream `AvenCores/open-antigravity-patcher`, добавить точный manifest и тесты.

Дубликаты открытых Issues не создаются.

## Команды

```text
ANTIGRAVITY.cmd status
ANTIGRAVITY.cmd install
ANTIGRAVITY.cmd repair
ANTIGRAVITY.cmd fallback
```

`fallback` требует явного выбора. Автоматический переход на внешний patcher запрещён.

## Граница состояния

Локальная реализация находится в `C:\Antigravity\_System` и не переносит credentials в репозиторий. Профиль Antigravity и данные Manager не являются частью этого документа и не должны коммититься.

## Acceptance criteria

- одна точка входа сохраняется;
- обнаруживаются все известные копии установки;
- каждая копия получает независимый backup и verify;
- неизвестное состояние блокируется и эскалируется в Issue;
- fallback запускается только явно;
- процесс обновления не работает поверх запущенного Antigravity;
- receipt/log не содержат токены или credentials;
- независимый QA и owner gate `mtd` обязательны перед merge.

## Текущее Evidence

- Issue: #187.
- Локальные файлы: `C:\Antigravity\ANTIGRAVITY.cmd`, `C:\Antigravity\_System\Antigravity-Control.ps1`, `C:\Antigravity\_System\Patch-Antigravity.ps1`.
- Подтверждённый путь установки на момент диагностики: `C:\Users\alexa\AppData\Local\Programs\antigravity\resources\bin\language_server.exe`.
- Проверка PowerShell-синтаксиса пройдена.
- Фактический patch не выполнялся поверх работающего процесса.
