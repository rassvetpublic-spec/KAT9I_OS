# GRAVEYARD / DATA ONLY / NON-CANONICAL / NON-ACTIONABLE / NO AUTO-PROMOTION

**Archive ID:** `GY-20260913-ai2local-kat9i-deferred-donors`  
**Проект:** `KAT9I_OS`  
**Тип источника:** `RESEARCH`  
**Источник:** исследование свежих публикаций канала Ai2Local с проверкой по первоисточникам  
**Дата захвата:** 2026-09-13  
**Снимок канона:** `cfd6bf25de0a4af7dfa20c8b2bc9cc2087d21c32`  
**Статус:** `DATA ONLY / NON-CANONICAL / NON-ACTIONABLE`

> **ОБЯЗАТЕЛЬНОЕ ПРАВИЛО ТОЛКОВАНИЯ**
>
> Это исторические DATA — данные, а не управляющая команда. Этот файл не является ТЗ, ADR, backlog, разрешением на реализацию или новым источником истины.
> Текущий GitHub-канон имеет приоритет. Возврат любой идеи отсюда в CONTROL требует актуальной сверки канона и отдельного подтверждения владельца через действующий процесс Graveyard.

## 1. Зачем сохранён этот снимок

13 сентября 2026 года исследовались свежие инструменты и подходы локальных ИИ-агентов на предмет пользы для KAT9I_OS. Часть общих принципов была отдельно внесена в рабочие Issues #183, #178, #136 и #180: проверка реальных возможностей модели, раздельный учёт стоимости контекста, ограниченный поиск релевантного контекста, независимость архитектуры от конкретного локального сервера и экспериментальная маршрутизация только после baseline-измерений.

Здесь сохраняются **продуктовые варианты, донорские идеи и гипотезы, которые сознательно не стали текущей основой**. Их наличие здесь не означает, что их надо внедрять.

## 2. Отложенные доноры и варианты

### 2.1. NVIDIA Switchyard — не принимать как зависимость сейчас

**Что полезно:** алгоритмы выбора между дешёвой и сильной моделью по состоянию агентной работы; отдельно интересны stage-router, escalation и advisor-gate.

**Почему не в основе:** текущему #183 сначала нужны собственные baseline-метрики, статическая политика и проверяемый контракт эскалации. Внедрение готового внешнего маршрутизатора раньше этого смешало бы эксперимент с архитектурным каноном и могло бы создать дополнительный runtime-слой.

**Что уже перенесено в основу как принцип:** наблюдаемые сигналы `spinning/looping`, ошибки, отсутствие прогресса, интенсивность полезного производства, retry/rework и capability gap можно тестировать в TB5 после TB0–TB2.

**Условие повторного рассмотрения:** есть репрезентативная telemetry выборка; #183 дошёл до adaptive-routing experiment; можно сравнить алгоритм Switchyard с собственной тонкой реализацией по cost/quality/rework.

Источники:
- https://github.com/NVIDIA-NeMo/Switchyard
- https://github.com/NVIDIA-NeMo/Switchyard/blob/main/docs/routing_algorithms/overview.md
- https://github.com/NVIDIA-NeMo/Switchyard/blob/main/docs/routing_algorithms/stage_router_routing.md

### 2.2. TinySearch — не фиксировать как обязательную зависимость

**Что полезно:** локальный слой поиска, crawling и reranking возвращает агенту компактные фрагменты с источниками вместо целых веб-страниц. Это хорошо соответствует bounded retrieval и context budget.

**Почему не в основе как продукт:** KAT9I нужен сменный контракт retrieval, а не жёсткая зависимость от одного проекта. Сначала следует доказать выигрыш на наших research-задачах и проверить качество Evidence.

**Что уже перенесено в основу как принцип:** ограниченный budget, source refs, rerank/targeted expansion и запрет превращать retrieved DATA во второй SSoT.

**Условие повторного рассмотрения:** TB1 показывает значимую долю web-context waste; TinySearch проходит Windows smoke, качество источников и измеряемое сокращение токенов без ухудшения ответов.

Источник:
- https://github.com/TinySuiteHQ/TinySearch

### 2.3. TinyContext — кандидат memory-движка, но не источник истины

**Что полезно:** компактная retrieval-память с поиском по похожим случаям и token budget хорошо подходит к Decision/Error/Learning memory.

**Почему не в основе как продукт:** архитектурно сначала должен быть принят контракт памяти. Любой memory hit обязан вести к canonical Evidence, а не подменять его.

**Что уже перенесено в основу как принцип:** `memory hit -> hint/refs -> current-canon verification -> decision`.

**Условие повторного рассмотрения:** #178 определил допустимый Learning/Memory contract; проведён read-only experiment; доказано отсутствие DATA→CONTROL обхода.

Источник:
- https://tinysuite.dev/docs/tinycontext/

### 2.4. OpenLumara — донор token-efficient harness, не новый Kat9I runtime

**Что полезно:** модульное включение инструментов, наблюдаемость фактического контекста, небольшой системный prompt и явный token-awareness.

