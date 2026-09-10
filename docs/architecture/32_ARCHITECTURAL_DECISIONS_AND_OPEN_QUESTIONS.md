# 32. Архитектурные решения, допущения и открытые вопросы KAT9I_OS

## 32.1. Назначение

Этот раздел является реестром архитектурных решений KAT9I_OS.

Он отвечает на три вопроса:

1. **Что уже принято и не должно обсуждаться заново без явной причины?**
2. **Что пока является выбором конкретной реализации?**
3. **Какие вопросы действительно ещё не закрыты?**

Главный принцип:

> **не путать принятое архитектурное решение с временной реализацией и не выдавать нерешённый вопрос за уже утверждённую архитектуру.**

## 32.2. Это не второй источник истины

Подробное определение решения остаётся в соответствующем каноническом разделе.

Раздел 32 хранит:

- идентификатор;
- краткую формулировку;
- статус;
- ссылку на канонический раздел;
- причину;
- последствия;
- условия пересмотра.

Например:

> Electron является основным UI.

Подробности находятся в разделе 29.

Раздел 32 не копирует весь раздел 29.

## 32.3. Типы записей

Каждая запись относится к одному типу.

### DECISION — решение

Архитектурное решение принято.

### ASSUMPTION — допущение

Сейчас считаем это верным, но требуется подтверждение практикой.

### IMPLEMENTATION CHOICE — выбор реализации

Архитектура определяет обязанность, но конкретная технология ещё может быть заменена.

### OPEN QUESTION — открытый вопрос

Решение ещё не принято.

### DEFERRED — отложено

Решение сознательно не требуется текущему этапу.

## 32.4. Статусы

Предлагаются:

- `ACCEPTED` — принято;
- `PROVISIONAL` — предварительно;
- `OPEN` — требует решения;
- `DEFERRED` — отложено;
- `SUPERSEDED` — заменено новым решением;
- `REJECTED` — вариант рассмотрен и отклонён.

## 32.5. Принятое нельзя менять молча

Если принятое решение меняется:

старое решение получает:

`SUPERSEDED`.

Новое решение получает собственную запись.

Должно быть понятно:

- что изменилось;
- почему;
- каким решением заменено;
- какие разделы затронуты.

## 32.6. Architecture Decision Record — запись архитектурного решения

Для значимых решений используется сокращённый ADR:

`Architecture Decision Record — запись архитектурного решения`.

Минимальные поля:

- ADR ID;
- название;
- статус;
- дата;
- контекст;
- принятое решение;
- причины;
- последствия;
- альтернативы;
- затронутые разделы;
- условия пересмотра.

## 32.7. Не создавать ADR на каждую мелочь

ADR нужен для решений, которые:

- влияют на несколько модулей;
- трудно изменить позднее;
- влияют на Security;
- определяют системную границу;
- определяют SSoT;
- определяют протокол;
- определяют основной технологический стек.

Цвет кнопки ADR не требует.

## 32.8. Уже принятые фундаментальные решения

Следующие решения считаются архитектурно принятыми.

## 32.9. ADR-001 — Executable-first

**Статус:** ACCEPTED.

> Повторяемые, формализуемые и проверяемые операции должны по возможности переходить из модельной логики в исполняемый код.

Приоритет:

`MODEL → HYBRID → CODE`.

ИИ используется там, где остаётся содержательная неопределённость.

## 32.10. ADR-002 — Local-first

**Статус:** ACCEPTED.

При прочих равных приоритет:

1. локальный исполняемый код;
2. локальный алгоритм;
3. локальный ИИ;
4. уже оплаченная подписка;
5. тарифицируемый внешний API.

Security и обязательное качество имеют больший приоритет.

## 32.11. ADR-003 — Reference-first

**Статус:** ACCEPTED.

Большие данные по возможности передаются:

> ссылками и идентификаторами,

а не копируются между модулями и Workers.

## 32.12. ADR-004 — Evidence-first

**Статус:** ACCEPTED.

Утверждение Worker или модели:

> «я выполнил задачу»

не является доказательством.

Исполнение подтверждается Evidence.

## 32.13. ADR-005 — один источник истины

**Статус:** ACCEPTED.

Для каждой системной сущности должен существовать один канонический владелец.

Кэш, индекс, HTML, Electron и локальная копия могут быть представлениями, но не конкурирующими SSoT.

## 32.14. ADR-006 — CONTROL и DATA разделены

**Статус:** ACCEPTED.

Внешнее содержимое остаётся DATA.

Оно не может само повысить себя до CONTROL.

## 32.15. ADR-007 — Rule Manager один

**Статус:** ACCEPTED.

В системе существует единый Rule Manager.

Другие модули не реализуют собственную параллельную систему обязательных правил.

## 32.16. ADR-008 — deny wins

**Статус:** ACCEPTED.

Применимый обязательный запрет имеет приоритет над разрешением.

Неоднозначность критического обязательного правила приводит к BLOCKED.

## 32.17. ADR-009 — независимый QA

**Статус:** SUPERSEDED by ADR-045.

Сохраняется исторически принятое требование независимости: Worker, реализовавший изменение, не выполняет квалифицирующий независимый QA собственного изменения.

Старая универсальная формулировка «изменение revision делает старый QA неактуальным» заменена ADR-045, потому что она смешивала Provenance проверки с решением о необходимости повторного содержательного QA.

## 32.17a. ADR-045 — применимость QA Evidence после изменения revision

**Статус:** ACCEPTED.

QA Evidence всегда хранит точную `source revision` как Provenance и проверенный ChangeSet. Изменение SHA/rebase/target само по себе не является достаточным основанием для повторного FULL QA.

После изменения система проверяет ChangeSet, значимые Rules/Policy, Scope, новый Evidence и Impact Assessment и выбирает `QA REUSE`, `DELTA QA`, `FULL QA` или `BLOCKED` согласно каноническому §23 и §20.34. Если изменился только target/base, пересчитывается Integration Evidence; Change Evidence не инвалидируется автоматически.

`INDETERMINATE` не разрешает QA REUSE. Независимость квалифицирующего DELTA/FULL QA сохраняется: Implementation Worker != QA Worker там, где policy требует независимую проверку.

**Причина пересмотра:** уменьшить повторный дорогой QA без ослабления Fail-Closed и без слепого переноса PASS на новую revision.

**Затронутые каноны:** §23, §20.34, §11.25, `docs/spec/13_CACHE_POLICY.md`, `docs/spec/24_GITHUB_PROJECT_MANAGEMENT.md`, §27.17.

## 32.18. ADR-010 — GitHub Issue является SSoT работы проекта

**Статус:** ACCEPTED.

Для разработки KAT9I_OS:

- Issue — состояние работы;
- PR — конкретное предлагаемое изменение;
- Actions — Evidence;
- Project — представление;
- Milestone — группировка;
- Release — выпущенная версия.

## 32.19. ADR-011 — Markdown является SSoT документации

**Статус:** ACCEPTED.

Канонические Markdown-документы являются источником архитектурной документации.

Electron Docs и GitHub Pages строятся из них.

Ручная параллельная HTML-копия не является допустимым источником истины.

## 32.20. ADR-012 — Electron является основным пользовательским интерфейсом

