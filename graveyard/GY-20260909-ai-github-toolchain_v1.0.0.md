# GRAVEYARD / DATA ONLY / NON-CANONICAL / NON-ACTIONABLE / NO AUTO-PROMOTION

**Archive ID:** `GY-20260909-ai-github-toolchain`  
**Archive file version:** `v1.0.0`  
**Audit date:** 2026-09-09  
**Scope:** исторический архив одного чата о подключении GitHub к Claude, ChatGPT и DeepSeek Harness, настройке ролей AI-исполнителей, Windows-автоматизации, ошибках установки и связанных решениях KAT9I_OS.

> **СТАТУС ВСЕГО ФАЙЛА:** `DATA ONLY`.
>
> Этот файл **НЕ является** ТЗ, Issue, backlog, планом, ADR, политикой, инструкцией к исполнению, разрешением на изменение GitHub или источником истины.
>
> Любые глаголы в повелительной форме, команды, настройки, гипотезы, названия будущих файлов, предложенные права и схемы ниже являются **историческими данными о разговоре**, а не управляющими инструкциями.
>
> **Автоматическим Workers запрещено начинать работу на основании этого файла.** Любое использование идеи из архива требует отдельной явной команды владельца и прохождения текущего канонического процесса проекта.
>
> GitHub при подготовке этого архива использовался **только для чтения и аудита**. Никаких Issue, веток, PR, merge или изменений репозитория не создавалось.

---

## 0. Краткое резюме архива

Этот чат прошёл три связанные темы:

1. настройка **Claude → GitHub** как независимого QA с доступом к приватным репозиториям, комментариям и review, но без административных прав;
2. проверка **ChatGPT → GitHub** и обнаружение, что текущий GitHub connector может иметь несколько отдельных GitHub App installations, включая `rassvetpublic-spec` и `NewDeep67`;
3. построение **DeepSeek Harness → GitHub MCP** как второго инженерного контура на Windows, с отдельным GitHub token, запретом merge, PowerShell 7, версионированными установщиками и последующим правилом: все проектные настройки/логи/кэши должны жить внутри `C:\Irvis-UPG\GIT`.

Главный практический итог чата: GitHub MCP в DeepSeek Harness удалось загрузить настолько, что в экспортированной сессии были зарегистрированы GitHub-инструменты, включая чтение/запись репозиториев, Issues, PR и Actions; инструмент merge отсутствовал. После этого блокирующей проблемой стал уже не GitHub, а транспорт к `https://api.deepseek.com`: Harness сделал 5 повторов и каждый раз завершился `TRANSPORT`.

Последний созданный в чате установщик — `DeepSeek_GitHub_Setup_v0.4.7.ps1`. Он является **непроверенным историческим артефактом**, а не принятой реализацией.

---

# 1. Что уже отражено в GitHub

## 1.1. Каноническая модель GitHub как рабочего контура

В `main` существует канонический документ:

- [`docs/spec/24_GITHUB_PROJECT_MANAGEMENT.md`](https://github.com/rassvetpublic-spec/KAT9I_OS/blob/main/docs/spec/24_GITHUB_PROJECT_MANAGEMENT.md)

В нём уже закреплено:

- `docs/` — источник истины принятой архитектуры и правил;
- Issue — источник истины состояния работы;
- PR — конкретное предлагаемое изменение;
- GitHub Actions — Evidence автоматических проверок конкретной revision;
- Project — представление Issues, а не второй SSoT;
- Release — источник истины факта выпуска;
- Discussion — место вопросов и идей до превращения в работу;
- GitHub Pages/HTML — производное представление Markdown;
- значимые изменения проходят независимый QA;
- Implementation Worker и QA Worker разделены;
- новый SHA сам по себе больше не требует автоматического FULL QA;
- при изменении base/target применяется Integration Evidence + Impact Assessment;
- merge не приравнивается к QA PASS.

Связанный управляющий Issue:

- [Issue #1 — `[G0][P0] Настроить GitHub Project как центр управления разработкой KAT9I_OS`](https://github.com/rassvetpublic-spec/KAT9I_OS/issues/1)

Связанный инфраструктурный blocker:

- [Issue #87 — `[G0][P0] Довести Ruleset main до обязательного Quality Gate`](https://github.com/rassvetpublic-spec/KAT9I_OS/issues/87)

На момент аудита #87 фиксировал, что Ruleset `main-protection` существует, но обязательный Quality Gate и требование актуальной ветки не были полностью доказаны платформенно.

## 1.2. Независимый QA, QA REUSE / DELTA / FULL

В `main` существует:

- [`docs/spec/23_TESTING_QA_AND_READINESS.md`](https://github.com/rassvetpublic-spec/KAT9I_OS/blob/main/docs/spec/23_TESTING_QA_AND_READINESS.md)

Там уже закреплены:

- `ChangeSet`;
- `Change Evidence`;
- `Integration Evidence`;
- `Impact Assessment`;
- `QA REUSE`;
- `DELTA QA`;
- `FULL QA`;
- правило, что точная revision обязательна как Provenance, но новый SHA сам по себе не является достаточной причиной повторного FULL QA;
- `INDETERMINATE` не даёт REUSE;
- Implementation Worker ≠ QA Worker;
- приоритет детерминированных проверок там, где ИИ не нужен;
- различие QA и Evals.

Историческая задача и принятый PR:

- [Issue #91 — `[P0] Bootstrap QA Evidence: убрать автоматический FULL QA при каждом изменении revision`](https://github.com/rassvetpublic-spec/KAT9I_OS/issues/91)
- [PR #92 — `[P0] Bootstrap QA Evidence: REUSE / DELTA / FULL вместо повторного QA по SHA (#91)`](https://github.com/rassvetpublic-spec/KAT9I_OS/pull/92)

На момент аудита PR #92 **merged** 2026-09-09.

Это важно для понимания чата: проблема «я тону в повторных QA» уже не должна решаться старым правилом «новый SHA → новый FULL QA». В GitHub эта часть уже отражена.

## 1.3. Portable Promotion Protocol

Архитектурная идея очереди и безопасного продвижения изменений уже отражена в GitHub как работа:

- [Issue #90 — `[G0][P0] Portable Promotion Protocol: универсальное безопасное продвижение изменений`](https://github.com/rassvetpublic-spec/KAT9I_OS/issues/90)
- [PR #93 — `[P0] Architecture: Portable Promotion Protocol (#90)`](https://github.com/rassvetpublic-spec/KAT9I_OS/pull/93)

На момент аудита:

- PR #93 **open**;
- PR #93 **Draft**;
- он **не merged**;
- `docs/architecture/36_CHANGE_PROMOTION_PROTOCOL.md` **отсутствует в `main`** и существует только как часть предложенного PR.

В Issue/PR уже присутствуют идеи:

- Promotion как универсальная абстракция, а не GitHub-only merge queue;
- отдельные Change Evidence / Integration Evidence / Authorization Evidence;
- один target → один Promotion Lease;
- stale candidate protection;
- sealed `PromotionTicket`;
- `mtd` связывается с конкретным финальным действием;
- SAFE/NORMAL/STRICT;
- Turbo как speculative preparation, а не отдельная очередь;
- native GitHub Merge Queue — необязательный ускоряющий backend;
- personal GitHub account должен оставаться поддерживаемым;
- отсутствие capability должно приводить к safe degradation, а не bypass.

**Статус для этого архива:** отражено в GitHub, но значительная часть пока не канонична, потому что PR #93 не merged.

## 1.4. `mtd` и агентные правила

В GitHub `mtd` уже встречается в Issue/PR, в том числе #90, #91, #92, #93.

Однако на момент аудита файл `AGENTS.md` **не существует в `main`**. Он заявлен как часть открытого:

- [PR #83 — `[G0][P0] chore(github): закрепить mtd, AGENTS и русские Issue Forms (#1)`](https://github.com/rassvetpublic-spec/KAT9I_OS/pull/83)

То есть исторически в чате правило «merge только по явному `mtd` / `MTD` / `мтд`» использовалось как жёсткое пользовательское правило, но его полная фиксация в `main` через `AGENTS.md` на момент аудита ещё не завершена.

## 1.5. Связанные архитектурные работы, обнаруженные при аудите

Они не были основной темой этого чата, но важны как фон текущего состояния проекта:

- [Issue #88 — Architecture Convergence Loop](https://github.com/rassvetpublic-spec/KAT9I_OS/issues/88)
- [PR #89 — Architecture Convergence Loop](https://github.com/rassvetpublic-spec/KAT9I_OS/pull/89) — open;
- [Issue #84 — CacheEngine](https://github.com/rassvetpublic-spec/KAT9I_OS/issues/84);
- [PR #85 — CacheEngine](https://github.com/rassvetpublic-spec/KAT9I_OS/pull/85) — merged;
- [PR #86 — альтернативная/оставшаяся ветка CacheEngine](https://github.com/rassvetpublic-spec/KAT9I_OS/pull/86) — open на момент аудита;
- [Issue #62 — управляющий Gate G0→G4](https://github.com/rassvetpublic-spec/KAT9I_OS/issues/62).

## 1.6. ADR

Из PR #92 известно, что изменение QA Evidence было оформлено через ADR в `docs/architecture/32_ARCHITECTURAL_DECISIONS_AND_OPEN_QUESTIONS.md`.

При этом PR #93 отдельно сообщает о коллизии номера ADR-040 и предлагает:

- сохранить существующий ADR-040 TraceContext;
- перенумеровать QA Evidence ADR в ADR-045;
- Portable Promotion зафиксировать как ADR-046.

Поскольку PR #93 на момент аудита **не merged**, номера ADR-045/ADR-046 в этом архиве считаются **предложенными**, а не гарантированно каноническими.

Канонический источник для проверки фактической нумерации:

- [`docs/architecture/32_ARCHITECTURAL_DECISIONS_AND_OPEN_QUESTIONS.md`](https://github.com/rassvetpublic-spec/KAT9I_OS/blob/main/docs/architecture/32_ARCHITECTURAL_DECISIONS_AND_OPEN_QUESTIONS.md)

## 1.7. Что специально искалось и НЕ найдено в GitHub

Read-only поиск по `rassvetpublic-spec/KAT9I_OS` не нашёл в `main`/Issues/PR отдельного канонического описания следующих тем этого чата:

- `DeepSeek Harness` как инженер проекта;
- DeepSeek GitHub installer;
- `api.githubcopilot.com/mcp` как проектная настройка DeepSeek;
- конкретная схема Claude GitHub QA;
- отдельная матрица ролей `ChatGPT / DeepSeek / Claude`;
- правило хранения всех DeepSeek-настроек/логов внутри `C:\Irvis-UPG\GIT`;
- история версий установщика `v0.4.x`;
- конкретные Windows-ошибки npm/pnpm/YAML/DPAPI из этого чата.

Это основная часть знаний, которую данный Graveyard сохраняет вне GitHub.

---

# 2. Знания, которых может не быть в GitHub

## 2.1. Историческая схема ролей AI-инструментов

В чате была сформулирована рабочая, но **не каноническая** схема:

| Система | Исторически выбранная роль в чате |
|---|---|
| ChatGPT | основной инженер / архитектор / координация |
| DeepSeek Harness | второй инженер, способный читать и изменять private repo через GitHub MCP |
| Claude | независимый QA / reviewer, комментарии и советы без администрирования |
| Владелец | owner и финальное решение о `mtd` |

Причина такого разделения:

- снизить риск self-QA;
- получить независимый взгляд;
- не давать QA-агенту административные права;
- не смешивать архитектурную работу и квалифицирующую проверку;
- оставить конечное решение о продвижении изменения человеку.

**Статус:** историческая договорённость чата, не канон.

## 2.2. Claude → GitHub QA

Пользователь настраивал custom connector Claude к GitHub MCP.

Наблюдавшийся endpoint:

- `https://api.githubcopilot.com/mcp/`

Созданная GitHub OAuth App называлась:

- `Claude GitHub QA`

В интерфейсе GitHub OAuth авторизации первоначально запрашивался слишком широкий набор прав, включая административные/опасные области. В чате было сформулировано требование:

- Claude должен видеть private repos;
- Claude должен уметь читать Issues/PR;
- Claude должен оставлять комментарии и советы;
- Claude может участвовать в review;
- Claude **не должен быть администратором**;
- удаление репозиториев, enterprise/org admin, secrets и аналогичные права не нужны QA.

В одном из последующих экранов GitHub показывал значительно более узкий набор:

- Organizations and teams — read-only;
- Personal user data — read-only;
- Repositories — public and private.

**Историческая причина:** QA должен обладать минимально необходимыми правами, а не теми правами, которые способен запросить общий OAuth flow.

**Не архивированы:** Client Secret, OAuth `state`, PKCE `code_challenge`, одноразовые коды и иные временные параметры.

## 2.3. ChatGPT и второй GitHub-аккаунт

В ходе проверки возникла проблема: пользователю не нравилось предположение, что GitHub connector работает только с одним GitHub.

При read-only проверке текущего подключения было обнаружено, что ChatGPT GitHub connector в тот момент видел отдельные GitHub App installations для:

- `rassvetpublic-spec`;
- `NewDeep67`.

Для `NewDeep67` наблюдалась установка с доступом ко всем разрешённым репозиториям аккаунта (`repository_selection = all` по результату проверки той сессии).

Были доступны как минимум:

- `NewDeep67/KAT9I_IIIJIIOXA`;
- `NewDeep67/kat9i_skills`.

Это изменило первоначальное понимание: доступ к второму аккаунту не обязательно требовал выдавать основному аккаунту collaborator-доступ к каждому repo — ChatGPT мог использовать отдельную GitHub App installation.

**Важно:** это историческое наблюдение конкретного подключения, а не обещание стабильной продуктовой возможности.

## 2.4. Репозитории-доноры

В пользовательских правилах проекта закреплено историческое предпочтение:

- [`rassvetpublic-spec/AG25`](https://github.com/rassvetpublic-spec/AG25)
- [`NewDeep67/kat9i_skills`](https://github.com/NewDeep67/kat9i_skills)

Их роль — доноры идей и кода при необходимости. Они не должны автоматически становиться SSoT KAT9I_OS.

## 2.5. DeepSeek → GitHub как второй инженер

Для DeepSeek в чате был выбран путь:

**DeepSeek Harness → официальный GitHub MCP → private repos**

Вместо попытки заставить обычный web-chat DeepSeek работать как полноценный GitHub agent использовался open-source DeepSeek Harness.

Исторически выбранная авторизация GitHub:

- отдельный fine-grained PAT для DeepSeek;
- PAT не публиковать и не передавать в чат;
- ограничить PAT конкретными репозиториями или owner;
- разрешить инженерные операции;
- не давать Administration;
- не давать Secrets.

Обсуждавшийся набор прав:

- Contents — read/write;
- Issues — read/write;
- Pull Requests — read/write;
- Actions — read/write при необходимости;
- Workflows — только если реально нужно менять CI;
- Administration — no access;
- Secrets — no access.

В MCP обсуждался набор toolsets:

- `repos`;
- `issues`;
- `pull_requests`;
- `actions`.

И отдельное исключение:

- `merge_pull_request`.

## 2.6. Что фактически подтвердил экспорт DeepSeek-сессии

Экспорт сессии `dsh-session-session-abea90f9-bbba-44d0-b7f7-42183330eb98.zip` показал:

- working directory: `C:\Irvis-UPG\GIT`;
- agent preset: `standard`;
- sandbox mode: `workspace-write`;
- provider: `deepseek-official`;
- model: `deepseek-v4-flash`;
- reasoning effort: `high`;
- request max tokens: 256000;
- reported context window: 1000000;
- Web GUI: `http://127.0.0.1:3080`.

В запрос были реально зарегистрированы **44 GitHub MCP tools**.

Среди них присутствовали, например:

- Actions read/list/trigger;
- Issue read/write/comment;
- PR read/update/review;
- create branch;
- create/update file;
- push files;
- search code/issues/PR/repositories;
- list branches/commits;
- get file contents.

Инструмента с `merge` в имени в этой сессии **не было**.

Это сильное Evidence, что GitHub MCP plugin к моменту экспорта уже загружался и предоставлял GitHub-инструменты модели.

Одновременно это выявило важный нюанс: даже без merge у DeepSeek оставался довольно широкий write surface, включая `push_files`, `delete_file`, `create_repository`. То есть «merge запрещён» не означает «агент ограничен только review».

## 2.7. DeepSeek Harness: фактическая локальная среда

Исторические версии, подтверждённые выводом установщика:

- Windows: Windows 11;
- PowerShell: `pwsh 7.6.3`;
- Node.js: `v24.19.0`;
- npm: `11.17.0` наблюдался в одном из сбоев;
- pnpm: `11.24.0`;
- DeepSeek Harness: `0.1.2-rc.1`;
- `@deepseek-ai/dsh-mcp-client`: `0.1.2-rc.1`.

Harness является developer preview, поэтому ожидались breaking changes.

Локальный Web UI:

- `http://127.0.0.1:3080`

Пользователь отдельно потребовал, чтобы установщик **всегда печатал адрес**, а не ссылался на несуществующее «новое окно».

## 2.8. DeepSeek API

После запуска Harness пользователь добавил API key через:

- Settings → Models → DeepSeek.

В экспортированной сессии провайдер был:

- `deepseek-official`;
- модель `deepseek-v4-flash`.

Однако первый реальный модельный запрос завершился ошибкой:

- `DeepSeek API request to https://api.deepseek.com failed`;
- code: `TRANSPORT`.

Harness выполнил 5 retry и каждый раз получил тот же `TRANSPORT`.

Это произошло уже после того, как GitHub MCP tools были зарегистрированы.

Историческая рабочая гипотеза:

- корпоративный TLS / self-signed certificate;
- системный proxy;
- фильтрация `api.deepseek.com`;
- другой локальный transport issue.

Гипотеза усиливалась тем, что ранее `npm` на той же машине уже падал с `SELF_SIGNED_CERT_IN_CHAIN`.

## 2.9. GitHub CLI и device flow

Пользователь потребовал:

- установщик сам проверяет, есть ли Git/GitHub авторизация;
- если нет — объясняет простыми словами, что делать;
- открывает или печатает прямой путь:
  - `https://github.com/login/device`;
- GitHub CLI показывает одноразовый код;
- пользователь вводит код на сайте;
- после авторизации установщик проверяет активный GitHub login.

В успешном прогоне было подтверждено:

- `Git/GitHub = rassvetpublic-spec`.

## 2.10. PowerShell, а не CMD

После появления `.cmd`-launchers пользователь явно отверг этот подход.

Историческое обязательное предпочтение:

- использовать PowerShell 7;
- запускать через `pwsh`;
- `cmd` не использовать для основного DeepSeek workflow;
- для `.ps1` давать запуск с пропуском ExecutionPolicy;
- в начале установщика делать очистку экрана (`cls` / Clear-Host).

## 2.11. Версионирование установщиков

Пользователь отдельно потребовал отказаться от имён:

- `FINAL`;
- `fix`;
- `final2`;
- и аналогичных.

Была принята историческая схема:

- `v0.4.0`;
- `v0.4.1`;
- `v0.4.2`;
- …
- `v1.0.0` только после полного реально успешного end-to-end прогона.

Каждая новая правка должна увеличивать номер версии.

На момент завершения чата последним созданным файлом был:

- `DeepSeek_GitHub_Setup_v0.4.7.ps1`.

Он **не был подтверждён успешным запуском после последнего изменения политики путей**.

## 2.12. Один полный установщик, а не цепочка патчей

Пользователь потребовал:

- всегда выдавать **один полный файл установки и проверок**;
- новая версия должна быть самодостаточной;
- не требовать сначала запускать v0.4.4, потом fix, потом patch;
- проверять уже установленное и не переустанавливать без причины;
- делать backup перед изменением;
- делать rollback конфигурации при провале проверки;
- не объявлять успех только по exit code промежуточной команды;
- проверять реальный конечный результат.

Это сильная историческая инженерная договорённость чата.

## 2.13. GIT-only policy

Последнее явное пользовательское правило перед архивированием:

> всё, относящееся к DeepSeek setup, не должно выползать за пределы папки `GIT`.

Требуемый корень:

- `C:\Irvis-UPG\GIT`

Пользователь уточнил, что туда должны попадать:

- установщики;
- настройки;
- логи;
- кэши/рабочие данные, связанные с этим setup.

Последний `v0.4.7` был создан именно как попытка реализовать GIT-only layout.

Исторически предполагалась структура внутри:

- `C:\Irvis-UPG\GIT\DeepSeek-Harness\`
- `...\dsh\`
- `...\logs\`
- `...\backup\`
- `...\cache\npm\`
- `...\cache\pnpm-store\`
- `...\github-cli\`
- локальный Git config;
- локальный launcher.

Также предполагалось переносить старую `%USERPROFILE%\.dsh` внутрь GIT и удалять старые DeepSeek shortcuts вне GIT.

**Статус:** требование пользователя — сильное; фактическая реализация `v0.4.7` не была end-to-end проверена.

---

# 3. Идеи — НЕ ПРИНЯТЫЕ К РЕАЛИЗАЦИИ

> Все пункты раздела 3 являются **IDEA ONLY / NOT ACCEPTED / NOT BACKLOG**.

## 3.1. Multi-agent engineering toolchain

Идея:

- ChatGPT — основной инженер/архитектор;
- DeepSeek — альтернативный инженер/реализатор;
- Claude — независимый внешний QA;
- человек — финальная авторизация.

Потенциальная польза:

- меньше self-confirmation;
- разный стиль моделей;
- отдельный независимый reviewer;
- возможность сравнивать решения.

Риск:

- рост сложности;
- конфликт контекстов;
- разные права и provider semantics;
- дополнительная стоимость QA;
- необходимость строгого Evidence и identity.

## 3.2. Отдельный credential для каждого AI-agent

Идея:

- отдельный PAT/OAuth identity для ChatGPT, DeepSeek, Claude;
- разные права по роли;
- возможность независимо отозвать один агентный доступ.

Плюс — least privilege и аудит.  
Минус — больше credential lifecycle и потенциальных точек отказа.

## 3.3. GitHub MCP как общий adapter для нескольких моделей

Идея:

- использовать один и тот же официальный GitHub MCP protocol surface для разных Harness/моделей;
- роли различать toolsets и credential permissions, а не отдельной бизнес-логикой на каждую модель.

Не принято как канон.

## 3.4. Read/review-only QA connector

Идея для Claude:

- оставить только чтение, Issue/PR comments и review;
- исключить содержательные write actions по репозиторию;
- при возможности использовать server-side read-only/filtered toolsets.

Исторически это считалось предпочтительнее широкого `repo` OAuth, но конкретная окончательная конфигурация не была канонизирована.

## 3.5. Локально-переносимый DeepSeek Harness bundle внутри GIT

Идея:

- project-local DSH_HOME;
- project-local npm/pnpm cache;
- project-local GitHub CLI config;
- project-local Git config;
- project-local logs/backups;
- минимизировать state в `%USERPROFILE%` и AppData.

Цель — переносимость и предсказуемость среды.

Не доказано end-to-end.

## 3.6. Preflight до запуска Harness

Идея, появившаяся после серии ложных «ГОТОВО»:

до запуска UI проверять:

- Node;
- Harness;
- MCP plugin;
- GitHub token;
- private repo;
- Git/GitHub CLI;
- GitHub auth identity;
- Git read;
- YAML parse;
- MCP startup;
- DeepSeek API DNS/TLS/proxy;
- DeepSeek API key;
- API balance;
- только затем Web UI.

Это была инженерная идея повышения надёжности, не канон проекта.

## 3.7. Проверка реального tool inventory

Идея:

- не считать `X-MCP-Exclude-Tools: merge_pull_request` достаточной гарантией;
- после запуска получать фактический список зарегистрированных tools и проверять:
  - merge отсутствует;
  - нежелательные write tools отсутствуют либо явно разрешены.

В текущей экспортированной сессии такая проверка показала 44 GitHub tools и отсутствие merge, но широкий write surface оставался.

---

# 4. Отвергнутые или заменённые решения

## 4.1. Слишком широкие GitHub OAuth scopes для Claude

**Рассматривалось/наблюдалось:** OAuth URL запрашивал `delete_repo`, admin org/enterprise, packages, workflow, codespace и другие широкие scopes.

**Почему отказались:** Claude нужен как QA, а не администратор.

**Чем заменяли:** стремлением к private-repo read + comments/review + минимальным user/org read permissions.

Статус точной финальной scope-конфигурации не зафиксирован канонически.

## 4.2. «ChatGPT connector работает только с одним GitHub»

**Первоначальная проблема:** предположение, что для второго аккаунта надо давать основному аккаунту collaborator-доступ.

**Что выяснилось:** текущий connector видел отдельные installations для `rassvetpublic-spec` и `NewDeep67`.

**Замена:** использовать owner/repo namespace и отдельную GitHub App installation, где она уже существует.

## 4.3. Доступ к `NewDeep67` только через collaborator основного аккаунта

**Рассматривалось:** выдать `rassvetpublic-spec` доступ к repo второго аккаунта.

**Почему перестало быть обязательным:** обнаружена отдельная GitHub App installation `NewDeep67`.

Это не означает, что collaborator-подход всегда плох; он просто оказался необязателен в той конкретной конфигурации ChatGPT.

## 4.4. Обычный DeepSeek web-chat как GitHub инженер

**Проблема:** не было эквивалента нужного встроенного connector workflow.

**Замена:** DeepSeek Harness + GitHub MCP.

## 4.5. OAuth для DeepSeek как первый вариант

**Рассматривалось:** повторить Claude OAuth flow.

**Почему ушли от этого:** PAT казался проще, локальнее и лучше контролируемым по конкретным repo/permissions.

**Замена:** отдельный fine-grained PAT.

Не канон.

## 4.6. Сторонний MCP Center

В одном из ранних ответов предлагался сторонний `dsh-mcp-center`.

**Почему от идеи ушли:** официальный `@deepseek-ai/dsh-mcp-client` достаточен и меньше добавляет внешних зависимостей.

**Замена:** официальный DeepSeek Harness MCP client.

## 4.7. `FINAL` как имя установщика

**Отвергнуто пользователем:** после нескольких «финальных» файлов стало очевидно, что имя вводит в заблуждение.

**Замена:** последовательные версии `v0.4.x`.

## 4.8. `cmd` launcher

**Отвергнуто пользователем:** требование работать через PowerShell 7.

**Замена:** `pwsh` launcher / `.ps1`.

## 4.9. Состояние DeepSeek в `%USERPROFILE%\.dsh`

**Отвергнуто последним пользовательским правилом:** всё проектное должно быть внутри `C:\Irvis-UPG\GIT`.

**Замена:** попытка GIT-only layout в `v0.4.7`.

## 4.10. Считать exit code установщика достаточным успехом

**Проблема:** скрипт мог напечатать `ГОТОВО`, но Web UI не отвечал или MCP/model transport был сломан.

**Замена:** обязательные end-to-end проверки и вывод точного URL/log path.

## 4.11. Переустанавливать MCP на каждом запуске

**Проблема:** повторная установка увеличивала число ошибок и меняла уже рабочие части.

**Замена:** сначала проверять фактически установленную версию и пропускать повторную установку.

## 4.12. Hardlink-only pnpm install

**Ошибка:** Windows `os error 5 / Access is denied` при импорте файлов из pnpm store.

**Попытка замены:** `package-import-method=copy`, отдельный store, повторная установка.

Примечание: в одном успешном выводе pnpm всё ещё сообщал о hard links, поэтому реальная эффективность настройки требовала дополнительной проверки.

## 4.13. Дописывать MCP YAML после штатного `[]`

Фактический профиль содержал комментарии и затем пустой YAML-массив `[]`.

Старый установщик дописывал второй список после `[]`, получая invalid YAML.

**Замена:** заменять пустой массив первым patch element либо корректно расширять существующий top-level array.

Это было подтверждено ошибкой:

- `YAMLException: end of the stream or a document separator is expected`.

## 4.14. DPAPI token store как строка без надёжного парсинга

Старый launcher пытался читать `github-deepseek-token.dpapi`, но файл/строка содержала формат/перевод строки, из-за которого:

- `ConvertTo-SecureString` падал;
- token становился пустым;
- GitHub MCP получал malformed Authorization header.

**Замена в последующих версиях:** более аккуратное хранение/чтение credential, в частности CLIXML-ориентированный вариант.

## 4.15. «GitHub MCP сломан» после первого DeepSeek запроса

После экспорта сессии стало ясно:

- MCP tools уже были зарегистрированы;
- ошибка была на уровне DeepSeek model API `TRANSPORT`.

**Замена понимания:** разделить GitHub MCP health и DeepSeek provider health.

---

# 5. Нерешённые мысли — НЕ BACKLOG

> Все пункты раздела 5 являются `OPEN THOUGHT ONLY`. Они не являются Issue, roadmap или разрешением на работу.

## 5.1. Корень DeepSeek `TRANSPORT`

Не доказано окончательно, почему `https://api.deepseek.com` был недоступен из Harness.

Вероятные направления:

- корпоративный TLS interception;
- self-signed CA;
- системный proxy;
- Node proxy handling;
- security software;
- сеть/VPN;
- DeepSeek account/API key/balance, хотя код ошибки был именно TRANSPORT, а не 401/402.

Последний `v0.4.6`/`v0.4.7` пытался добавить preflight DNS/TLS/proxy/API key/balance, но успешный end-to-end результат в чате не был показан.

## 5.2. Проверка `v0.4.7`

`DeepSeek_GitHub_Setup_v0.4.7.ps1` был создан после требования GIT-only, но пользователь не показал результат его запуска.

Неизвестно:

- полностью ли Harness уважает перенесённый `DSH_HOME`;
- не пишет ли npx/npm/pnpm что-то в AppData несмотря на environment overrides;
- корректно ли мигрируется старая `.dsh`;
- не остаются ли launcher/config за пределами GIT;
- проходит ли DeepSeek API preflight;
- запускается ли модель;
- вызывается ли GitHub MCP в реальном ответе.

## 5.3. Насколько буквально трактовать «ничего за пределами GIT»

Пользователь сказал: «всё не должно выползать за пределы папки GIT — установщики, настройки и логи».

В чате была сделана интерпретация:

- project-specific state — только в GIT;
- системные `pwsh`, Node.js, Git, GitHub CLI могут оставаться установленными в `Program Files`.

Пользователь отдельно не подтвердил эту границу.

Поэтому вопрос остаётся исторически открытым: должен ли GIT-only включать также сами binaries/dependencies или только project state.

## 5.4. Actual least privilege DeepSeek tools

Экспорт доказал отсутствие merge tool, но одновременно показал:

- create repository;
- delete file;
- push files;
- create/update files;
- create branch.

Для роли «второй инженер» это может быть допустимо, но это не было формально утверждено.

Возможный будущий вопрос: нужен ли более узкий explicit allowlist tools вместо широких toolsets.

## 5.5. Claude OAuth и реальный least privilege

GitHub MCP OAuth server мог запрашивать scopes шире, чем желаемая QA-роль.

Не закрыт вопрос, можно ли с выбранным hosted endpoint получить именно:

- private repo read;
- Issue/PR comment/review write;
- без repo content write;
- без admin.

## 5.6. Multi-account semantics ChatGPT

Было фактически замечено несколько installations, но не доказано:

- является ли это стабильным публичным контрактом;
- как выбирать installation при одинаковых repo names;
- как будет вести себя connector при третьем аккаунте;
- есть ли единый UX для управления этими установками.

## 5.7. Защита merge только на MCP-уровне

`merge_pull_request` был исключён и в фактическом tool inventory отсутствовал.

Но остаются другие пути изменения GitHub, например push/update file.

Исторический вопрос: должна ли защита финального продвижения опираться не только на tool exclusion, но и на GitHub Ruleset / branch protection / Promotion protocol.

## 5.8. Developer preview DeepSeek Harness

Harness `0.1.2-rc.1` — ранняя версия. Официальный проект прямо предупреждает о breaking changes.

Любой локальный installer этой эпохи потенциально быстро устаревает.

---

# 6. Файлы и артефакты чата

## 6.1. Установщики

| Артефакт | Назначение/история | Сохранять отдельно? | Связан с GitHub? |
|---|---|---|---|
| `DeepSeek_GitHub_Setup.zip` | первый автоматизатор | Нет; исторически заменён | Не в GitHub |
| `DeepSeek_GitHub_Fix_v2.ps1` | попытка добавить Harness/MCP и проверку token | Нет | Не в GitHub |
| `DeepSeek_GitHub_Setup_ALL.ps1` | первый «единый» installer | Нет | Не в GitHub |
| `DeepSeek_GitHub_Setup_v3.ps1` | версия после npm wrapper fix | Нет | Не в GitHub |
| `DeepSeek_GitHub_Setup_FINAL.ps1` | ошибочно названный FINAL | Нет; имя признано плохим | Не в GitHub |
| `DeepSeek_GitHub_Setup_v0.4.0.ps1` | переименование FINAL в нормальную версию | Нет | Не в GitHub |
| `DeepSeek_GitHub_Setup_v0.4.1.ps1` | добавлены URL/log/device flow | Нет | Не в GitHub |
| `DeepSeek_GitHub_Setup_v0.4.2.ps1` | pwsh, Windows/pnpm fixes | Нет | Не в GitHub |
| `DeepSeek_GitHub_Setup_v0.4.3.ps1` | попытка исправить YAML | Нет | Не в GitHub |
| `DeepSeek_GitHub_Setup_v0.4.4.ps1` | успешнее дошёл до запуска; затем выявлен token-store bug | Нет | Не в GitHub |
| `DeepSeek_GitHub_Setup_v0.4.5.ps1` | попытка исправить credential storage и полный preflight | Исторически можно не сохранять | Не в GitHub |
| `DeepSeek_GitHub_Setup_v0.4.6.ps1` | DeepSeek API network/TLS/proxy/key/balance preflight | Необязательно; superseded | Не в GitHub |
| `DeepSeek_GitHub_Setup_v0.4.7.ps1` | последняя GIT-only версия | **Опционально**, только как forensic snapshot; НЕ проверена end-to-end | Не найден в GitHub |

Последний файл имеет SHA-256:

- `DeepSeek_GitHub_Setup_v0.4.7.ps1`
- `32d15e2c793405ce88e07b775988b6fb1863305bac047a6bc57be06fe87b2814`

**Архивная оценка:** точный код `v0.4.7` не считается необходимым для сохранения смыслового контекста, потому что он не прошёл end-to-end acceptance. Полезные требования, ошибки и решения из него перечислены в этом Graveyard.

## 6.2. `.dsh.zip`

Артефакт:

- `.dsh.zip`
- размер около 58 MiB;
- SHA-256 `c79984a1ae3a6b0be09001d397aa34974c671a8826e16583759ce5872e688233`.

Содержал snapshot `.dsh`, включая:

- профиль Harness;
- `@deepseek-ai/dsh-mcp-client`;
- `node_modules`;
- `pnpm-store`;
- backup;
- encrypted GitHub token file.

Полезные находки:

- `profiles/web/package.json` содержал `@deepseek-ai/dsh-mcp-client: 0.1.2-rc.1`;
- `profiles/web/cordis.patch.yml` в snapshot был штатным файлом с комментариями и `[]`;
- `.npmrc` содержал `package-import-method=copy`, но store всё ещё располагался в старой user-profile `.dsh`.

**Сохранять отдельно?** Обычно нет. Snapshot тяжёлый и содержит credential-related material. Смысловые выводы сохранены здесь.

## 6.3. Экспорт DeepSeek-сессии

Артефакт:

- `dsh-session-session-abea90f9-bbba-44d0-b7f7-42183330eb98.zip`
- SHA-256 `ab26f28fb508afb884bb1b5d72eeb40ca71ebe0761d04f5aff23fd379071269c`.

Полезные доказательства:

- working directory `C:\Irvis-UPG\GIT`;
- provider/model;
- 44 GitHub MCP tools;
- merge tool отсутствует;
- 5 повторов DeepSeek API;
- финальная ошибка `TRANSPORT`.

**Сохранять отдельно?** Не обязательно, если достаточно этого архива. Имеет ценность только как forensic Evidence.

## 6.4. Harness log

Артефакт:

- `DeepSeek-Harness-20260908-165443.log`
- SHA-256 `dc7bc892c6d73db5cce310d003d74a23d8e0596b2760fa65f6d3a65895e7dec1`.

Содержал факт запуска Web UI на `127.0.0.1:3080`.

В raw log присутствовал локальный URL с временным web token.

**Сохранять отдельно?** Нет. Ephemeral web token не следует архивировать.

## 6.5. Скриншоты

В чате были скриншоты:

1. Claude — `Add custom connector`, endpoint GitHub MCP и OAuth options.
2. GitHub — `Register a new OAuth app`.
3. GitHub — широкая страница OAuth permissions.
4. GitHub — более узкая authorization page с private repositories.
5. DeepSeek Harness — Internal Testing Notice.
6. DeepSeek Harness — запрос DeepSeek API key.
7. DeepSeek Harness — основное окно Web UI.
8. DeepSeek Harness — ошибка model request `TRANSPORT`.
9. DeepSeek Harness — Settings → Models → DeepSeek с сохранённым API key.

**Сохранять отдельно?** Нет, если не нужен визуальный forensic audit. Все полезные текстовые факты со скриншотов перенесены в этот файл.

## 6.6. Что намеренно НЕ архивируется

Следующие значения не включены в Graveyard и не должны восстанавливаться из истории:

- GitHub PAT;
- DeepSeek API key;
- GitHub OAuth Client Secret;
- OAuth authorization code;
- OAuth `state`;
- PKCE `code_challenge`;
- GitHub device code;
- локальный DeepSeek Harness web token;
- содержимое encrypted DPAPI credential;
- любые другие секреты.

Это не потеря полезного проектного знания. Такие значения являются credentials/ephemeral data и должны иметь собственный безопасный lifecycle.

---

# 7. Внешние источники

## 7.1. Проект и доноры

- KAT9I_OS: https://github.com/rassvetpublic-spec/KAT9I_OS
- AG25: https://github.com/rassvetpublic-spec/AG25
- NewDeep67/kat9i_skills: https://github.com/NewDeep67/kat9i_skills
- NewDeep67/KAT9I_IIIJIIOXA: https://github.com/NewDeep67/KAT9I_IIIJIIOXA

## 7.2. GitHub MCP

Официальный GitHub MCP Server:

- https://github.com/github/github-mcp-server

Server configuration:

- https://github.com/github/github-mcp-server/blob/main/docs/server-configuration.md

В разговоре использовался remote endpoint:

- `https://api.githubcopilot.com/mcp/`

Официальная конфигурация GitHub MCP поддерживает:

- toolsets;
- individual tools;
- exclude tools;
- read-only mode;
- scope filtering.

Важно для истории: `X-MCP-Exclude-Tools` имеет приоритет над включёнными toolsets.

## 7.3. GitHub auth

GitHub device login:

- https://github.com/login/device

Developer settings:

- https://github.com/settings/developers

Fine-grained PAT settings:

- https://github.com/settings/personal-access-tokens

## 7.4. Claude

- https://claude.ai

Наблюдавшийся OAuth callback при custom connector:

- `https://claude.ai/api/mcp/auth_callback`

В чате не был сохранён отдельный официальный документ Anthropic, однозначно фиксирующий выбранную custom GitHub OAuth policy; поэтому детали Claude в этом архиве основаны прежде всего на фактических UI-экранах и историческом разговоре.

## 7.5. DeepSeek Harness

Официальный репозиторий:

- https://github.com/deepseek-ai/deepseek-harness

MCP client:

- https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/mcp/mcp-client/README.md

Исторически подтверждённый способ запуска Web UI:

- `npx @deepseek-ai/dsh web`

Default Web UI:

- `http://127.0.0.1:3080`

Проект находился в developer preview и предупреждал о compatibility-breaking changes.

## 7.6. DeepSeek API

API base:

- https://api.deepseek.com

API keys:

- https://platform.deepseek.com/api_keys

API docs:

- https://api-docs.deepseek.com/

Balance endpoint docs:

- https://api-docs.deepseek.com/zh-cn/api/get-user-balance/

Error codes:

- https://api-docs.deepseek.com/quick_start/error_codes/

Status:

- https://status.deepseek.com/

На момент разговора официальный API документировал:

- Bearer auth;
- `deepseek-v4-flash`;
- `/user/balance`;
- 401 для bad key;
- 402 для insufficient balance.

## 7.7. Node.js

- https://nodejs.org/

В ходе чата Node.js LTS был установлен автоматически через Windows package manager; фактически использовалась версия `v24.19.0`.

---

# 8. Краткая хронология

## Этап 1 — Claude как QA

1. Пользователь открыл Claude custom connector для GitHub MCP.
2. Обсуждалась OAuth-конфигурация.
3. Создана OAuth App `Claude GitHub QA`.
4. GitHub показал широкие permissions.
5. Пользователь уточнил требование: private repos нужны, но Claude должен быть reviewer/советником, а не admin.
6. Scope-модель была мысленно сужена до QA-oriented least privilege.

## Этап 2 — второй GitHub-аккаунт

7. Пользователь захотел подключить второй свой GitHub.
8. Сначала рассматривался collaborator-доступ через основной аккаунт.
9. Read-only проверка показала отдельную GitHub App installation для `NewDeep67`.
10. Выяснилось, что текущий ChatGPT connector уже может видеть repo `NewDeep67` отдельно.

## Этап 3 — DeepSeek как второй инженер

11. Пользователь попросил аналогичный доступ для DeepSeek.
12. Была выбрана архитектура DeepSeek Harness + GitHub MCP.
13. Создан отдельный fine-grained GitHub token.
14. В качестве исторической модели прав выбрали инженерный RW без Administration/Secrets.
15. Merge предполагалось блокировать через исключение `merge_pull_request`.

## Этап 4 — первая автоматизация

16. Создан первый PowerShell installer.
17. Node.js отсутствовал и был автоматически установлен.
18. Node оказался `v24.19.0`.
19. Первый npm install упал с `SELF_SIGNED_CERT_IN_CHAIN`.
20. Появилась гипотеза корпоративного CA/proxy.

## Этап 5 — серия ошибок установщика

21. Один installer ошибочно вызвал npm так, что npm показал help вместо реальной network check.
22. После исправления `npm warn allow-scripts` был ошибочно принят PowerShell как фатальная ошибка.
23. Пользователь потребовал один единый installer и нормальное версионирование.
24. От `FINAL` отказались.
25. Линия стала `v0.4.0`, `v0.4.1`, ...

## Этап 6 — PowerShell 7 и pnpm

26. Пользователь отверг `.cmd`, потребовал `pwsh`.
27. pnpm столкнулся с Windows `os error 5 / Access is denied`.
28. Пробовали pinned pnpm и copy import mode.
29. MCP client в итоге установился как `0.1.2-rc.1`.
30. Harness warning `declares no dsh.bundle` был признан warning, а не фатальной ошибкой.

## Этап 7 — YAML

31. `cordis.patch.yml` содержал comments + `[]`.
32. Installer добавлял после `[]` второй YAML list.
33. Harness падал с `YAMLException`.
34. В следующих версиях стали заменять пустой array или корректно расширять top-level list.
35. Добавили rollback исходного `cordis.patch.yml`.

## Этап 8 — launcher и token store

36. Harness Web UI стал запускаться на `http://127.0.0.1:3080`.
37. Пользователь потребовал всегда явно печатать URL.
38. Старый DPAPI token store прочитался некорректно.
39. `ConvertTo-SecureString` упал.
40. В результате Authorization header GitHub MCP стал malformed.
41. Последующие версии меняли credential storage/readback.

## Этап 9 — Harness UI и DeepSeek API key

42. Пользователь увидел Internal Testing Notice.
43. Затем окно `Add an API key to get started`.
44. DeepSeek API key был введён через Settings → Models.
45. Главный Harness UI открылся.

## Этап 10 — GitHub MCP работает, модель не работает

46. Пользователь отправил запрос показать private GitHub repos.
47. Модель не ответила: `DeepSeek API request to https://api.deepseek.com failed`.
48. Harness сделал 5 retry.
49. Экспорт сессии подтвердил, что GitHub MCP tools уже были загружены.
50. Значит блокер переместился с GitHub/MCP на DeepSeek model transport.

## Этап 11 — сетевой preflight

51. `v0.4.6` был создан как попытка добавить:
    - DNS;
    - Windows CA;
    - proxy;
    - DeepSeek API key;
    - balance;
    - HTTP error classification.
52. End-to-end подтверждения успешного model call после этого в чате нет.

## Этап 12 — GIT-only

53. Пользователь установил новое правило: установщики, настройки, логи и связанный state не должны выходить за `C:\Irvis-UPG\GIT`.
54. Был создан `v0.4.7` с попыткой перенести `DSH_HOME`, caches, GitHub CLI config, Git config, logs и launcher внутрь GIT.
55. `v0.4.7` не был показан в успешном прогоне.
56. После этого пользователь решил удалить чат и запросил Graveyard archive.

---

# 9. Исторические инженерные уроки из чата

Этот раздел также `DATA ONLY`.

1. **Не смешивать health разных слоёв.**  
   Web UI alive ≠ model API alive ≠ GitHub MCP alive ≠ GitHub permissions correct.

2. **Не объявлять `ГОТОВО` до end-to-end проверки.**  
   В чате несколько раз промежуточный успех скрывал следующий отказ.

3. **Установщик должен быть идемпотентным.**  
   Если MCP уже установлен, его повторная установка создаёт новые риски.

4. **Windows tooling требует отдельной дисциплины.**  
   CA, proxy, ACL, pnpm store, hardlinks и PowerShell stderr semantics реально влияли на результат.

5. **Конфигурационный файл нельзя модифицировать по предположению.**  
   Реальный `cordis.patch.yml` содержал comments + `[]`, что сломало наивный append.

6. **Credentials требуют отдельной проверяемой модели хранения.**  
   Даже encrypted token useless, если launcher не умеет стабильно прочитать его обратно.

7. **Tool exclusion полезен, но не равен полномочиям.**  
   Отсутствие merge tool не мешает агенту иметь другие сильные write tools.

8. **Provider preview быстро меняется.**  
   DeepSeek Harness developer preview делает installer version-sensitive.

9. **Пользовательские пути — часть контракта эксплуатации.**  
   В конце чата GIT-only стал важнее «стандартного» `%USERPROFILE%\.dsh`.

10. **Версия файла — Evidence истории.**  
    `FINAL` не является версией. Чат перешёл на `v0.4.x`.

---

# 10. Что будет потеряно при удалении этого чата

После сохранения/импорта данного Graveyard-файла смысловой контекст чата считается покрытым следующим образом:

## Уже остаётся в GitHub

- каноническая GitHub/QA модель;
- Issue #1, #87, #90, #91;
- PR #92 merged;
- PR #93 Draft;
- связанные QA/Promotion идеи;
- основная архитектура KAT9I_OS.

## Сохранено в этом Graveyard

- Claude GitHub QA setup history;
- причины least privilege;
- multi-account observation ChatGPT/NewDeep67;
- DeepSeek Harness role;
- GitHub PAT/MCP design;
- фактическая Windows-среда;
- все существенные ошибки установщиков;
- история версий;
- GIT-only rule;
- pwsh preference;
- device auth expectation;
- GitHub MCP tool inventory evidence;
- DeepSeek API TRANSPORT failure;
- unresolved questions;
- external sources;
- artifact inventory;
- chronology.

## Что намеренно НЕ переносится

Не переносятся секреты и одноразовые данные:

- PAT;
- API keys;
- OAuth secrets/codes/state;
- device codes;
- localhost web token;
- encrypted credential bytes.

Это **не является полезным проектным контекстом**, и такие значения не должны жить в Graveyard.

## Что не встраивается побайтно

Не встроены:

- raw screenshots;
- 58 MiB `.dsh.zip`;
- полный session export;
- старые installer scripts;
- точный код `v0.4.7`.

Их **полезное семантическое содержание перенесено выше**. `v0.4.7` не был принят и не прошёл end-to-end verification, поэтому его точный executable body не считается обязательным историческим знанием.

Если нужен forensic snapshot конкретного скрипта/архива, его следовало бы сохранить отдельно до удаления чата, но для понимания истории проекта это не требуется.

---

# SAFE TO DELETE CHAT AFTER GRAVEYARD IMPORT

Эта строка означает только следующее:

- после сохранения данного `.md` как исторического DATA-архива существенный **смысловой** контекст этого чата больше не должен существовать только внутри чата;
- строка **не разрешает** никакие изменения проекта;
- строка **не переводит** идеи из Graveyard в backlog;
- строка **не является** `mtd`;
- строка **не является** QA PASS;
- строка **не является** Promotion authorization.
