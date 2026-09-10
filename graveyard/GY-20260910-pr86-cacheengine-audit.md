# GRAVEYARD / DATA ONLY / NON-CANONICAL / NON-ACTIONABLE / NO AUTO-PROMOTION

**Archive ID:** `GY-20260910-pr86-cacheengine-audit`  
**Проект:** `KAT9I_OS`  
**Тип записи:** дистиллированный аудит закрытого PR  
**Источник:** `PR #86 docs(architecture): зафиксировать высокопроизводительный CacheEngine на Rust (#84)`  
**Источник-ветка:** `feat/issue-84-cache-engine-architecture`  
**Источник-ревизия:** `88d40ba6cb4e5143c013490db11dedcc82881a45`  
**Снимок канона при аудите:** `bb7b4702126aabd402f942f2dc71d095110b7d0e`  
**Каноническая реализация исходной задачи:** `PR #85`, merge commit `73e80ddb029cb27cfde117e00c5971064a76f277`  
**Статус:** `DATA ONLY / NON-CANONICAL / NON-ACTIONABLE`  
**Автопродвижение:** `FORBIDDEN`

> Эта запись сохраняет только историческое знание и идеи. Она не является Issue, ADR, TaskContract, backlog, разрешением на изменение проекта или основанием для автоматического переноса файлов из PR #86. Текущий `main` всегда имеет приоритет. Любое возвращение идеи в рабочий контур требует новой сверки с актуальным каноном и явного подтверждения владельца.

---

## 1. Итог аудита

PR #86 закрыт без слияния не потому, что в нём не было полезной работы, а потому, что он стал параллельной и устаревшей реализацией той же задачи #84. К моменту закрытия каноническая архитектура CacheEngine уже была принята через PR #85. Ветка #86 разошлась с `main`, содержала 13 собственных коммитов, меняла 17 файлов и имела 29 нерешённых review threads.

Большая часть архитектурных идей #86 уже присутствует в текущем каноне: отдельный процесс на Rust, RAM-first модель, SingleFlight, security-gated batch spill, immutable spill segments, fail-open/degraded mode, versioned protocol, capability negotiation, PayloadRef как абстракция размещения данных, детерминированная инвалидация и будущая совместимость с Shared Memory, Zero-Copy, MMAP, compression и другими ускорениями.

Поэтому целиком восстанавливать PR #86 нельзя. Полезен только уникальный остаток, описанный ниже.

---

## 2. Что уже поглощено текущим каноном и НЕ требует восстановления

### 2.1. Базовая архитектура CacheEngine

Уже закреплено в `docs/architecture/34_CACHE_ENGINE.md`:

- отдельный Rust-процесс вне Electron hot path;
- RAM-first;
- редкий batch spill только при memory pressure;
- CacheEngine никогда не является SSoT;
- Cache Policy / Security gate перед записью на SSD;
- `CACHE_SESSION_ONLY` не spill'ится в v1;
- `CACHE_LIMITED` spill'ится только при явном разрешении политики;
- SingleFlight;
- deterministic invalidation через revision/hash и зависимости правил/контекста;
- versioned protocol и capability negotiation;
- PayloadRef;
- MemoryBackend / SpillBackend;
- fail-open и `CACHE_DEGRADED`;
- benchmark-first для сложных оптимизаций;
- принцип `Full architecture, minimal implementation`.

### 2.2. Связь с Context и реестром модулей

В текущем `modules_registry.json` CacheEngine уже существует как отдельный модуль и предоставляет:

- `CacheKey`;
- `CacheEntry`;
- `PayloadRef`;
- `CacheCapabilities`.

Context уже имеет optional dependency на CacheEngine и optional contracts `CacheKey` / `PayloadRef`.

Следовательно, старые изменения `ModuleRegistry` из PR #86 считаются superseded и не должны переноситься.

### 2.3. Negative cache как обязательная функция

В PR #86 negative caching был прописан в Context как текущее поведение. Это не следует возвращать. В текущем §34 `NEGATIVE_CACHE` оставлен только как будущая capability. Такое поведение можно включать лишь после явного согласования capability и определения корректной инвалидации.