**Статус:** ACCEPTED.

KAT9I_OS является настольным приложением на Electron.

В Electron находятся:

- визуализация;
- задачи;
- настройки;
- документация;
- Knowledge UI;
- диагностика;
- Learning UI;
- onboarding.

Electron не заменяет Core.

## 32.21. ADR-013 — UI не имеет обходного системного доступа

**Статус:** ACCEPTED.

Renderer работает через ограниченный Preload/API/IPC.

Управляющий путь:

> Electron → Identity → Rules → Security → Core → соответствующий модуль.

Renderer не получает универсальный Shell или прямой доступ ко всей БД.

## 32.22. ADR-014 — Windows 11 является первой целевой системой

**Статус:** ACCEPTED.

Первая полноценная пользовательская реализация ориентирована на Windows 11.

Внутренние контракты при этом не должны искусственно становиться Windows-only.

## 32.23. ADR-015 — SQLite как первое структурированное локальное хранилище

**Статус:** ACCEPTED как выбор первой реализации.

SQLite используется как основное структурированное локальное хранилище первой версии.

Но архитектурные модули работают через интерфейсы Storage.

SQLite не является вечным обязательным архитектурным контрактом.

## 32.24. ADR-016 — код и пользовательское состояние разделены

**Статус:** ACCEPTED.

Git-репозиторий KAT9I_OS и пользовательское состояние физически разделены.

Переустановка или обновление кода не должно уничтожать состояние пользователя.

## 32.25. ADR-017 — секреты хранятся отдельно

**Статус:** ACCEPTED.

Системные модули используют `SecretRef`.

Секреты не помещаются в:

- Git;
- TaskContract;
- Knowledge;
- Logs;
- обычный Cache;
- HTML;
- Telegram.

## 32.26. ADR-018 — один Primary Node первой версии

**Статус:** ACCEPTED.

Первая распределённая архитектура имеет один канонический Primary Node.

Другие компьютеры подключаются как Workers.

Не реализуется ранний распределённый Consensus между несколькими равноправными Core.

## 32.27. ADR-019 — один компьютер является полноценной KAT9I_OS

**Статус:** ACCEPTED.

Удалённая инфраструктура не является обязательной для MVP.

KAT9I_OS должна полноценно работать на одном Windows 11 компьютере.

## 32.28. ADR-020 — Workers работают через контракты

**Статус:** ACCEPTED.

Worker не получает прямой доступ ко всей SQLite, Knowledge Base или Secret Store.

Он получает минимально необходимые:

- TaskContract;
- Context;
- ResourceRef;
- Capability Grant;
- Lease.

## 32.29. ADR-021 — Lease + generation + fencing

**Статус:** ACCEPTED.

Для изменяющей операции только одно поколение Lease имеет право совершить побочный эффект.

Старый Worker после переназначения не может законно опубликовать результат.

## 32.30. ADR-022 — Git используется как система версий кода

**Статус:** ACCEPTED.

KAT9I_OS не создаёт собственный параллельный механизм версионирования репозитория.

Используются:

- commit;
- branch;
- tag;
- worktree;
- diff.

## 32.31. ADR-023 — отдельный Git Worktree для изменяющего Worker

**Статус:** ACCEPTED как основной подход.

Параллельные изменения изолируются через ветки и Worktree.

Это снижает риск загрязнения общей рабочей директории.

## 32.32. ADR-024 — первая рабочая вертикаль через GitHub

**Статус:** ACCEPTED.

Первый главный dogfood:

> Issue → TaskContract → Worker → branch/worktree → implementation → tests → PR → independent QA → Merge → Metrics.

## 32.33. ADR-025 — Learning не является условием корректности

**Статус:** ACCEPTED.

Система должна корректно работать с выключенным Learning.

Learning улучшает уже работающий механизм.

## 32.34. ADR-026 — Cache не является условием корректности

**Статус:** ACCEPTED.

Полное удаление Cache может сделать работу:

- медленнее;
- дороже;

но не должно менять правильность результата.

## 32.35. ADR-027 — Recovery опирается на проверенное состояние

**Статус:** ACCEPTED.

Recovery использует:

- Task State;
- Checkpoint;
- Event Journal;
- Evidence;
- фактическое внешнее состояние.

Не:

> догадку LLM.

## 32.36. ADR-028 — прогнозирование выполняется до расхода ресурсов

**Статус:** ACCEPTED.

Для значимой задачи используются:

- preliminary estimate;
- refined estimate;
- rolling estimate;
- forecast vs actual.

## 32.37. ADR-029 — обычная Telemetry и Visualization не требуют LLM

**Статус:** ACCEPTED.

Нормальное отображение:

- задач;
- графиков;
- Metrics;
- статусов;
- Replay;

строится программным кодом с примерно нулевым дополнительным расходом LLM.

## 32.38. ADR-030 — Telegram не является внутренней шиной Workers

**Статус:** ACCEPTED.

Telegram — внешний человеческий канал:

- команды;
- решения;
- уведомления;
- вопросы;
- ResultSink.

Не внутренний Worker Bus.

## 32.39. ADR-031 — Obsidian не является обязательным Core-компонентом

**Статус:** ACCEPTED.

Obsidian может быть:

- внешним Knowledge Store;
- человеческим Markdown-интерфейсом.

При его отсутствии Core продолжает работу.

## 32.40. ADR-032 — один владелец архитектурной ответственности

**Статус:** ACCEPTED.

Каждая верхнеуровневая ответственность имеет одного канонического владельца.

Несколько модулей могут участвовать в процессе, но не конкурируют за одну семантику.

## 32.40a. ADR-034 — канонический формат машинных контрактов и каталог схем

