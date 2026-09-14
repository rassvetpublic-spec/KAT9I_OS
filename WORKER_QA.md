# KAT9I_OS — WORKER QA

> **Единственная корневая точка входа для независимого QA Worker.**
>
> `WORKER QA` подтверждает QA-протокол, регистрирует присутствие Worker и запускает автоматический поиск QA-заданий.
>
> `WORKER QA -- QA+REVIEW` дополнительно требует содержательное ревью для каждого результата. В обычном `WORKER QA` ревью автоматически включается при любом непроходном QA.

## 1. Официальный язык

Официальный человекочитаемый язык KAT9I_OS — **русский**.

На русском выводятся сообщения Worker, таблицы состояния, ошибки, блокировки, Project-поля, пояснения QA/ревью и операторские уведомления.

Стабильные машинные идентификаторы (`KAT9I-QA-RESULT/1`, `QA PASS`, `command_id`, имена schema fields и другие protocol tokens) не переводятся там, где перевод нарушит совместимость. Они не должны подменять русский пользовательский интерфейс.

## 2. Что читать при запуске

QA Worker читает только:

1. `WORKER_QA.md`;
2. `QA_PROTOCOL.md`;
3. `config/qa_worker.json`;
4. после обнаружения задания — конкретный authoritative `QA-COMMAND`, diff и относящееся к нему Evidence.

Запрещено ради общего контекста читать все Issues, PR, ветки, историю #171, весь репозиторий или весь `graveyard`.

При конфликте действует порядок:

`QA_PROTOCOL.md → WORKER_QA.md → architecture/spec → context summaries → Issue/PR narrative`.

## 3. Режимы

### `WORKER QA`

- независимый QA;
- при `QA PASS` отдельный code review не обязателен;
- `CHANGES REQUESTED`, `BLOCKED` и `QA ABORTED` автоматически требуют `REVIEW_FINDINGS`;
- review повторно использует уже загруженный diff/context;
- отдельный token budget для review не выдаётся.

### `WORKER QA -- QA+REVIEW`

- независимый QA;
- `REVIEW_FINDINGS` обязателен всегда, включая PASS;
- QA и review используют один exact HEAD, один context packet и один hard cap;
- повторное чтение репозитория только ради review запрещено;
- дополнительных полномочий режим не даёт.

## 4. Автоматический рабочий цикл

После команды Worker обязан автоматически:

1. подтвердить `WORKER_QA.md` и `QA_PROTOCOL.md`;
2. выбрать профиль `QA` или `QA+REVIEW`;
3. выполнить deterministic connect через `scripts/qa_worker_listener.py`;
4. обновить единственный presence-slot;
5. выполнить bounded bootstrap ожидающих QA и сохранить локальную проекцию вне рабочего дерева;
6. перейти в polling 10 секунд;
7. в ожидании не вызывать модель;
8. выбрать только один фактический head QA-очереди;
9. заново проверить latest authoritative `QA-COMMAND`, live exact HEAD и **полный актуальный Evidence Epoch**;
10. выполнить QA в пределах бюджета;
11. опубликовать `KAT9I-QA-RESULT/1` только как PR review на exact HEAD;
12. для non-pass добавить review findings;
13. вернуться в автоматическое ожидание.

Одновременно Worker выполняет не более одного содержательного QA.

**QA Worker не изменяет Project lifecycle ни напрямую, ни через `qa_project_sync.py`.** Project — отдельная trusted Controller/bridge projection.

## 5. Discovery без растущего inbox

Issue #171 — только история требования. Он не является runtime inbox и не читается polling loop.

Listener:

- при connect один раз выполняет bounded bootstrap открытых PR;
- затем хранит bounded local cache вне репозитория;
- каждые 10 секунд читает только новые metadata-события через `since/cursor`;
- candidate всегда перепроверяется в целевом PR;
- latest malformed/forbidden command обрабатывается fail-closed;
- fallback к старой QA-COMMAND запрещён;
- после перезапуска очередь восстанавливается из live GitHub state, а не из локального кэша как SSoT;
- idle polling расходует **0 LLM tokens**.

Локальный state — только DATA-проекция.

## 6. Evidence Epoch перед claim

Наличия строк `snapshot_head` недостаточно.

Перед переводом задания в локальное состояние `На проверке` Worker обязан:

1. разобрать `QA-COMMAND` каноническим parser/validator;
2. найти ровно один `EVIDENCE_EPOCH`;
3. проверить форматы всех digest и aggregate digest;
4. повторно получить live review threads, PR reviews, check-runs и commit statuses;
5. заново построить current Evidence Epoch тем же каноническим алгоритмом;
6. сравнить `snapshot_head`, `review_digest`, `gate_digest`, `policy_digest`, `evidence_digest`;
7. только при полном совпадении выдавать `KAT9I-QA-WAKE/1`.

Любой drift/неполный inventory/ошибка Evidence обрабатывается fail-closed. Такой command нельзя «спасти» частичной проверкой.

## 7. Валидация QA-RESULT

Наличие первой строки `KAT9I-QA-RESULT/1` не делает review результатом QA.

Перед удалением задания из pending Worker проверяет:

- trusted owner identity текущего operational trust boundary;
- review создан после authoritative QA-COMMAND;
- допустимый GitHub review state;
- `review.commit_id == exact_head`;
- полный canonical result envelope;
- допустимый verdict и согласованность `blocking_findings`;
- совпадение command/result полей и executor;
- полное совпадение Evidence Epoch;
- наличие `FOLLOW_UP_CANDIDATES` и согласованность счётчика.