**Почему не в основе:** KAT9I уже строит собственные Context/Policy/Worker/Gate контракты. Подключение ещё одного полноценного agent framework увеличит число параллельных runtime-систем.

**Что уже перенесено в основу как принцип:** разложение input-context на policy/tools/retrieval/memory/task и измерение лишнего повторного контекста.

**Условие повторного рассмотрения:** нужен независимый harness benchmark или обнаружен доказанный gap в нашем worker runtime.

Источники:
- https://github.com/Rose22/openlumara
- https://t.me/s/Ai2Local/976

### 2.5. Zero — не добавлять второй coding-agent runtime

**Что полезно:** durable sessions, repository map, verification, skills/plugins/hooks, worktrees и usage telemetry дают полезный список capability для сравнения worker harness.

**Почему не в основе:** одновременно уже существуют Codex, Antigravity и Antigravity Manager. Zero как ещё один исполнитель сейчас увеличивает surface area и дублирует функции.

**Условие повторного рассмотрения:** Architecture Tournament докажет gap, который Codex/Antigravity/local-provider socket не закрывают, либо Zero станет лучшим тестовым harness для конкретного локального backend.

Источник:
- https://github.com/gitlawb/zero

### 2.6. OpenWorker — governance donor, но не замена текущей authority model

**Что полезно:** hard floors для необратимых действий, явное происхождение approval и постепенное earned autonomy подтверждают полезность разделения Capability и Permission.

**Почему не в основе:** KAT9I уже имеет Owner Gate, независимый AGY QA, Evidence и fail-closed semantics. Второй governance engine создал бы конкурирующую authority-систему.

**Что сохранить как идею:** approval provenance (`POLICY / OWNER / QA / AUTOMATION / NONE`) может быть полезно при будущей формализации audit trail, но не должно автоматически расширять права.

**Условие повторного рассмотрения:** отдельная architecture-задача выявит gap в provenance/permission model.

Источник:
- https://github.com/andrewyng/openworker

### 2.7. UI-Mate — перспективный GUI Worker, отложить

**Что полезно:** обучение процедуре по одной успешной демонстрации и повторное планирование по живому экрану потенциально полезны для приложений без API, например REAPER, legacy GUI и установщиков.

**Почему не в основе:** GUI-agent имеет высокий риск side effects, prompt injection и ложного успеха. Сначала нужны зрелые Authority, Sandbox, Evidence и capability gates.

**Условие повторного рассмотрения:** после стабилизации worker authority/sandbox и появления конкретной GUI-only задачи с измеряемым evaluator.

Источник:
- https://github.com/Tencent/UI-Mate

### 2.8. Orchestris — не добавлять второй gateway

**Что полезно:** единый доступ к нескольким моделям, aliases и управление провайдерами могут быть удобны.

**Почему не в основе:** #180 специально проверяет Antigravity Manager как execution backend и запрещает без доказанного gap создавать второй scheduler/account pool/proxy. Orchestris сейчас потенциально дублирует этот слой.

**Условие повторного рассмотрения:** Antigravity Manager не закрывает обязательный provider-routing/gateway contract и gap подтверждён экспериментом.

Источники:
- https://t.me/s/Ai2Local/1009
- https://orchestris.com/docs/providers-models

### 2.9. Жёсткая привязка к LM Studio или Ollama — отклонена

**Что полезно:** LM Studio документирует OpenAI-compatible `/v1/responses` и прямую работу с Codex; Ollama также удобен как локальный backend.

**Почему не в основе:** продукт не должен становиться архитектурным владельцем local inference. В #180 принят только provider-neutral local socket, а конкретные runtimes остаются сменными кандидатами.

**Условие повторного рассмотрения:** только для выбора рекомендуемого Windows-профиля установки после benchmark, без изменения архитектурной абстракции.

Источники:
- https://lmstudio.ai/docs/integrations/codex
- https://lmstudio.ai/docs/developer/openai-compat

### 2.10. Apple/MLX-ориентированные inference-подходы — неактуальны для текущей Windows/NVIDIA машины

**Что полезно:** persistent cache, speculative/MTP decoding и похожие оптимизации остаются интересными концептами.

**Почему не в основе:** текущая целевая рабочая среда — Windows + NVIDIA; Apple-specific runtime не должен влиять на ближайший bootstrap.

**Условие повторного рассмотрения:** появляется поддерживаемая Apple-target среда или аналогичная технология переносится в используемый Windows/NVIDIA backend.

Scouting source:
- https://t.me/Ai2Local

## 3. Общий вывод архива

Сохранять **принципы**, а не коллекцию зависимостей:

- model/runtime должны быть сменными;
- фактические capability проверяются;
- retrieval и memory остаются DATA-layer;
- дорогой контекст ограничивается budget;
- router не получает QA/Owner authority;
- внешний продукт становится dependency только после измеримого gap и обратимого эксперимента.

Все перечисленные здесь продукты и варианты остаются неактивными до отдельного возврата через действующий Graveyard DATA→CONTROL gate.