---

## 3. Уникальная идея №1 — машинные схемы CacheEntry и PayloadRef

### Наблюдение

Текущий `main` уже объявляет `CacheEntry` и `PayloadRef` как межмодульные контракты, но отдельных файлов `schemas/v1/CacheEntry.json` и `schemas/v1/PayloadRef.json` в каноне нет.

PR #86 пытался создать эти схемы. Это полезное направление, но сами файлы нельзя cherry-pick'ать: review выявил в них последовательность контрактных дефектов.

### Что стоит сохранить как требования

Для будущей версии `CacheEntry`:

- явная версия экземпляра контракта;
- строгая связь с версией схемы;
- явный алгоритм hash источника;
- source identity + revision/hash;
- transform id/version;
- security scope;
- конкретный owner для session/task/workspace-local кэша;
- строгая ссылка на `PayloadRef`;
- отсутствие дублирующих авторитетных checksum;
- строгий запрет неизвестных полей, если это соответствует общей schema policy.

Для будущего `PayloadRef`:

- одна авторитетная checksum;
- явный checksum algorithm;
- byte size;
- storage mode;
- mode-specific locator;
- строгая невозможность валидного, но фактически неразрешимого locator.

### Важное ограничение

Будущие схемы нужно проектировать заново от актуального §34 и актуального `schemas/README.md`. PR #86 — только донор требований и негативных тест-кейсов.

---

## 4. Уникальная идея №2 — безопасное каноническое построение CacheKey

PR #86 на одном из этапов зафиксировал строку вида:

`namespace:source_ref:revision:transform:version:scope:owner_id`

Review показал, что такой формат не является инъективным: если компоненты сами содержат `:`, разные входы могут дать одинаковую строку.

### Полезный принцип

CacheKey должен строиться из структурированного canonical pre-image, а не из простого delimiter join.

При будущей формализации стоит рассмотреть:

- каноническую структурированную сериализацию;
- length-prefix для полей или другой однозначный формат;
- при необходимости canonical CBOR/аналог;
- затем криптографический hash компактного представления.

В pre-image должны входить все реальные зависимости валидности результата:

- namespace;
- source identity;
- revision/hash;
- transform id/version;
- parameters;
- RulesRef / Effective Ruleset fingerprint;
- значимая Context/Context Drift basis;
- Skill/Workflow version;
- Security scope/domain;
- конкретный owner_id для локальных областей.

Отдельно требуется правило: если wire-объект содержит и составные поля, и готовый `key`, потребитель обязан детерминированно проверить их соответствие либо готовый `key` вообще не должен быть независимо задаваемым.

---

## 5. Уникальная идея №3 — строгий tagged union для PayloadRef

Само перечисление режимов уже есть в каноне. Уникальная ценность #86 — накопленные требования к их точной машинной семантике.

Будущий `PayloadRef` желательно моделировать как строгий tagged union:

- `INLINE`: обязательны данные и один однозначный encoding; byte_size/checksum считаются по строго определённому представлению;
- `SPILL_SEGMENT`: обязательны `segment_id` + неотрицательный `offset`;
- `MMAP`: обязателен `offset` и ровно один авторитетный locator; нельзя одновременно иметь два конкурирующих locator без правила приоритета;
- `SHARED_MEMORY`: обязателен пригодный handle/name;
- `REMOTE_REF`: обязателен валидный URI поддерживаемой схемы;
- режим разрешён только если соответствующая capability согласована и ENABLED.

Это особенно важно для Zero-Copy/Shared Memory/MMAP будущего fast path: неправильный locator должен отклоняться на контрактной границе, а не обнаруживаться позже в runtime.

---

## 6. Уникальная идея №4 — отдельный wire protocol для CacheEngine

Текущий §34 правильно требует versioned protocol и capability negotiation, но пока описывает их архитектурно, а не как полный машинный wire-contract.

PR #86 review выявил потенциальный будущий пробел: при отдельном процессе CacheEngine клиентам потребуется точный формат обмена.

