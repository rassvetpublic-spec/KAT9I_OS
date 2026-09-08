# 34. CacheEngine — высокопроизводительный кэш KAT9I_OS

## 34.1. Назначение

`CacheEngine` — отдельный системный модуль ускорения KAT9I_OS.

Его задача:

> быстро повторно использовать производные данные, не превращая кэш в источник истины и не влияя на корректность системы.

Главный принцип:

> **полная потеря CacheEngine или всего его содержимого может сделать KAT9I_OS медленнее, но не должна сделать её неправильной.**

## 34.2. Отдельный модуль на Rust

CacheEngine реализуется как отдельный процесс/модуль на Rust.

Причины:

- минимальная задержка на горячем пути;
- отсутствие GC-пауз;
- безопасная многопоточность;
- эффективная работа с памятью;
- возможность использовать shared memory, mmap и другие низкоуровневые механизмы в будущем;
- независимый жизненный цикл от Electron.

Electron не участвует в `GET`/`PUT` пути кэша. UI может только читать состояние, метрики и отправлять административные команды через Core.

## 34.3. RAM-first

Нормальный режим CacheEngine — хранение кэша в оперативной памяти.

SSD не является обычным рабочим уровнем кэша.

Пока RAM хватает, CacheEngine не должен постоянно дублировать записи на накопитель.

Это уменьшает:

- задержки;
- количество системных вызовов;
- write amplification;
- фоновую compaction-нагрузку;
- износ SSD.

## 34.4. Spill на диск только при memory pressure

При достижении порогов memory pressure CacheEngine освобождает RAM.

Политика первой версии:

1. дешёвые для повторного построения холодные записи удаляются;
2. дорогие для повторного построения холодные записи собираются в batch;
3. batch записывается одной крупной последовательной операцией в immutable spill segment;
4. RAM освобождается;
5. при последующем запросе нужный объект лениво возвращается в RAM.

SSD используется как резерв ёмкости, а не как обязательное постоянное хранилище.

## 34.5. Immutable spill segments

Spill-сегмент после успешной записи не изменяется.

Минимально формат должен предусматривать:

- magic;
- format_version;
- segment_id;
- created_at;
- entry_count;
- индекс записей;
- payload;
- checksum.

Запись выполняется через временный файл и атомарное завершение. Незавершённый временный файл удаляется после сбоя.

Повреждённый segment удаляется и при необходимости пересоздаётся из первоисточника.

## 34.6. Cache не является SSoT

В CacheEngine запрещено хранить единственную каноническую копию:

- TaskRuntimeState;
- Rule;
- KnowledgeRecord;
- Evidence;
- Git commit/Issue/PR state;
- пользовательских настроек;
- секретов;
- других данных, потеря которых нарушает корректность системы.

CacheEngine хранит только производные, повторно получаемые или повторно вычисляемые данные.

## 34.7. Примеры допустимых данных

Допустимо кэшировать:

- результаты поиска;
- Repo Map;
- AST и symbol index;
- dependency graph;
- materialized context;
- Context Pack;
- embeddings;
- безопасные read-only Tool Results;
- вычисленные hash;
- преобразованные документы;
- промежуточные результаты локального анализа.

## 34.8. Детерминированный CacheKey

CacheKey должен быть структурированным и затем может преобразовываться в компактный binary/hash key.

Логически он включает:

- namespace;
- identity источника;
- revision/hash источника;
- transformation id;
- transformation version;
- parameters hash;
- security domain/scope.

Свежесть по возможности определяется identity/revision/hash, а не догадкой по TTL.

## 34.9. CacheEntry

Контракт CacheEntry с первой версии должен предусматривать совместимость будущего.

Минимальные группы метаданных:

- identity: key, namespace;
- source: source_ref, revision, hash;
- transform: transform_id, transform_version;
- payload: type, size, location;
- lifecycle: created_at, last_access, expires_at при необходимости;
- cost: build_cost/rebuild_cost;
- policy: class/priority hints;
- security: scope;
- integrity: checksum;
- observability: hit_count;
- compatibility: schema_version.

Не все поля обязаны активно участвовать в политике первой версии.

## 34.10. Версионированный протокол

Взаимодействие клиентов с CacheEngine строится через versioned protocol.

Клиент и CacheEngine должны уметь согласовать:

- protocol version;
- supported capabilities;
- payload modes;
- storage modes.

Добавление новой возможности не должно требовать изменения Task/Context/Worker API.

## 34.11. Capability negotiation

Архитектура сразу предусматривает capability negotiation.

Примеры capabilities:

- RAM_CACHE;
- BATCH_SPILL;
- SINGLEFLIGHT;
- SHARED_MEMORY;
- ZERO_COPY;
- DEDUPLICATION;
- NAMESPACE_QUOTAS;
- NEGATIVE_CACHE;
- MMAP;
- COMPRESSION;
- ENCRYPTION;
- DISTRIBUTED_CACHE;
- LEARNING_TUNED_POLICY.

Capability может быть `SUPPORTED`, `IMPLEMENTED`, `ENABLED` независимо.

## 34.12. PayloadRef

Публичный контракт не должен предполагать, что payload всегда передаётся inline через IPC.

`PayloadRef` архитектурно предусматривает режимы:

