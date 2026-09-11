# Kat9I v1 — Current Discovery Synthesis

## Статус
CURRENT / DISCOVERY.

Этот документ не объявляет Architecture v1 принятой. Он кратко фиксирует текущее понимание первой архитектурной итерации и должен обновляться по мере Discovery.

## Current baseline

Действующая архитектура репозитория продолжает применяться операционно до принятой замены.

Для архитектурного анализа она считается `CURRENT BASELINE v0`, а не автоматически лучшим или окончательным решением.

## Главная задача итерации

Issue #178 проводит brainstorm ТЗ и Architecture Tournament.
RAW-контекст первой итерации сохранён в Issue #177.

## Гипотезы высокого приоритета

### Portable bootstrap
`КАТЯ-ВХОД` — единая точка входа любого AI, которая должна находить актуальный trusted context, роль/capability, задачу и ограничения без создания второго SSoT.

### Compact Worker Output
Worker должен выдавать короткий структурированный результат, пригодный человеку и автоматике. Кандидатные поля: ROLE, STATUS, TASK, RESULT, EVIDENCE, METRICS, TAGS, NEXT; для блокировки — CAUSE/NEED.

### Cheap telemetry
На старте полезны минимальные ручные metrics (`checks`, `findings`, `rework`, `confidence`) и 5–10 context tags. Метрики, доступные из GitHub автоматически, в будущем следует вычислять машиной, а не заставлять Worker дублировать их текстом.

### Safe modes
`QAA` рассматривается как portable read-only QA/Review mode, а не отдельная authority-система.
`AMTD` рассматривается как автономная работа до запрещённого Gate, но не как automatic merge.

### Learning layer
Первая гипотеза самообучения: Task → Action → Result → QA/Owner feedback → Learning Event → retrieval похожих случаев. Fine-tuning и автономное изменение правил не являются первым шагом.

### Flow architecture
Kanban, FIFO, priority queue, dependency-driven, goal-driven и hybrid scheduling должны сравниваться как конкурирующие решения. Текущая Project-модель не считается победителем без Architecture Tournament.

### Hooks
Hooks рассматриваются и как automation layer, и как возможный event runtime. Выбор архитектуры откладывается до сравнения кандидатов.

## Architecture Tournament
Первая серия кандидатов:

- A — Current evolved architecture;
- B — Thin orchestrator: Context + Policy + Events;
- C — Event-driven runtime: Hooks + event log + agents;
- D — Blackboard/shared-state architecture;
- E — Hybrid: GitHub control-plane + Kat9I event/runtime.

Сравнение должно использовать одинаковые критерии: safety/trust, simplicity, implementation cost, token/tool cost, portability, auditability, learning, failure recovery, GitHub lock-in, scaling, migration cost, human UX.

## Knowledge lifecycle

Гипотеза текущей модели знаний описана в `docs/context/KNOWLEDGE_LIFECYCLE.md`.

Базовые статусы: HYPOTHESIS, EXPERIMENT, CURRENT, ACCEPTED, SUPERSEDED.

## Что пока не цементировать

До завершения Discovery не считать окончательными:

- постоянный набор Worker roles;
- Controller=ChatGPT как вечную архитектурную сущность;
- конкретную форму QA handshake;
- Kanban/FIFO/PromotionStore как обязательный фундамент;
- конкретную Hook-архитектуру;
- механизм самообучения;
- формулу priority;
- долгосрочный набор Project views.

При этом действующие safety/control правила продолжают соблюдаться, пока не заменены принятым изменением.