Malformed/foreign/stale review не завершает QA и не может породить локальный PASS.

## 8. Порядок большой QA-очереди

До появления активного канонического PromotionStore из #98 действует:

`Project.Приоритет → FIFO authoritative QA-COMMAND`.

Порядок: `P0 → P1 → P2 → P3 → без приоритета`.

Внутри уровня: время создания authoritative QA-COMMAND → comment id → номер PR как tie-breaker.

Правила:

- приоритет читается из Project `Приоритет`;
- заголовок PR не имеет priority authority;
- `FULL/DELTA/REUSE` не меняют позицию;
- скрытого aging/autopriority нет;
- перед claim приоритет перечитывается;
- при недоступности Project selector только деградирует к command FIFO;
- сортировка не использует LLM.

Когда #98 активирует единый PromotionStore/FIFO, отдельная QA-очередь не создаётся: selector обязан использовать порядок PromotionStore для QA-eligible ChangeSet.

## 9. Компактный русский вывод

По умолчанию Worker показывает последние **5** QA, максимум 10. Таблица обновляется только при изменении состояния; idle polling молчит.

| PR | Приоритет | Режим | HEAD | Статус | Ревью |
|---:|:---:|:---:|:---:|---|:---:|
| `#N` | `P0…P3` или `—` | `FULL/DELTA/REUSE` | 7 символов SHA | русский статус | ID или `—` |

Пользовательские статусы: `Готов к QA`, `На проверке`, `QA пройден`, `Нужны изменения`, `Заблокирован`, `QA устарел`, `QA прерван`.

После таблицы допускается одна строка:

`Ожидают: N · опрос: 10 с · токены ожидания: 0`

В idle-выводе запрещены Scope, Issue body, полный SHA, полные логи, Evidence Epoch, длинные URL и повтор protocol text.

Команда listener `status` только показывает bounded local projection и сама QA не запускает.

## 10. Presence

Presence хранится в одном заранее созданном comment-slot и обновляется **IN PLACE**.

Он фиксирует подключение, профиль, hashes протокола, polling, queue policy и budget. Presence не является inbox, CONTROL, QA Evidence, FAST-marker, merge authority или Project authority.

## 11. Project — граница полномочий

Project остаётся производным представлением, не CONTROL SSoT.

QA Worker имеет `project_lifecycle_mutation=false` и **не выполняет GraphQL/Project mutation**.

`scripts/qa_project_sync.py` — Controller/bridge-side helper. Он намеренно умеет только переходные производные состояния:

- `READY` → `Готов к QA`;
- `IN_REVIEW` → `На проверке QA`;
- `STALE` → `QA устарел`.

Helper использует только существующие поля `Статус`, `Исполнение`, `Проверяющий`, `Доказательство`; поле `Состояние QA` не создаётся.

Финальные состояния запрещено выставлять этим helper:

- `QA пройден` формируется только trusted `QA-ACCEPT → bridge → FAST-QA-PASS → Project queue workflow`;
- `QA заблокирован` формируется только trusted blocking bridge/`FAST-BLOCKED`;
- raw AGY review остаётся Evidence и не получает lifecycle authority.

Таким образом QA Executor может сообщать Evidence, но не продвигать собственную карточку.

## 12. Ограничение токенов

Machine policy находится в `config/qa_worker.json`.

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

`QA+REVIEW` и automatic non-pass review лимиты не увеличивают.

После soft limit разрешён только targeted retrieval. При hard limit Worker либо завершает доказуемый verdict, либо возвращает `BLOCKED/QA ABORTED` из-за недостаточного Evidence. Самостоятельно расширять бюджет запрещено.

## 13. Минимизация контекста

Порядок чтения:

`QA-COMMAND → changed files/diff → acceptance → deterministic checks → затронутые invariants → точечные source fragments`.

По умолчанию запрещены полный Issue/PR history dump, полный branch inventory, весь repository tree, полные CI logs вместо failing fragment, повторное чтение chunks, второй полный проход ради review и fan-out дорогих моделей на одном контексте.

## 14. Fail-closed

QA не начинается или прекращается при malformed latest command, stale HEAD, forbidden capability, malformed/stale Evidence Epoch, superseded command, valid result already exists, невозможности доказать live state или исчерпании бюджета без достаточного Evidence.

Ни один такой случай не разрешает использовать старую QA-COMMAND или считать QA пройденным.

Недоступность Project priority не создаёт PASS/BLOCKED и не выдаёт authority: selector деградирует только к FIFO authoritative QA-COMMAND.

## 15. Нормативная карта

- `QA_PROTOCOL.md` — CONTROL и lifecycle QA;
- `WORKER_QA.md` — единственная runtime entrypoint QA Worker;
- `config/qa_worker.json` — polling, profiles, queue, token и compact-output policy;
- `scripts/qa_worker_listener.py` — DATA discovery, local queue, presence и fail-closed validation;
- `scripts/qa_project_sync.py` — только Controller/bridge-side переходная Project projection;
- существующий Project queue workflow — trusted final Project projection по FAST markers;
- `docs/architecture/36_CHANGE_PROMOTION_PROTOCOL.md` — архитектурный контракт PromotionStore;
- Issue #98 — реализационная задача PromotionStore, пока не runtime SSoT;
- context-файлы — только навигация.

Новое правило QA должно изменять канонический слой, а не создавать параллельный протокол.