Если эта граница станет runtime-задачей, потребуются отдельные versioned contracts как минимум для:

- handshake / protocol negotiation;
- protocol version;
- capability state (`SUPPORTED` / `IMPLEMENTED` / `ENABLED`);
- выбранных payload/storage modes;
- GET;
- PUT;
- INVALIDATE;
- health/status;
- typed protocol errors;
- correlation/request id;
- forward/backward compatibility.

Это не означает, что такие схемы нужно создавать сейчас. Идея сохраняется до момента, когда соответствующий Runtime Gate разрешит реализацию.

---

## 7. Что из PR #86 сохранять НЕ надо

### 7.1. Готовые CacheEntry.json / PayloadRef.json

Не переносить автоматически. Они прошли длинную цепочку исправлений, но финальный head всё равно имел нерешённые review findings.

### 7.2. Старую строковую сериализацию CacheKey

Не использовать из-за delimiter collision и риска нарушения isolation через несогласованный owner.

### 7.3. Старые изменения ModuleRegistry

Текущий registry ушёл дальше и уже содержит более новую модель optional dependencies/contracts.

### 7.4. Изменения генератора HTML и `index.html`

Это побочный cross-cutting scope PR #86. Он получил отдельные замечания по ссылкам. Если проблема генератора существует в будущем, её нужно воспроизвести на текущем `main` и решать независимо от CacheEngine.

### 7.5. Старые тесты PR #86

Тесты были связаны с конкретными промежуточными схемами. Сохранять следует не файлы тестов, а обнаруженные инварианты и негативные сценарии.

---

## 8. Полезные негативные сценарии, которые стоит помнить

При будущей формализации CacheEngine contracts полезно снова проверить:

1. два разных набора компонентов CacheKey не могут дать одинаковый key;
2. `owner_id` участвует в изоляции и не может расходиться с key;
3. смена RulesRef / Context / Skill / Workflow invalidates зависимый результат;
4. session-local данные не могут попасть в persistent spill без разрешения политики;
5. `SPILL_SEGMENT` без locator невалиден;
6. `MMAP` без однозначного locator/offset невалиден;
7. `INLINE` имеет ровно одну определённую encoding semantics;
8. checksum имеет один источник истины и явный algorithm;
9. source hash имеет явный algorithm;
10. protocol/capability vocabulary едино во всех схемах и registry;
11. будущая capability не используется до negotiation;
12. несовместимая schema_version отклоняется или проходит только через явно определённую совместимость.

---

## 9. Как «раскапывать» эту запись в будущем

Эту запись не следует превращать в одну большую задачу.

Если владелец явно решит вернуть идеи, их лучше разделить на независимые GraveyardCandidate:

1. **CacheEntry/PayloadRef schemas** — формализация межмодульных контрактов;
2. **Canonical CacheKey encoding** — однозначная сериализация и проверка isolation/invalidation;
3. **CacheEngine wire protocol** — handshake, capability negotiation и GET/PUT envelopes.

Каждый кандидат должен:

- заново сравниваться с тогдашним `main`;
- получить `COMPATIBLE`, а не `SUPERSEDED/CONFLICT/UNKNOWN`;
- пройти Human Approval;
- только после этого попасть в обычный Issue/ADR/TaskContract workflow.

---

## 10. Provenance

Первичный исторический источник:

- PR: https://github.com/rassvetpublic-spec/KAT9I_OS/pull/86
- branch: `feat/issue-84-cache-engine-architecture`
- head: `88d40ba6cb4e5143c013490db11dedcc82881a45`
- merge base с линией разработки: `ac1b55544cc8b2fd6879b28577193bdac68dc167`
- состояние PR при закрытии: closed, not merged.

Канонический источник для сравнения:

- `main` при аудите: `bb7b4702126aabd402f942f2dc71d095110b7d0e`
- основной CacheEngine: `docs/architecture/34_CACHE_ENGINE.md`
- machine registry: `modules_registry.json`
- Graveyard policy: `graveyard/README.md`

Эта запись сохраняет знания из #86 без повышения их до текущей работы.
