# Карта архитектурной ответственности модулей KAT9I_OS

## 1. Назначение документа

Настоящий документ фиксирует каноническую карту архитектурной ответственности доменов и модулей KAT9I_OS в соответствии с принятыми спецификациями (`docs/spec/` и `docs/architecture/`).

> **Ключевой инвариант:**
> Архитектурная ответственность за модуль и механизм автоматического назначения review (`.github/CODEOWNERS`) строго разделены:
> 1. Архитектурная карта определяет, кто проектирует модуль, отвечает за его инварианты и целостность контрактов.
> 2. `CODEOWNERS` — это исключительно сервисный механизм GitHub для маршрутизации review (проверки изменений), который не является источником архитектурных полномочий и не выдаёт административных прав.
> 3. Назначение ответственного за домен не означает автоматического назначения его исполнителем (Worker) каждого связанного Issue или PR.

---

## 2. Сводная карта ответственности

| Домен / Модуль | Канонический раздел документации | Архитектурный ответственный | Описание и границы ответственности |
|---|---|---|---|
| **Ядро и оркестрация (Core & Lifecycle)** | `docs/architecture/20_TASK_LIFECYCLE_AND_ORCHESTRATION.md`, `docs/architecture/03_TASK_CONTRACT.md` | Владелец проекта (`rassvetpublic-spec`) | Жизненный цикл задачи, переходы состояний, TaskContract, FSM, ResultSink. |
| **Правила и безопасность (Rule Manager & Security)** | `docs/architecture/04_RULES_AND_EXECUTION_PRIORITIES.md`, `docs/spec/24_GITHUB_PROJECT_MANAGEMENT.md` | Владелец проекта (`rassvetpublic-spec`) | Иерархия правил (ENGINE > USER > PROJECT > TASK), fail-closed шлюзы, разграничение CONTROL/DATA, приватность. |
| **Распределённые исполнители (Coworker)** | `docs/architecture/11_COWORKER.md` | Владелец проекта (`rassvetpublic-spec`) | Реестр Worker Registry, Claim, Lease, Heartbeat, изоляция исполнителей, независимый QA. |
| **Контекст и ресурсы (Context, Knowledge & Resources)** | `docs/architecture/07_CONTEXT.md`, `docs/architecture/08_KNOWLEDGE_BASE.md`, `docs/architecture/09_RESOURCES.md` | Владелец проекта (`rassvetpublic-spec`) | Разделение Context (оперативный) vs Knowledge (накопленный), ResourceRef, кэширование, дедупликация. |
| **Маршрутизация интеллекта (Inference & Routing)** | `docs/architecture/10_INFERENCE_AND_DECISION_ROUTING_RU.md` | Владелец проекта (`rassvetpublic-spec`) | Выбор классов моделей, Executable-First, расчет затрат токенов, детерминированные маршруты. |
| **Планирование и прогнозирование ресурсов** | `docs/architecture/19_RESOURCE_PLANNING_AND_FORECASTING.md` | Владелец проекта (`rassvetpublic-spec`) | Оценка ресурсов до запуска (Pre-execution forecast), динамический пересчет, план/факт анализ. |
| **Самообучение (Learning & Self-Improvement)** | `docs/architecture/06_LEARNING_SELF_IMPROVEMENT.md` | Владелец проекта (`rassvetpublic-spec`) | Анализ Evidence и Metrics, безопасные предложения оптимизаций, перенос эвристик в код. |
| **Персональный слой (Personal Layer)** | `docs/architecture/18_PERSONAL_LAYER.md` | Владелец проекта (`rassvetpublic-spec`) | Индивидуальные настройки пользователя, доверенные профили, локальные предпочтения. |
| **Визуализация процессов (Process Visualization)** | `docs/architecture/17_PROCESS_VISUALIZATION.md` | Артём (`Art3m1da`) | Локальный веб-интерфейс, схема модулей в реальном времени, read-only наблюдение телеметрии и графов. |
| **Генерация документации и витрина (HTML Generator & UI)** | `docs/spec/24_GITHUB_PROJECT_MANAGEMENT.md`, Issue #2, #6 | Артём (`Art3m1da`) | Сборка производного HTML из канонических Markdown, переключатели подробности, режим «Я здесь впервые». |

---

## 3. Политика CODEOWNERS в GitHub

1. **Репозиторий по умолчанию:**
   - Общим владельцем по умолчанию для всех файлов репозитория является `@rassvetpublic-spec`.
2. **Доменные назначения в CODEOWNERS:**
   - Доменные владельцы (включая `@Art3m1da` для визуализации и UI-представлений) добавляются в `.github/CODEOWNERS` по мере настройки их доступа в репозитории на GitHub.
   - До момента подключения персональных доступов запросы на review централизованно маршрутизируются на `@rassvetpublic-spec`.
3. **Разрешение конфликтов:**
   - При любых изменениях, затрагивающих несколько модулей, приоритет имеют инварианты Безопасности и Ядра (`Core`, `Rules`, `Security`).