**Статус:** ACCEPTED (канонический источник: [schemas/README.md](../../schemas/README.md), `schemas/v1/`, Issue #40).

1. В качестве канонического формата машинных контрактов KAT9I_OS принят **JSON Schema (Draft 2020-12)**.
2. Единым физическим каталогом SSoT схем зафиксирован каталог `schemas/v1/`.
3. Все контракты обязаны содержать инвариант безопасности `additionalProperties: false` (Fail-Closed).
4. Версионирование схем осуществляется по SemVer 2.0.0; неизвестные мажорные версии вызывают немедленный отказ `INCOMPATIBLE_SCHEMA_VERSION`.

## 32.40b. ADR-035 — машинная структура Module Registry и правила графа зависимостей

**Статус:** ACCEPTED (канонический источник: `schemas/v1/ModuleRegistry.json`, `modules_registry.json`, `scripts/verify_module_registry.py`, Issue #47).

1. Реестр модулей KAT9I_OS описывается строго машинно через каноническую схему `schemas/v1/ModuleRegistry.json` (JSON Schema Draft 2020-12).
2. Реестр не дублирует текстовые архитектурные спецификации, а ссылается на канонический источник ответственности (`docs/architecture/27_MODULE_REGISTRY_AND_RESPONSIBILITY_MAP.md`).
3. Граф зависимостей между модулями обязан быть направленным ациклическим графом (DAG). Наличие циклов (`CIRCULAR_DEPENDENCY_DETECTED`) является фатальной ошибкой инициализации.
4. Каждый модуль обязан иметь уникальную каноническую ответственность в соответствии с инвариантом ADR-032.
5. Любой требуемый контракт (`requires_contracts`) должен обеспечиваться хотя бы одним зарегистрированным модулем (`provides_contracts`).

## 32.40c. ADR-036 — модель Identity, роли субъектов и безопасная привязка к Windows

**Статус:** ACCEPTED (канонический источник: `schemas/v1/Identity.json`, `schemas/v1/ApprovalRecord.json`, `docs/spec/14_SECURITY.md`, `tests/test_identity_security.py`, Issue #44).

1. **Разделение сущностей безопасности**:
   - `Identity` (`identity_id` вида `id-...`): кто субъект;
   - `Role`: логическая роль в системе (`LOCAL_USER`, `LOCAL_ADMIN`, `WORKER`, `CORE_SERVICE`, `NODE_OPERATOR`, `AUDITOR`);
   - `Trust Level`: уровень доверия (`UNTRUSTED`, `PROVISIONAL`, `AUTHENTICATED`, `FULL_LOCAL_TRUST`);
   - `Capability`: временный мандат на исполнение конкретных действий (`CapabilityGrant.json`).
2. **Привязка к Windows без хранения паролей**:
   - Категорически запрещено сохранение любых паролей или хэшей паролей Windows (NTLM/LM);
   - Субъекты связываются через канонический Windows SID (`security_identifier`) и криптографический `account_hash` (соль машины);
   - Роль `LOCAL_USER` и `LOCAL_ADMIN` строго разделены: получение `LOCAL_ADMIN` требует подтверждённого административного токена Windows (`is_elevated=true`);
   - При смене или удалении учетной записи Windows сессии и временные права немедленно отзываются (`Fail-Closed`).
3. **Защита Human Approval от Replay-атак**:
   - Человеческое подтверждение описывается канонической схемой `schemas/v1/ApprovalRecord.json`;
   - Запись обязана содержать `approval_id`, `approver_identity_id`, `approver_role`, `task_id`, `action_hash`, криптографический `nonce` (длиной не менее 16 символов), метки `issued_at` и `expires_at`;
   - Воркеры (`WORKER`) или внешние сервисы не могут генерировать или подписывать Human Approval.

## 32.40d. ADR-037 — Event Journal, Checkpoint и правила Replay Recovery

**Статус:** ACCEPTED (канонический источник: `schemas/v1/JournalEvent.json`, `schemas/v1/Checkpoint.json`, `docs/architecture/21_RELIABILITY_AND_RECOVERY.md`, `tests/test_journal_recovery.py`, Issue #46).

1. **Машинный контракт append-only Event Journal**:
   - Журнал критических событий является строго append-only и описывается схемой `schemas/v1/JournalEvent.json`;
   - Каждое событие имеет строго монотонный `sequence_number` (начиная с 1);
   - Обязательный перечень событий v0.1: переходы жизненного цикла задач (`TASK_CREATED`, `TASK_STATUS_CHANGED`, `TASK_COMPLETED`, `TASK_FAILED`, `TASK_CANCELLED`), управление Lease (`LEASE_ACQUIRED`, `LEASE_EXPIRED`, `LEASE_REVOKED`), внешние действия (`SIDE_EFFECT_PLANNED`, `SIDE_EFFECT_EXECUTED`), события безопасности (`SECURITY_VIOLATION_DETECTED`, `CAPABILITY_GRANTED`, `CAPABILITY_REVOKED`, `APPROVAL_RECORDED`) и фиксация контрольных точек (`CHECKPOINT_COMMITTED`).
2. **Контрольные точки (Checkpoint)**:
   - Контрольная точка описывается схемой `schemas/v1/Checkpoint.json` и связывается с `last_sequence_number`;
   - Включает моментальный снимок согласованного `runtime_state`, перечень выполненных `operation_id`, активное поколение владения `active_lease_generation` и ссылки на подтвержденные артефакты.
3. **Replay Recovery и защита от дублирующих побочных действий**:
   - Восстановление после сбоя или перезапуска всегда стартует с последней подтвержденной контрольной точки Checkpoint с доигрыванием последующих событий журнала;
   - Защита от повтора внешних изменяющих действий (идемпотентность): если `operation_id` уже зафиксирован в чекпоинте или журнале с подтвержденным Evidence, повторная отправка блокируется (`SKIP_ALREADY_EXECUTED`);
   - Защита от зомби-воркеров (Fencing Token): события от устаревшего поколения владения (`lease_generation < current_lease_generation`) безусловно отклоняются;
   - Срок хранения (Retention): события активных задач хранятся непрерывно, завершенных — минимум 30 суток для аудита.

## 32.40e. ADR-038 — физическая граница Core Runtime и безопасный IPC с Electron

**Статус:** ACCEPTED (канонический источник: `schemas/v1/CoreIpcMessage.json`, `scripts/core_ipc_prototype.py`, `tests/test_core_ipc_boundary.py`, Issue #41).

1. **Физическая изоляция Core Runtime (Вариант B)**:
   - Системное ядро KAT9I_OS функционирует как **отдельный локальный процесс** (Rust Core Runtime), физически независимый от Electron Main и Renderer.
   - Сбой, закрытие или перезапуск Electron не уничтожает состояние активных задач (Zero Task Disruption).
   - Поддерживается нативный автономный фоновый режим (Headless Mode).
2. **Локальный транспорт и сессионная аутентификация**:
   - В качестве локального транспорта выбран Loopback IPC (TCP / локальный именованный канал Windows на `127.0.0.1`);
   - Подключение защищено локальным сессионным токеном `auth_token`, генерируемым ядром при запуске. Любое неавторизованное подключение немедленно отклоняется (`ACCESS_DENIED`).
3. **Узкий типизированный контракт (Narrow API Surface)**:
   - Обмен строго регламентирован схемой `schemas/v1/CoreIpcMessage.json` (JSON Schema Draft 2020-12);
   - Разрешённый набор методов: `core.ping`, `core.get_system_state`, `core.create_task`, `core.cancel_task`, `core.subscribe_events`;
   - Строгий запрет произвольного выполнения shell/eval: любой неизвестный или недоверенный метод вызывает ошибку `METHOD_NOT_ALLOWED`;
   - Задержка IPC на Windows 11 не превышает единиц миллисекунд (< 5 мс).
4. **Reconnect и синхронизация состояния**:
   - При перезапуске интерфейса или обрыве связи новый клиент Electron восстанавливает сессию и мгновенно считывает актуальное состояние ядра через `core.get_system_state`, возобновляя получение системных событий через `core.subscribe_events`.

## 32.40f. ADR-039 — реализация Windows Secret Store и модель SecretRef

**Статус:** ACCEPTED (канонический источник: `schemas/v1/SecretRef.json`, `scripts/windows_secret_store.py`, `tests/test_secret_store.py`, Issue #45).

1. **Базовый криптографический механизм для Windows 11**:
   - В качестве базового механизма защиты секретов на Windows 11 утверждён **Windows Data Protection API (DPAPI / CryptProtectData)** с опциональной интеграцией Windows Credential Manager.
   - Секреты шифруются с привязкой к учётной записи пользователя Windows (`USER_LOCAL`). Перенос зашифрованного файла на другую машину или запуск от другого пользователя делает расшифровку невозможной (`Fail-Closed`).
2. **Модель SecretRef**:
   - Значения секретов категорически запрещены к размещению в TaskContract, Knowledge Base, журнале событий Event Journal, кэше или обычном состоянии;
   - Задачи и модули оперируют только ссылкой `SecretRef` (`schemas/v1/SecretRef.json`, поля: `secret_id`, `name`, `provider`, `scope`, `created_at`);
   - Доступ к значению секрета разрешён строго в момент выполнения операции и только при наличии действующего мандата `CapabilityGrant` с возможностью `SECRET_READ_SCOPED`.
3. **Безопасность и предотвращение утечек**:
   - Неавторизованные исполнители или сторонние процессы получают немедленный отказ `PermissionError` (Security Scope Guard);
   - Индексы и метаданные хранилища не содержат секретных значений;
   - Предусмотрена процедура мгновенного отзыва (`revoke_secret`) с безопасной перезаписью блоба нулями;
   - Резервное копирование (Backup) секретов: ключи шифруются аппаратно или привязываются к мастер-паролю пользователя, перенос в незашифрованном виде запрещён.

## 32.40g. ADR-040 — стандарт сквозной трассировки (TraceContext, SpanKind, OpenTelemetry)

**Статус:** ACCEPTED (канонический источник: `schemas/v1/TraceContext.json`, `scripts/tracer.py`, `tests/test_trace_standard.py`, Issue #50).

1. **W3C TraceContext и совместимость с OpenTelemetry**:
   - В качестве стандарта идентификации трасс принят W3C TraceContext: `trace_id` (16 байт / 32 hex) и `span_id` (8 байт / 16 hex).
   - Поддерживается иерархическая вложенность через `parent_span_id`, позволяющая восстановить полный граф выполнения: `Task → Worker → Model/Tool → Result → QA`.
   - Предусмотрен канонический экспорт в OTLP JSON (`ResourceSpans`), совместимый с Jaeger, Tempo, SigNoz и OpenTelemetry Collector.
2. **Канонические типы этапов (SpanKind)**:
   - Введены строго типизированные категории спанов: `CORE`, `SECURITY_DECISION`, `CONTEXT_PREPARATION`, `MODEL_CALL`, `TOOL_CALL`, `WORKER_EXECUTION`, `EXTERNAL_INTEGRATION`, `QA`, `STORAGE`, `RECOVERY`.
3. **Безопасность и Zero Leak в телеметрии**:
   - Трассировка категорически не должна содержать секретов, паролей, токенов и скрытых рассуждений модели (Fail-Closed фильтрация атрибутов).
   - Trace показывает путь выполнения и временную шкалу, а Evidence подтверждает факт результата.
4. **Производительность и накладные расходы**:
   - Накладные расходы на формирование, атрибутирование и закрытие одного спана составляют единицы миллисекунд (< 1.5 мс с полной валидацией по схеме и < 0.05 мс в памяти), что не создает заметной нагрузки на runtime.

## 32.40h. ADR-041 — снимок семантического окружения выполнения (Execution Semantic Snapshot) и семантическая изоляция возобновления

**Статус:** ACCEPTED (канонический источник: [docs/architecture/21_RELIABILITY_AND_RECOVERY.md](21_RELIABILITY_AND_RECOVERY.md), `schemas/v1/SemanticSnapshot.json`, `scripts/semantic_isolation.py`, `tests/test_semantic_isolation.py`, Issue #42).

1. **Проблема неявного семантического дрейфа**:
   - Традиционные контрольные точки (Checkpoint) сохраняют только переменные и статус задачи, что недостаточно для длительных AI-workflow.
   - Изменение версии модели (тихий alias drift), системного промпта, системных правил (`RulesRef`), схем инструментов или индекса контекста между началом, паузой и возобновлением приводит к скрытой потере воспроизводимости.
2. **Модель Execution Semantic Snapshot (`schemas/v1/SemanticSnapshot.json`)**:
   - В соответствии с принципом `Reference-first` снимок фиксирует идентификаторы, версии и хэши значимых ресурсов (без дублирования тяжелых данных):
     * `rules_ref`;
     * `model_route` (`provider`, `model_alias`, `resolved_model_version`, `prompt_template_revision`);
     * `context_manifest_ref`;
     * `skill_revisions`;
     * `tool_definitions` (схемы инструментов / MCP серверов);
     * `config_revision` и `contract_versions`.
3. **Политика Resume Preflight и Fail-Closed защита**:
   - Перед возобновлением задачи компонент `SemanticIsolationGuard` сопоставляет базовый снимок с текущим окружением.
   - Критический дрейф (`BREAKING_DRIFT`: смена версии модели, изменение `RulesRef`, удаление/изменение схем инструментов) блокирует продолжение задачи (`RESUME_BLOCKED` / `SemanticDriftError`), предотвращая скрытые искажения результатов.
   - Задача переводится в статус `BLOCKED` с требованием повторного планирования или ручного подтверждения оператором.

## 32.40i. ADR-042 — версионирование Workflow и детерминированная миграция длительных задач (StateMigration)

**Статус:** ACCEPTED (канонический источник: [docs/architecture/30_VERSIONING_RELEASES_AND_LIFECYCLE.md](30_VERSIONING_RELEASES_AND_LIFECYCLE.md), `schemas/v1/StateMigration.json`, `scripts/workflow_migration.py`, `tests/test_workflow_migration.py`, Issue #52).

1. **Идентификация и версионирование процессов**:
   - Каждая длительная задача обязана содержать точные `workflow_id` и `workflow_version` (SemVer) в своем состоянии выполнения.
2. **Классификация изменений структуры графа**:
   - `FULLY_COMPATIBLE`: минорные обновления, не меняющие схему состояния и граф; продолжение задачи без модификации полей.
   - `REQUIRES_STATE_MIGRATION`: совместимое расширение схемы переменных или шагов. Применяется зарегистрированный версионированный мигратор состояния (`WorkflowMigrationEngine`).
   - `BREAKING_INCOMPATIBLE`: мажорное удаление шагов или изменение семантики без явного пути миграции. В соответствии с принципом `Fail-Closed` задача блокируется (`BLOCKED` / `WorkflowIncompatibleError`), исключая скрытое искажение логики выполнения.
3. **Идемпотентность и доказательства (Evidence-first)**:
   - Миграции состояния строго идемпотентны: повторное применение возвращает `SKIPPED_IDEMPOTENT` без повторного изменения полей.
   - Каждая операция миграции фиксируется машинным контрактом `StateMigration.json` и связывается с аудиторским Evidence.

## 32.40j. ADR-043 — систематические оценки (Evals) и регрессионный анализ агентного поведения

**Статус:** ACCEPTED (канонический источник: [docs/spec/23_TESTING_QA_AND_READINESS.md](../spec/23_TESTING_QA_AND_READINESS.md), `schemas/v1/EvalSuite.json`, `scripts/eval_runner.py`, `tests/test_evals_regression.py`, Issue #51).

1. **Разделение независимого QA и систематических Evals**:
   - QA подтверждает корректность отдельного коммита/PR перед слиянием.
   - Evals систематически оценивает поведение агентов во времени на неизменном наборе воспроизводимых сценариев (`EvalSuite` / `EvalCase`).
2. **Многоуровневая верификация (детерминированная + поведенческая)**:
   - В первую очередь оцениваются детерминированные инварианты (соблюдение Scope, создание веток/PR, валидность выходных контрактов).
   - Строгий контроль запрещенных действий (`forbidden_actions`: прямой push в `main`, самовольный Self-QA, исполнение несанкционированных команд).
   - Качественная оценка исключает использование тестируемой модели в роли судьи без изолированного арбитража.
3. **Регрессионный контроль (Regression Report)**:
   - Изменение модели, системных промптов или навыков принимается только при отсутствии деградации на базовом наборе сценариев.
   - Любое ухудшение ранее работавшего сценария порождает статус `REGRESSION_DETECTED` и блокирует признание обновления успешным.

## 32.40k. ADR-046 — Portable Promotion Protocol

**Статус:** ACCEPTED (канонический источник: `docs/architecture/36_CHANGE_PROMOTION_PROTOCOL.md`, `schemas/v1/PromotionRequest.json`, `schemas/v1/ChangeEvidence.json`, `schemas/v1/ImpactAssessment.json`, `schemas/v1/PromotionTicket.json`, Issue #90).

1. Каноническая абстракция — Promotion, а не platform-specific Merge Queue.
2. Change Evidence, Integration Evidence и Authorization Evidence имеют независимые области жизни и инвалидируются по разным причинам.
3. Финальный side effect разрешён только по sealed PromotionTicket; Human Approval связывается с hash этого ticket через существующий ApprovalRecord.
4. Один target имеет не более одного активного Promotion Lease; stale executor блокируется fencing generation.
5. Native platform queue является optional acceleration adapter; personal GitHub repository должен поддерживаться portable backend.
6. Missing capability приводит к safe degradation, а не к обходу Gate.
7. AI не может единолично понижать risk class до SAFE.
8. PromotionStore имеет ровно один authoritative SSoT.

## 32.41. Технологические решения, которые пока не должны становиться архитектурными догмами

Следующие вещи могут быть заменены без изменения архитектурных принципов.

## 32.42. Реализация IPC Electron

**Тип:** IMPLEMENTATION CHOICE.

Необходимо:

- изолировать Renderer;
- валидировать сообщения;
- иметь узкий API;
- не давать прямой Shell.

Но точное устройство IPC определяется реализацией.

## 32.43. UI framework внутри Electron

**Тип:** OPEN IMPLEMENTATION CHOICE.

Не утверждено архитектурой:

- React;
- Vue;
- Svelte;
- чистый TypeScript;
- другой подход.

Выбор должен учитывать:

- производительность;
- сложность;
- поддержку;
- визуализацию графов;
- объём зависимостей;
- безопасность.

## 32.44. Язык реализации отдельных модулей

**Тип:** IMPLEMENTATION CHOICE с ограничениями.

Стек может быть смешанным.

Архитектура требует:

- понятных контрактов;
- воспроизводимой сборки;
- Windows 11 support;
- простого IPC;
- тестируемости.

Не требуется писать абсолютно все компоненты на одном языке, если это ухудшает систему.

## 32.45. Формат внутренних схем

**Тип:** OPEN IMPLEMENTATION CHOICE.

Нужно определить точный машинный формат:

- JSON Schema;
- Protocol Buffers;
- TypeScript schema;
- Python models;
- другой вариант.

Критерий:

> одна каноническая схема должна давать валидацию и генерацию производных представлений.

## 32.46. Физическая реализация Event Journal

**Тип:** IMPLEMENTATION CHOICE.

Архитектурно Event Journal обязателен для критичных переходов.

Не закреплено навсегда:

- отдельная SQLite-таблица;
- отдельная база;
- append-only файлы;
- другой локальный механизм.

## 32.47. Secret Store Windows

**Тип:** IMPLEMENTATION CHOICE.

Варианты могут включать:

- Windows Credential Manager;
- DPAPI;
- другой защищённый механизм.

Главное:

> секрет не хранится открытым текстом в обычной конфигурации.

## 32.48. Сетевой транспорт Worker

**Тип:** DEFERRED IMPLEMENTATION CHOICE до remote Worker этапа.

Возможны:

- защищённый локальный API;
- WebSocket;
- gRPC;
- другой транспорт.

Контракты должны быть независимы от транспорта.

## 32.49. Технология локального Discovery

**Тип:** DEFERRED.

Выбирается к этапу удалённых Workers.

Discovery не должен автоматически выдавать Trust.

## 32.50. Технология векторного индекса

**Тип:** DEFERRED.

Векторный индекс является производным ускорителем.

Выбор конкретной реализации не должен менять Knowledge semantics.

## 32.51. Реестр открытых вопросов, обязательных до версии v0.1 (OPEN BEFORE v0.1)

В соответствии с Architecture Baseline Gate [Issue #62], до начала полномасштабного кодирования версии v0.1 зафиксирован закрытый исчерпывающий перечень архитектурных вопросов, распределённых по этапам Gate:

### Этап G2 — Machine Contracts (Машинные контракты)
- **OQ-003** — единый машинный формат системных контрактов (JSON Schema / Protobuf) и правила версий (Issue #40) — **ACCEPTED** (ADR-034).
- **OQ-005** — машинно-читаемая структура Module Registry и граф зависимостей (Issue #47) — **ACCEPTED** (ADR-035, `modules_registry.json`).
- **OQ-006** — каталог физических канонических схем (Issue #40) — **ACCEPTED** (ADR-034, `schemas/v1/`).
- **OQ-007** — минимальная модель Identity и привязка пользователя Windows к ролям KAT9I_OS (Issue #44) — **ACCEPTED** (ADR-036, `schemas/v1/Identity.json`, `schemas/v1/ApprovalRecord.json`).
- **OQ-009** — формат Event Journal, Checkpoint и Replay Recovery (Issue #46) — **ACCEPTED** (ADR-037, `schemas/v1/JournalEvent.json`, `schemas/v1/Checkpoint.json`).

### Этап G3 — Runtime Foundation (Фундамент исполняемой системы)
- **OQ-002** — физическая граница Electron Main и отдельного Rust Core Runtime (отдельный сервис + безопасный IPC) (Issue #41) — **ACCEPTED** (ADR-038).
- **OQ-004** — минимальный безопасный внутренний API между Electron и Core (Issue #41) — **ACCEPTED** (ADR-038, `schemas/v1/CoreIpcMessage.json`).
- **OQ-008** — минимальный Windows Secret Store (DPAPI / Credential Manager) (Issue #45) — **ACCEPTED** (ADR-039, `schemas/v1/SecretRef.json`).
- **OQ-010** — правила завершения Core при закрытии окна Electron (System Tray vs Process Tree Kill).

Остальные вопросы не входят в список `OPEN BEFORE v0.1` выше и откладываются строго по своим детальным статусам: OQ-011 — `DEFERRED UNTIL PRE-RELEASE`, OQ-012 и OQ-013 — `DEFERRED UNTIL v0.2`; будущие OQ получают собственный явный этап. Они не должны считаться закрытыми или переноситься на другой срок только из-за этой сводки.

## 32.52. OQ-001 — основной язык/стек Core

> **Статус:** `SUPERSEDED` / `ACCEPTED` (ADR-033, канонический источник: [Раздел 23. Технологический стек и границы среды выполнения](23_TECHNOLOGY_STACK_AND_RUNTIME.md)).

Решение принято в разделе 23:
- **Rust** — системное ядро KAT9I_OS и основной локальный Runtime.
- **Electron + TypeScript** — настольная оболочка и пользовательский интерфейс.
- **Python** — специализированный AI/ML Worker-слой.

## 32.53. OQ-002 — точная граница Electron Main и отдельного Core Runtime

> **Статус:** `ACCEPTED` (ADR-038, канонический источник: [docs/architecture/23_TECHNOLOGY_STACK_AND_RUNTIME.md](23_TECHNOLOGY_STACK_AND_RUNTIME.md), [docs/architecture/29_ELECTRON_UI.md](29_ELECTRON_UI.md), Issue #41).

Принят **Вариант B**: Core является физически отдельным локальным процессом (Rust Core Runtime), Electron подключается к нему через защищённый IPC.
Обоснование:
- Сбой или перезапуск Electron не уничтожает состояние активных задач (Zero Task Disruption);
- Возможность автономной работы без GUI (Headless Mode);
- Renderer не получает прямого доступа к файловой системе, БД или shell;
- Reconnect восстанавливает наблюдение за текущим состоянием.

## 32.54. OQ-004 — внутренний API между Electron и Core

> **Статус:** `ACCEPTED` (ADR-038, канонический источник: `schemas/v1/CoreIpcMessage.json`, `scripts/core_ipc_prototype.py`, `tests/test_core_ipc_boundary.py`, Issue #41).

В качестве механизма взаимодействия принят узкий типизированный Loopback IPC (TCP / локальный сокет на `127.0.0.1` со строгим `auth_token`):
- Контракт сообщений: `schemas/v1/CoreIpcMessage.json` (JSON Schema Draft 2020-12);
- Разрешённые методы: `core.ping`, `core.get_system_state`, `core.create_task`, `core.cancel_task`, `core.subscribe_events`;
- Полная изоляция от произвольного выполнения команд: любой неразрешённый метод отклоняется (`METHOD_NOT_ALLOWED`);
- Высокая производительность: задержка ping/pong на Windows 11 составляет менее 5 мс;
- Поддержка стриминга событий и повторного подключения при сбоях UI.

## 32.55. OQ-003 — формат системных контрактов

> **Статус:** `ACCEPTED` (ADR-034, канонический источник: [schemas/README.md](../../schemas/README.md), `schemas/v1/`, Issue #40).

В качестве канонического машинного формата системных контрактов KAT9I_OS для всех слоёв (Rust Core, TypeScript UI, Python Workers) принят **JSON Schema (Draft 2020-12)**.
Обоснование:
- Нативная поддержка во всех трёх языках без обязательных бинарных компиляторов (protoc);
- Строгая проверка ограничений (`pattern`, `enum`, `minimum`, `maximum`, `required`);
- Строгий инвариант безопасности `additionalProperties: false` (Fail-Closed при неизвестных полях);
- Человекочитаемость и прозрачность в журналах аудита и отладке.

## 32.56. Итоги выбора внутреннего API Electron и Core

> **Статус:** Закрыто в рамках OQ-004 / ADR-038 (канонический источник: `schemas/v1/CoreIpcMessage.json`, `scripts/core_ipc_prototype.py`, `tests/test_core_ipc_boundary.py`, Issue #41).

Выбран узкий типизированный Loopback IPC (TCP / сокет на `127.0.0.1`) с сессионной авторизацией и валидацией схем Draft 2020-12.

## 32.57. OQ-005 — структура Module Registry

> **Статус:** `ACCEPTED` (ADR-035, канонический источник: `schemas/v1/ModuleRegistry.json`, `modules_registry.json`, `scripts/verify_module_registry.py`, Issue #47).

Машинная структура реестра модулей утверждена:
- Формат: JSON Schema Draft 2020-12 (`schemas/v1/ModuleRegistry.json`);
- Физический реестр первой вертикали v0.1: `modules_registry.json`;
- Обязательные машинные поля: `module_id`, `name`, `version`, `tier`, `canonical_owner_ref`, `canonical_responsibility`, `provides_contracts`, `requires_contracts`, `dependencies`, `capabilities`, `health_interface`, `documentation_ref`;
- Автоматическая валидация и построение топологического порядка: `scripts/verify_module_registry.py`;
- Инварианты: ацикличность графа (DAG), уникальность ответственности (ADR-032) и полная связность контрактов.

## 32.58. OQ-006 — каталог канонических схем

> **Статус:** `ACCEPTED` (ADR-034, канонический источник: [schemas/README.md](../../schemas/README.md), `schemas/v1/`, Issue #40).

Физическим единым источником истины (SSoT) для канонических схем определён каталог:

> `schemas/v1/`

В каталоге зафиксирован минимальный набор схем первой вертикали v0.1:
- `TaskContract.json` — паспорт и требования задачи;
- `TaskRuntimeState.json` — состояние исполнения;
- `TaskResult.json` — результат задачи;
- `Evidence.json` — запись аудита и доказательства;
- `SecurityDecision.json` — решение Scope Guard;
- `CapabilityGrant.json` — мандат прав;
- `SystemEvent.json` — универсальный конверт событий.

## 32.59. OQ-007 — минимальная модель Identity

> **Статус:** `ACCEPTED` (ADR-036, канонический источник: [docs/spec/14_SECURITY.md](../spec/14_SECURITY.md), `schemas/v1/Identity.json`, `schemas/v1/ApprovalRecord.json`, Issue #44).

Решение формализовано:
1. **Канонические сущности**:
   - `Identity` (`identity_id` вида `id-...`): уникальный неизменный субъект;
   - `Role`: роль субъекта (`LOCAL_USER`, `LOCAL_ADMIN`, `WORKER`, `CORE_SERVICE`, `NODE_OPERATOR`, `AUDITOR`);
   - `Trust Level`: уровень доверия (`UNTRUSTED`, `PROVISIONAL`, `AUTHENTICATED`, `FULL_LOCAL_TRUST`);
   - `Capability Grant`: временные мандаты прав (`schemas/v1/CapabilityGrant.json`).
2. **Безопасная привязка к Windows без хранения паролей**:
   - Никакие пароли или NTLM/LM хэши Windows не хранятся;
   - Связывание осуществляется через канонический Windows SID (`security_identifier`) и криптографический `account_hash`;
   - Роль `LOCAL_ADMIN` требует подтверждённого административного токена Windows (`is_elevated=true`);
   - Смена активного Windows SID немедленно отзывает активные сессии (`Fail-Closed`).
3. **Модель Human Approval и защита от Replay**:
   - Человеческое одобрение оформляется по схеме `schemas/v1/ApprovalRecord.json` с проверкой `task_id`, `action_hash`, криптографического `nonce` (длина >= 16) и временного окна `issued_at` - `expires_at`;
   - Worker не может выступать автором Human Approval.

## 32.60. OQ-008 — минимальный Secret Store

> **Статус:** `ACCEPTED` (ADR-039, канонический источник: `schemas/v1/SecretRef.json`, `scripts/windows_secret_store.py`, `tests/test_secret_store.py`, Issue #45).

Решение формализовано:
1. **Криптографический механизм Windows 11**:
   - Выбран **Windows Data Protection API (DPAPI)** с привязкой к текущей учётной записи пользователя (`USER_LOCAL`).
   - Исключена утечка ключей на другие машины или учётные записи.
2. **Модель SecretRef**:
   - Контракт `schemas/v1/SecretRef.json` содержит только идентификатор и метаданные;
   - Значение секрета отсутствует в TaskContract, журналах Event Journal, Knowledge Base и обычном состоянии;
   - Доступ предоставляется только при наличии действующего `CapabilityGrant` ("SECRET_READ_SCOPED").
3. **Отзыв и безопасность**:
   - Процедура немедленного отзыва (`revoke_secret`) с затиранием нулями;
   - Проверка существования секрета без раскрытия значения (`check_exists`).

## 32.61. OQ-009 — формат Event Journal и Checkpoint

> **Статус:** `ACCEPTED` (ADR-037, канонический источник: [docs/architecture/21_RELIABILITY_AND_RECOVERY.md](21_RELIABILITY_AND_RECOVERY.md), `schemas/v1/JournalEvent.json`, `schemas/v1/Checkpoint.json`, Issue #46).

Решение формализовано:
1. **Append-only Event Journal (`schemas/v1/JournalEvent.json`)**:
   - Строгая монотонность `sequence_number` (от 1);
   - Обязательный перечень событий v0.1: жизненный цикл задач (`TASK_*`), управление Lease (`LEASE_*`), внешние действия (`SIDE_EFFECT_*`), события безопасности (`SECURITY_*`, `CAPABILITY_*`, `APPROVAL_RECORDED`) и чекпоинты (`CHECKPOINT_COMMITTED`);
   - Идемпотентность побочных эффектов через уникальный `operation_id` (`op-...`);
   - Защита от устаревших воркеров через `lease_generation` (Fencing Token).
2. **Контрольные точки (`schemas/v1/Checkpoint.json`)**:
   - Фиксация согласованного снимка `runtime_state`, перечня выполненных `operation_id` и ссылок на артефакты;
   - Связка с `last_sequence_number`.
3. **Replay Recovery**:
   - Старт с последнего Checkpoint с доигрыванием последующих событий;
   - Защита от дублирующих побочных действий (`SKIP_ALREADY_EXECUTED`);
   - Retention: минимум 30 суток для аудита.

## 32.62. OQ-010 — правила завершения Core при закрытии Electron

Нужно определить пользовательский UX:

- закрытие окна → Tray;
- отдельная команда «Завершить KAT9I_OS»;
- поведение активных задач;
- Windows shutdown.

Статус:

`OPEN BEFORE Electron P0`.

## 32.63. OQ-011 — система обновления Electron/Runtime

Архитектура обновлений принята.

Но конкретный механизм доставки:

- installer;
- updater;
- package;

ещё не выбран.

Статус:

`DEFERRED UNTIL PRE-RELEASE`.

## 32.64. OQ-012 — первая локальная AI Runtime

Нужно определить первую реально поддерживаемую локальную среду для v0.2.

Это не означает эксклюзивность навсегда.

Статус:

`DEFERRED UNTIL v0.2`.

## 32.65. OQ-013 — первая внешняя AI-интеграция

Нужно выбрать первый внешний Provider для проверки NORMAL/HIGH routing.

Архитектура не должна зависеть от одного Provider.

Статус:

`DEFERRED UNTIL v0.2`.

## 32.66. OQ-014 — формат документации с уровнями подробности

> **Статус:** `ACCEPTED` (канонический источник: `scripts/generate_html_docs.py`, PR #60, PR #68, Issue #36).

Реализовано единое производное представление с 5 уровнями подробности (1. Очень просто / 2. Просто / 3. Рабочий / 4. Технический / 5. Максимум) на базе двухуровневой разметки атрибутов `data-section-level` и `data-detail-level` без дублирования текста спецификаций. Автоматические тесты `tests/test_docs_ssot.py` подтверждают структурное наличие разметки и связанной JavaScript-логики; они не являются browser/DOM-level доказательством фактического поведения навигации и фильтрации.

## 32.67. OQ-015 — интерфейс архитектурного словаря

> **Статус:** `ACCEPTED` (канонический источник: [docs/GLOSSARY.md](../GLOSSARY.md), PR #24).

Формат многоуровневых словарных статей утверждён и реализован в `docs/GLOSSARY.md`: «Очень просто», «Рабочее объяснение», «Технически» со ссылками на канонические архитектурные разделы.

## 32.68. OQ-016 — GitHub Project и Ruleset

> **Статус:** `SPECIFICATION ACCEPTED / INFRASTRUCTURE PROVISIONAL` (канонический источник: [docs/spec/24_GITHUB_PROJECT_MANAGEMENT.md](../spec/24_GITHUB_PROJECT_MANAGEMENT.md), `.github/workflows/quality.yml`, PR #54, Issue #1).

Архитектурная спецификация процессов разработки, ролей коворкеров и автоматический CI Quality Gate приняты и внедрены через workflow GitHub Actions (`.github/workflows/quality.yml`). Настройка платформенных Rulesets защиты ветки main и досок GitHub Project v2 в API репозитория отслеживается в Issue #1 и выполняется координатором инфраструктуры.

## 32.69. Вопросы, которые сознательно откладываются

Следующие решения не должны тормозить MVP.

## 32.70. Federation нескольких полноценных KAT9I_OS

`DEFERRED AFTER 1.0`, если не появится более ранняя реальная необходимость.

## 32.71. Enterprise multi-user

Базовые поля user_id/Scope предусматриваются заранее.

Полноценное корпоративное управление пользователями:

`DEFERRED`.

## 32.72. Kubernetes / сложный cluster orchestration

`REJECTED FOR MVP`.

Может быть пересмотрено только при доказанной необходимости.

## 32.73. Distributed Consensus

`DEFERRED`.

Первая версия использует один Primary Node.

## 32.74. Marketplace Skills

`DEFERRED`.

Сначала должен заработать собственный Skill lifecycle.

## 32.75. Поддержка десятков AI Providers

`DEFERRED`.

Сначала достаточно нескольких маршрутов, чтобы доказать интерфейс Provider abstraction.

## 32.76. Полностью автономное изменение собственной архитектуры

`REJECTED`.

Learning может предлагать улучшения.

Критические архитектурные решения не принимаются Learning самостоятельно.

## 32.77. Допущения, которые необходимо проверять экспериментально

Некоторые решения выглядят правильными, но требуют измерений.

## 32.78. A-001 — Electron достаточно производителен для визуализации

Предположение:

> Electron справится с TaskGraph, Telemetry и Replay без заметного влияния на Core.

Нужно подтвердить нагрузочными тестами.

## 32.79. A-002 — SQLite достаточно для локального Primary

Предположение:

> до масштабов первой версии SQLite обеспечивает достаточную производительность Task State, Metrics и системной metadata.

Нужно измерять:

- contention;
- write latency;
- DB size;
- Recovery;
- backup time.

## 32.80. A-003 — один Primary достаточно до 1.0

Предположение:

> реальные задачи первой версии не требуют high-availability Core cluster.

Если практика докажет обратное — решение пересматривается.

## 32.81. A-004 — GitHub development vertical действительно лучший первый MVP

Предположение основано на том, что KAT9I_OS сама развивается через GitHub.

Если реализация выявит более простой вертикальный тест:

он может появиться раньше.

Но GitHub остаётся первой **полезной** dogfood-вертикалью.

## 32.82. A-005 — локальная модель способна покрывать часть LOW/NORMAL задач

Это проверяется benchmark на реальных задачах KAT9I_OS.

Local-first не означает:

> использовать локальную модель даже при неприемлемом качестве.

## 32.83. A-006 — Reference-first даст существенную экономию

Нужно измерять:

- Context Transfer;
- tokens;
- network;
- cache hit;
- latency.

Если Resolver слишком дорогой, стратегия может адаптироваться.

## 32.84. A-007 — Learning способен улучшать операционные параметры локальными алгоритмами

Первый Learning должен проверять это на:

- Timeout;
- Retry;
- Cache TTL;
- forecast calibration.

До доказательства не нужно строить сложный ML.

## 32.85. Как закрывается открытый вопрос

Open Question закрывается только когда есть:

1. варианты;
2. критерии;
3. сравнительный анализ;
4. решение;
5. причина;
6. последствия;
7. при необходимости прототип/Evidence.

После этого создаётся ADR со статусом `ACCEPTED`.

## 32.86. Не принимать технологию только потому, что она популярна

Например нельзя выбирать:

- React;
- gRPC;
- Kafka;
- PostgreSQL;

только потому, что они часто встречаются.

Нужно показать:

> какую конкретную проблему KAT9I_OS технология решает лучше альтернатив.

## 32.87. Внешний comparative research используется для закрытия вопросов

После завершения спецификации проводится исследование аналогов.

Для каждого открытого вопроса можно искать:

- как проблему решают mature-проекты;
- какие были реальные проблемы;
- насколько решение подходит Local-first desktop architecture.

## 32.88. Доноры тоже участвуют в сравнении

Для существенного решения проверяются:

- AG25;
- `kat9i_skills`;

если там уже существует рабочий механизм.

Но донор не получает автоматический приоритет.

## 32.89. Решение должно учитывать стоимость миграции

Если два варианта близки по качеству:

предпочтение может получить тот, который:

- проще заменить;
- лучше тестируется;
- имеет меньше скрытых зависимостей;
- меньше блокирует будущую архитектуру.

## 32.90. Reversible-first — сначала обратимые решения

На ранней стадии полезно предпочитать:

> **решения, которые можно заменить без переписывания всей системы.**

Особенно для:

- UI library;
- network transport;
- local AI runtime;
- vector DB;
- adapter implementation.

## 32.91. Irreversible decisions требуют больше Evidence

Чем сложнее решение изменить позднее:

тем выше требования к:

- анализу;
- прототипу;
- тестам;
- внешнему сравнению.

Например:

> формат базовых системных контрактов

важнее выбора библиотеки иконок.

## 32.92. Решения имеют Scope

Не каждое архитектурное решение глобально.

Например:

> SQLite для первой локальной версии

не означает:

> SQLite обязателен для любой будущей enterprise deployment.

Scope должен быть явным.

## 32.93. Решение имеет условия пересмотра

Пример:

> SQLite пересматривается, если реальные тесты показывают недопустимые блокировки или объём данных выходит за установленную границу.

Так система избегает как догматизма, так и бесконечного пересмотра.

## 32.94. Архитектурный долг

Если принято временное компромиссное решение:

создаётся:

`Architecture Debt — архитектурный долг`.

Указывается:

- почему временно принято;
- риск;
- срок/условие пересмотра.

Архитектурный долг оформляется Issue.

## 32.95. Нельзя скрывать временное решение как окончательное

Например:

> «пока положим всё в один JSON».

Если это технический прототип:

он должен быть явно обозначен как временный.

Иначе прототип превращается в архитектуру случайно.

## 32.96. Связь с GitHub

После Architecture Baseline новые крупные ADR должны быть связаны с:

- Issue;
- обсуждением;
- PR документации;
- QA архитектурного изменения.

Так история решений становится проверяемой.

## 32.97. Связь ADR с кодом

При реализации модуль может ссылаться на ADR ID.

Это помогает понять:

> почему код построен именно так.

Но ADR не должен превращаться в комментарий к каждой строке.

## 32.98. Electron показывает решения

В будущем в режиме разработки можно открыть:

> **Архитектурные решения**

и увидеть:

- ACCEPTED;
- OPEN;
- DEFERRED;
- SUPERSEDED.

Это особенно полезно новым коворкерам.

## 32.99. Open Questions в Electron

Разработчик может увидеть:

> 7 вопросов требуется закрыть до v0.1.

Но SSoT рабочей задачи остаётся соответствующий GitHub Issue.

## 32.100. Quality Gate для решений

После Architecture Baseline Quality Gate должен постепенно проверять:

- уникальность ADR ID;
- валидный статус;
- существование ссылки на канонический раздел;
- отсутствие двух ACCEPTED решений, которые прямо противоречат друг другу;
- отсутствие OPEN-вопроса, который реализация уже самовольно решила без ADR.

## 32.101. Что раздел не должен делать

Раздел 32 не должен:

- повторять полное ТЗ;
- создавать параллельные определения;
- автоматически превращать предложение в ACCEPTED;
- скрывать открытые вопросы;
- заставлять решить сейчас то, что не нужно MVP;
- делать временную библиотеку архитектурной догмой;
- использовать популярность технологии как доказательство;
- позволять Learning самостоятельно принимать критические ADR.

## 32.102. Основные принципы

1. **Принятое решение, допущение и выбор реализации — разные сущности.**
2. **Принятое решение не меняется молча.**
3. **Крупные решения фиксируются ADR.**
4. **Подробный смысл остаётся в каноническом разделе.**
5. **Открытые вопросы имеют срок или этап, к которому должны быть закрыты.**
6. **Необязательные для MVP вопросы сознательно откладываются.**
7. **Обратимые технологические решения не должны превращаться в догму.**
8. **Необратимые решения требуют большего количества Evidence.**
9. **Допущения проверяются реальными измерениями.**
10. **Внешний comparative research помогает принимать решения, но не диктует архитектуру.**
11. **Доноры рассматриваются как источник опыта, а не как шаблон.**
12. **Architecture Debt становится видимой GitHub-задачей.**
13. **После Architecture Baseline крупные изменения проходят Issue → решение → PR → QA.**
14. **Quality Gate со временем проверяет целостность реестра решений.**

## 32.103. Главный принцип

> **В KAT9I_OS всегда должно быть понятно, что уже решено, что пока только предполагается, что является заменяемой технической реализацией и что ещё требует решения; система не должна строиться на скрытых предположениях, случайных технологиях или забытых устных договорённостях.**
