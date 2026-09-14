# KAT9I_OS — WORKER QA

> **Единственная корневая точка входа для независимого QA Worker.**
>
> Команда `WORKER QA` запускает чтение и подтверждение QA-протокола, регистрацию подключения и автоматический поиск QA-заданий.
>
> Команда `WORKER QA -- QA+REVIEW` включает обязательный review для каждого результата. В обычном `WORKER QA` review автоматически включается при любом непроходном QA.

## 1. Официальный язык

Официальный человекочитаемый язык KAT9I_OS — **русский**.

На русском обязаны выводиться:

- сообщения Worker;
- таблицы состояния;
- объяснения ошибок и блокировок;
- Project-поля и человекочитаемые статусы;
- итоговые QA/review пояснения;
- операторские уведомления.

Стабильные машинные идентификаторы и протокольные токены (`KAT9I-QA-RESULT/1`, `QA PASS`, `command_id`, schema keys и аналогичные значения) сохраняются без перевода только там, где перевод сломал бы машинный контракт. Они не должны подменять русскоязычный пользовательский интерфейс.

## 2. Что читать при запуске

QA Worker читает только:

1. `WORKER_QA.md`;
2. `QA_PROTOCOL.md`;
3. `config/qa_worker.json`;
4. после обнаружения задания — конкретный authoritative `QA-COMMAND`, diff и только относящийся к нему Evidence.

Запрещено для общего контекста читать все Issues, PR, ветки, историю #171, весь репозиторий или весь `graveyard`.

При конфликте действует порядок:

`QA_PROTOCOL.md → WORKER_QA.md → канонические architecture/spec docs → context summaries → Issue/PR narrative`.

## 3. Режимы

### `WORKER QA`

- независимый QA;
- review при PASS не обязателен;
- любой `CHANGES REQUESTED`, `BLOCKED` или `QA ABORTED` автоматически требует `REVIEW_FINDINGS`;
- review использует уже загруженный diff/context;
- отдельный бюджет токенов на review не выдаётся.

### `WORKER QA -- QA+REVIEW`

- независимый QA;
- `REVIEW_FINDINGS` обязателен всегда, включая PASS;
- QA и review работают на одном exact HEAD и одном context packet;
- повторное чтение репозитория только ради review запрещено;
- полномочия режима не отличаются от обычного QA.

## 4. Автоматический рабочий цикл

После команды Worker обязан автоматически:

1. подтвердить `WORKER_QA.md` и `QA_PROTOCOL.md`;
2. определить профиль `QA` или `QA+REVIEW`;
3. выполнить deterministic connect через `scripts/qa_worker_listener.py`;
4. зарегистрировать presence;
5. перейти в автоматическое прослушивание с polling **10 секунд**;
6. во время ожидания не вызывать модель;
7. при обнаружении задания проверить latest authoritative `QA-COMMAND`, exact HEAD и Evidence Epoch;
8. синхронизировать Project в фазу проверки;
9. выполнить QA в пределах бюджета;
10. опубликовать `KAT9I-QA-RESULT/1` только как PR review на exact HEAD;
11. для non-pass автоматически добавить review findings;
12. вернуться в автоматическое ожидание следующей команды.

## 5. Discovery без растущего inbox

Issue #171 — только история требования. Он не является runtime inbox и не читается polling loop.

`scripts/qa_worker_listener.py` использует GitHub API и локальный cursor:

- bootstrap проверяет открытые PR на уже ожидающий QA-COMMAND;
- затем каждые 10 секунд проверяются только новые metadata-события;
- найденный кандидат перепроверяется в целевом PR;
- latest malformed/stale/forbidden command обрабатывается fail-closed;
- fallback к более старой QA-COMMAND запрещён;
- idle polling расходует **0 LLM tokens**.

## 6. Компактный вывод последних QA

Worker не должен засорять консоль длинными отчётами.

По умолчанию показываются **последние 5** обнаруженных QA; максимум — 10. Вывод обновляется только при изменении состояния. Если изменений нет, polling ничего не печатает.

Канонические колонки:

| PR | Режим | HEAD | Статус | Review |
|---:|---|---|---|---|
| `#N` | `FULL/DELTA/REUSE` | первые 7 символов SHA | русский статус | ID или `—` |

Русские пользовательские статусы:

- `Готов к QA`;
- `На проверке`;
- `QA пройден`;
- `Нужны изменения`;
- `Заблокирован`;
- `QA устарел`;
- `QA прерван`.

После таблицы допустима только одна компактная строка состояния вида:

`Автопрослушивание · 10 с · ожидают: N · токены ожидания: 0`

Запрещено в idle-выводе печатать Scope, Issue body, полный SHA, полные логи, Evidence Epoch, длинные URL и повторяющийся protocol text.

Таблица и footer строятся детерминированно без LLM.

## 7. Presence

Presence хранится в одном заранее созданном редактируемом comment-slot и обновляется **на месте**.

Presence фиксирует подключение, профиль, protocol hashes, интервал polling и бюджет. Он не является inbox, CONTROL, QA Evidence, FAST-marker, merge authority или Project lifecycle authority.

## 8. Project — автоматическое заполнение карточек

Project остаётся производным представлением, а не источником CONTROL.

Новые поля для QA не создаются. Используются только существующие канонические поля:

- `Статус`;
- `Исполнение`;
- `Проверяющий`;
- `Доказательство`.

Логические QA-фазы выводятся из их комбинации:

- **Готов к QA** → `Проверка QA / В очереди / AGY / Автопроверки пройдены`;
- **На проверке QA** → `Проверка QA / На проверке / AGY / Автопроверки пройдены`;
- **QA пройден** → `Проверка QA / В очереди / AGY / Проверка качества пройдена`;
- **QA заблокирован** → `Заблокировано / Заблокировано / AGY / Частично`;
- **QA устарел** → `Проверка QA / В очереди / AGY / Частично`.

Переход `QA пройден` выполняется только после trusted `QA-ACCEPT/FAST-QA-PASS` exact HEAD. Сам review AGY является Evidence и не получает lifecycle authority.

Если PR закрывает связанную Issue, одинаковая QA-фаза синхронизируется для обеих карточек.

## 9. Token Guard

Machine policy: `config/qa_worker.json`.

На один QA:

- preferred tier: Sol;
- soft input: **24 000**;
- hard input: **32 000**;
- max output: **4 000**;
- hard total: **40 000**;
- max context files: **20**;
- max log lines: **600**;
- max escalation: **1**;
- idle polling: **0 model tokens**.

`QA+REVIEW` и auto-review при non-pass не увеличивают лимиты.

После soft limit разрешён только targeted retrieval. При hard limit Worker либо завершает доказуемый verdict, либо возвращает BLOCKED/QA ABORTED с причиной нехватки Evidence. Самостоятельно расширять бюджет запрещено.

## 10. Минимизация контекста

Порядок чтения:

`QA-COMMAND → changed files/diff → acceptance → deterministic checks → затронутые invariants → точечные source fragments`.

По умолчанию запрещены:

- полный Issue/PR history dump;
- полный inventory веток;
- весь repository tree;
- полные CI logs вместо failing fragment;
- повторное чтение уже полученных chunks;
- повторный полный проход только ради review;
- fan-out дорогих QA-моделей на одинаковом контексте.

## 11. Fail-closed

QA не начинается или прекращается при malformed latest command, stale HEAD, forbidden capability, invalid Evidence Epoch, superseded command, уже существующем результате, невозможности проверить live state или исчерпании бюджета без достаточного Evidence.

Ни один такой случай не разрешает использовать старую QA-COMMAND или считать QA пройденным.

## 12. Нормативная карта

- `QA_PROTOCOL.md` — CONTROL и lifecycle QA;
- `WORKER_QA.md` — единственная точка входа QA Worker;
- `config/qa_worker.json` — polling, profiles, token policy и compact-output policy;
- `scripts/qa_worker_listener.py` — discovery/presence;
- `scripts/qa_project_sync.py` — производная синхронизация Project;
- context-файлы — только навигация, без собственного QA-протокола.

Новое правило QA должно изменять канонический слой, а не создавать параллельный документ.
