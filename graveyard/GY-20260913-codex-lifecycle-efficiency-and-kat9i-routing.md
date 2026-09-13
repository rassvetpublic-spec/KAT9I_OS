# GRAVEYARD / DATA ONLY / NON-CANONICAL / NON-ACTIONABLE / NO AUTO-PROMOTION

**Archive ID:** `GY-20260913-codex-lifecycle-efficiency-and-kat9i-routing`  
**Проект:** `KAT9I_OS`  
**Тип записи:** дистиллированные знания из рабочего чата  
**Источник:** обсуждение standalone Codex Desktop / Work / ChatGPT, 2026-09-13  
**Статус:** `DATA ONLY / NON-CANONICAL / NON-ACTIONABLE`  
**Автопродвижение:** `FORBIDDEN`

> Эта запись сохраняет архитектурные наблюдения и идеи для будущего обсуждения. Она не является Issue, ADR, TaskContract, backlog, политикой исполнения или разрешением на изменение KAT9I_OS. Любое возвращение материала в рабочий контур требует сверки с текущим `main` и отдельного решения владельца.

---

## 1. Главная ментальная модель Codex

Codex полезно понимать не как «LLM с терминалом», а как агентный цикл:

`thread → instruction resolution → context assembly → model inference → tool decision → permission gate → sandbox/environment → tool result → next inference → edit → validation → stop/final`

Один пользовательский prompt может вызвать несколько model↔tool циклов. Поэтому число пользовательских сообщений не равно реальному расходу agentic allowance.

Основные независимые оси:

1. **Product surface:** ChatGPT Chat / Work / Codex.
2. **Model:** Luna / Terra / Sol / Astra и другие доступные модели.
3. **Reasoning effort:** Light / Medium / High и т.п.
4. **Environment:** Local / Worktree / Cloud.
5. **Permissions:** read-only / workspace / full access.
6. **Instruction stack:** system + global AGENTS + repo/nested AGENTS + skills/plugins + prompt.

Не смешивать эти оси. Например, `Full access` — это capability boundary, а не уровень интеллекта; `Light` — reasoning effort, а не отдельный продуктовый режим.

---

## 2. Chat / Work / Codex

Рабочее разделение:

- **ChatGPT Chat** — мышление, обсуждение, архитектура, формулировка ТЗ, review идей.
- **Work** — длинная general-purpose агентная работа, исследования и артефакты.
- **Codex** — software engineering с filesystem/git/shell/repo context.

Практический принцип экономии:

`думать в Chat → сформулировать точную задачу → выполнять в Codex → остановиться после acceptance criteria`

Work и Codex следует считать общим дорогим agentic-контуром; обычный Chat использовать как дешёвый слой рассуждений, когда локальные инструменты не нужны.

---

## 3. Thread и context economics

Thread — временная рабочая память, не долговременное хранилище проекта.

Рекомендуемая граница:

`PROJECT = область работы`
`THREAD = один outcome`

Пример:
- thread A: issue #145;
- thread B: issue #136;
- thread C: отдельный архитектурный анализ.

Не следует тащить завершённый outcome в следующий несвязанный thread. Чем длиннее история, тем больше context assembly, тем дороже каждый последующий model call и тем выше риск compaction/re-read/rework.

Compaction — механизм удержания длинной истории в context window, но не архитектура долговременной памяти. Важные решения должны жить в repo: Issues, ADR, docs, config, tests, commits, PR evidence.

Принцип:

`repo = durable memory`
`thread = transient working memory`

---

## 4. Где реально растёт расход

Наибольшие множители:

1. дорогая модель + высокий reasoning;
2. большой накопленный context;
3. много subagents / широкий fan-out;
4. огромные tool outputs;
5. много model↔tool циклов;
6. повторное чтение уже известных файлов;
7. full test suites без необходимости;
8. длинные повторяющиеся summaries.

Особенно опасен широкий локальный вывод. Команда сама может быть дешёвой, но её результат становится частью model context.

Плохие шаблоны:
- рекурсивный полный листинг;
- чтение огромного лога целиком;
- `git log --all` без ограничения;
- повторное чтение неизменившихся файлов;
- восемь агентов, каждый анализирует весь repo.

Предпочтительные шаблоны:
- `rg`/точный search;
- exact file;
- small line ranges;
- `Tail` для логов;
- targeted tests;
- bounded fan-out;
- reuse already established facts.

---

## 5. Model escalation ladder

Идея для эффективного routing:

`Luna Light → Terra Light → Sol Medium → Astra Light/Medium`

Эскалация только если предыдущий уровень недостаточен по сложности, неопределённости, риску или после неудачной попытки.

Типовой routing:

- **Luna:** точные routine-действия, git status, найти файл, небольшая правка, простой test.
- **Terra:** обычный bugfix, несколько связанных файлов, небольшой refactor.
- **Sol:** сложный bug, race, substantial review, архитектурный refactor.
- **Astra:** тяжёлое расследование, неоднозначная архитектура, большой repo, competing hypotheses.

Антипаттерн: использовать Astra для deterministic routine work.

---

## 6. Tool loop и permission architecture

Типовой цикл:

`MODEL → tool request → permission/sandbox check → execution → observation → MODEL`

Permissions определяют **CAN**, а AGENTS/policy — **SHOULD**.

Пример:
- Full access технически позволяет `git merge`;
- repo policy может запрещать merge без MTD.

Full access может уменьшать количество approval round-trips, но не снижает стоимость model inference и не отменяет policy.

---

## 7. AGENTS.md и config.toml

Разделение ответственности:

- `config.toml` — control plane runtime: model, reasoning, permissions, sandbox, MCP/features/environment и т.п.
- `AGENTS.md` — поведенческая policy: как искать, как тестировать, когда останавливаться, какие repo rules соблюдать.

Instruction hierarchy концептуально:

`system → global CODEX_HOME/AGENTS.md → repo AGENTS.md → nested/override AGENTS → prompt`

Global AGENTS должен быть небольшим и универсальным. KAT9I-specific правила должны жить на repo-level или ниже.

Полезная глобальная efficiency-policy:
- targeted search/read;
- deterministic-first;
- minimum sufficient reasoning;
- bounded fan-out;
- smallest meaningful validation first;
- compact output;
- reuse established context;
- avoid redundant rereads;
- stop when requested outcome and required checks are complete.

---

## 8. Stop condition как token brake

После прохождения acceptance criteria агент должен остановиться.

Антипаттерн:
`исправил → ещё соседний audit → ещё full test → ещё docs → ещё refactor`

Предпочтительно:
`targeted change → targeted validation → required broader checks only if justified → final → stop`

Это отдельный механизм экономии, а не косметика prompt style.

---

## 9. Worktree как изоляция параллельных workers

Для KAT9I-подобного multi-worker процесса естественная схема:

`main repo`
`├─ worker A → worktree/branch issue-A`
`├─ worker B → worktree/branch issue-B`
`└─ worker C → worktree/branch issue-C`

Каждый worker получает отдельное рабочее дерево и outcome, затем branch → commit → PR → QA → MTD.

Worktree следует рассматривать как environment/isolation primitive, а не как policy или memory layer.

---

## 10. Две будущие ветки для отдельного обсуждения

### Ветка A — локальные изменения Codex control plane

Возможные темы для сверки и проектирования:

- профессиональная структура `C:\CODEX\home`;
- минимальный global `AGENTS.md`;
- безопасный `config.toml`;
- model/reasoning routing defaults;
- permissions profiles;
- Local / Worktree / Cloud defaults;
- hooks/skills/plugins/MCP;
- observability расхода и thread lifecycle;
- local fallback;
- автоматический выбор дешёвой модели и эскалация;
- thread hygiene и session retention;
- проверка effective instructions;
- rollout/rollback/versioning глобальных правил.

Это только seed для будущего анализа. Никаких изменений локальной конфигурации из этой Graveyard-записи выполнять нельзя.

### Ветка B — как перенести принципы в KAT9I_OS

Идеи для будущей сверки с текущим каноном:

- формализовать task routing по классам THINK / RESEARCH / CODE / AUTOMATE;
- выбирать worker/model tier по сложности и риску;
- ввести bounded fan-out budget;
- хранить durable memory в repo, а не в длинных чатах;
- один TaskContract/outcome на worker thread;
- targeted retrieval и context budget;
- запрет повторного чтения неизменившихся evidence без причины;
- smallest meaningful validation first;
- явный stop condition;
- worktree-per-worker там, где это оправдано;
- telemetry: context size proxy, tool-output size, model/tool loop count, re-read rate, validation cost;
- promotion/escalation только по измеримым триггерам;
- repo-level AGENTS как policy layer поверх глобального Codex efficiency baseline;
- не переносить глобальные Codex-specific детали в KAT9I canon без отдельной архитектурной сверки.

---

## 11. Кандидатные метрики для будущего исследования

Не канон, только гипотезы:

- `tool_calls_per_outcome`;
- `model_turns_per_outcome`;
- `tool_output_bytes`;
- `duplicate_reads`;
- `full_file_reads / targeted_reads`;
- `subagent_fanout`;
- `validation_scope`;
- `rework_turns`;
- `thread_age / outcome_count`;
- `escalation_count`;
- `cheap_model_completion_rate`;
- `cost_or_allowance_proxy_per_completed_task`.

Главная цель метрик — не «минимум токенов любой ценой», а стоимость завершённого корректного outcome при сохранении качества и required validation.

---

## 12. Сводка исторического знания

Ключевые тезисы для будущего «раскапывания»:

- Codex — agent loop, а не единичный LLM-call.
- Самые дорогие факторы — context, model tier, reasoning, fan-out и observations/tool output.
- Thread должен быть bounded одним outcome.
- Durable memory должна жить в repo.
- Targeted retrieval и targeted validation дают большую экономию без потери качества.
- Model escalation предпочтительнее постоянного использования максимальной модели.
- Permissions, environment, model, reasoning и instructions — независимые архитектурные оси.
- `config.toml` и `AGENTS.md` решают разные задачи.
- Stop condition является важным control для agentic cost.
- Для KAT9I эти принципы потенциально применимы как routing/context/worker architecture, но требуют отдельной сверки с текущим каноном.