- INLINE;
- SHARED_MEMORY;
- RAM_REGION;
- SPILL_SEGMENT;
- MMAP;
- REMOTE_REF.

В первой версии достаточно реализовать только необходимые режимы. Остальные остаются совместимыми путями развития.

## 34.13. Backend abstraction

CacheEngine разделяет публичный API и физическое размещение данных.

Минимальные логические backend:

- MemoryBackend;
- SpillBackend.

В будущем могут появиться mmap, persistent memory, remote backend и другие варианты без изменения верхнего API.

## 34.14. Policy abstractions

Архитектура заранее разделяет:

- AdmissionPolicy;
- EvictionPolicy;
- MemoryBudgetPolicy;
- SpillPolicy.

Первая версия использует простые детерминированные реализации. AI не находится на горячем пути CacheEngine.

## 34.15. SingleFlight

Первая версия должна поддерживать SingleFlight / request coalescing.

Если несколько Worker одновременно запросили один отсутствующий объект, один исполнитель строит результат, остальные используют тот же результат вместо повторного вычисления.

Это защищает от дублирования CPU, RAM, I/O, внешних запросов и дорогих AI-вызовов.

## 34.16. Простота первой реализации

Первая реализация намеренно ограничена.

Обязательно:

- Rust отдельным процессом;
- RAM-first;
- revision/hash keys;
- простой eviction;
- базовые memory thresholds;
- SingleFlight;
- batch spill;
- immutable segments;
- checksum;
- lazy restore;
- health/status;
- метрики;
- degraded/fail-open поведение.

## 34.17. Будущая совместимость без обязательной реализации

С первой версии контракты не должны препятствовать последующему добавлению:

- Shared Memory;
- Zero-Copy;
- content deduplication;
- namespace quotas;
- negative cache;
- mmap;
- compression;
- encryption;
- distributed cache;
- Learning-tuned policies;
- NUMA-aware размещения.

Наличие совместимости не означает обязательную реализацию этих функций в v1.

## 34.18. IPC

Electron не является транспортным посредником CacheEngine.

Локальные клиенты обращаются к CacheEngine через низкоуровневый локальный IPC. На Windows предпочтителен Windows Named Pipe. Архитектура транспорта должна позволять в будущем Unix Domain Socket и Shared Memory fast-path.

Не следует делать HTTP/JSON обязательным hot-path протоколом CacheEngine.

## 34.19. Memory Budget

Первая версия использует простую предсказуемую политику RAM budget с настраиваемыми порогами.

CacheEngine должен освобождать память до системного OOM и не конкурировать бесконтрольно с Core, Worker и локальными AI runtime.

Более сложная динамическая политика может быть добавлена позже через `MemoryBudgetPolicy` без изменения клиентов.

## 34.20. Fail-open и degraded mode

Сбой CacheEngine не должен блокировать нормальную работу KAT9I_OS, если исходные ресурсы доступны.

При недоступности CacheEngine Core/Context переходят в `CACHE_DEGRADED` и получают/вычисляют данные обычным путём.

После восстановления CacheEngine может снова принимать производные данные.

## 34.21. Recovery

CacheEngine не должен требовать сложного восстановления.

Правила:

- RAM-кэш потерян → начать пустым;
- spill index повреждён → пересоздать или удалить;
- segment повреждён → удалить;
- весь cache storage повреждён → удалить и построить заново;
- незавершённый temporary segment → удалить при старте.

Никакая из этих операций не должна затрагивать SSoT.

## 34.22. Метрики

Минимальные метрики:

- L1/RAM hit rate;
- spill hit rate;
- miss rate;
- p50/p95/p99 GET latency;
- PUT latency;
- throughput;
- RAM usage;
- spill disk usage;
- evictions;
- invalidations;
- SingleFlight coalesced requests;
- bytes avoided;
- rebuild time avoided;
- context tokens avoided, если измеримо;
- degraded mode events.

## 34.23. Benchmark-first для усложнений

Новая оптимизация CacheEngine не становится обязательной только потому, что теоретически быстрее.

Перед включением сложной оптимизации нужны реальные измерения на нагрузке KAT9I_OS.

Особенно это относится к:

- zero-copy;
- custom allocator;
- deduplication;
- NUMA;
- huge pages;
- distributed cache;
- сложным adaptive policies.

## 34.24. Надёжность и приоритеты

Порядок приоритетов CacheEngine:

1. Correctness — корректность системы;
2. Simplicity — простота;
3. Recoverability — лёгкое восстановление;
4. Predictability — предсказуемое поведение;
5. Speed — скорость.

Высокая производительность достигается внутри этих ограничений, а не вместо них.

## 34.25. Главный критерий качества

Обязательный системный тест:

> удалить весь кэш KAT9I_OS и убедиться, что система продолжает выполнять задачи корректно, только медленнее.

## 34.26. Принцип развития

Для CacheEngine действует правило:

> **Full architecture, minimal implementation.**

То есть ожидаемые пути развития учитываются в контрактах заранее, но неиспользуемая сложность не реализуется до появления измеренной необходимости.

Дополнительный принцип:

> **совместимость с будущей функцией обеспечивается контрактом, а не заранее написанным неиспользуемым кодом.**
