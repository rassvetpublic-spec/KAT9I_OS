# CKS Current-State Delta — 2026-09-17

Status: **DATA ONLY / NON-CANONICAL / FORENSIC INPUT**  
Parent work item: KAT9I_OS #233  
Purpose: зафиксировать, насколько CKS изменился за время donor-аудита, до продолжения Architecture Genome.

## 1. Exact revision

Проверено по `rassvetpublic-spec/CKS` ветка `main`.

Первый exact HEAD этого delta-аудита:

`a499436faa0fe86411962fcd6422357628a2b941`

После этого CKS продолжил развиваться прямо во время forensic-прохода. Текущая контрольная revision на момент Stage 1 regression-check:

`acc429ca6497b45810e0285220e0a9a8adf4e709`

Commit message:

`docs(snapshot): close full knowledge snapshot operation`

Между `a499436...` и `acc429ca...` — 28 commit. Изменения затронули не только документацию, но и graph runtime, schema, tests и CI. Поэтому дальнейшие выводы о границе KAT9I ↔ CKS обязаны иметь revision binding.

---

## 2. Главное изменение картины

Ранее CKS можно было описывать как независимую систему контекста, знаний, решений, доказательств и истории.

Это по-прежнему верно для границы системы, но теперь недостаточно полно.

Текущий CKS содержит самостоятельный исполняемый рабочий контур знаний поверх замороженного Core:

- формальную модель объекта знания;
- две различающиеся шкалы жизненного цикла: системный lifecycle и детальный knowledge lifecycle;
- Knowledge Runtime;
- Knowledge Intelligence;
- Knowledge Evolution / migration / snapshot / recovery;
- Knowledge Graph Runtime;
- Traceability Engine;
- Project Federation без объединения владельцев Canon;
- derived Obsidian projection;
- Governance Runner;
- Self Audit;
- интегральную regression-проверку;
- Relation History;
- Graph Migration;
- Graph Recovery;
- Graph Object Lifecycle;
- Node Versioning.

Следствие: CKS нельзя больше моделировать как «пассивное хранилище памяти» KAT9I_OS. Это автономная knowledge system со своим Core, governance, lifecycle, schemas, runtime и диагностической аналитикой.

---

## 3. Граница CKS ↔ KAT9I подтверждена, а не размыта

Текущий `ARCHITECTURE.md` CKS продолжает фиксировать:

- CKS — независимая система работы с контекстом, знаниями, решениями, доказательствами и историей;
- CKS не является исполнительным слоем;
- KAT9I_OS владеет исполнением, рабочими процессами и операциями;
- внутреннее состояние CKS не принадлежит KAT9I_OS.

Accepted `docs/ADR/ADR-001-CKS-INDEPENDENCE.md` дополнительно закрепляет:

- CKS остаётся independent system/repository;
- CKS не является subsystem KAT9I_OS;
- Knowledge lifecycle и Execution lifecycle имеют разные требования;
- интеграция требует explicit contracts и review.

`core/ADAPTER_BOUNDARY_RULE.md` усиливает границу:

- адаптер может читать утверждённые объекты, преобразовывать внешний формат, делать mapping и создавать Proposal;
- адаптер не может менять CKS Core, создавать Decision, превращать внешний статус в знание или обходить Evidence.

Поэтому будущий общий контракт должен быть **boundary contract**, а не новый общий исполняемый Core, который поглощает две системы.

---

## 4. Принятый Knowledge-Centric Runtime

`decisions/ADR-0002-knowledge-centric-runtime.md` имеет статус `Принято`.

Он закрепляет два развиваемых слоя:

1. **Knowledge Runtime** — объект знания, кластеры, теги, lifecycle, динамические представления, Obsidian-compatible representation.
2. **Knowledge Intelligence** — скрытые связи, кандидаты кластеров, анализ превращения материала в знание, карта развития, self-audit.

Критическое ограничение ADR:

- CKS v1.2 Core остаётся frozen;
- Runtime/Intelligence не переписывают Core автоматически;
- граф, views, metrics и analytics не являются SSOT;
- analytics не принимает Decision и не меняет Canon.

Это напрямую подтверждает принцип:

`autonomous analysis ≠ autonomous authority`.

---

## 5. Два уровня lifecycle теперь формализованы

`control/lifecycle-state-model.yaml` разделяет:

### system_lifecycle

`discovered → researched → proposed → reviewed → accepted → canonical → deprecated → archived`

### knowledge_runtime

Детальный lifecycle берётся из `schemas/cks-knowledge-object.schema.json` и проверяется `tools/cks_knowledge_state_machine.py`.

Основной путь знания:

`raw → captured → normalized → deduplicated → clustered → researched → understood → connected → validated → knowledge → canonical → evolving`

Дополнительные состояния:

`disputed / superseded / archived / rejected`.

Compatibility aliases сохраняют старые `draft/review/active`.

Это важный вывод для будущего Kernel Contract: нельзя сводить KAT9I task lifecycle и CKS knowledge lifecycle в одну общую State Machine. Общим может быть только мета-контракт состояния/перехода/evidence/revision, а сами state spaces принадлежат своим системам.

---

## 6. Модель объекта знания стала машинным контрактом

`schemas/cks-knowledge-object.schema.json` требует как минимум:

- `id`;
- `type`;
- `status`;
- `owner`;
- `lifecycle`;
- `relations`;
- `evidence`;
- `history`.

Модель также содержит:

- clusters;
- tags;
- project projections;
- relation-level evidence/confidence/history;
- traceability;
- signals: confidence / importance / novelty / uncertainty / intuition;
- Obsidian projection settings.

Смысловой вывод: CKS уже имеет richer object contract, поэтому будущий межсистемный контракт должен ссылаться на CKS objects через идентификаторы/provenance и не копировать их структуру в KAT9I.

---

## 7. CKS действительно реализовал путь «хаос → знание»

Актуальная документация Runtime/Intelligence фиксирует путь:

`сырой материал → захват → нормализация → очистка дублей → кластеры/теги → исследование → понимание → связи → проверка → знание → Canon через Decision`.

Stage roadmap развивает это по этапам:

1. audit / no duplicate model;
2. executable Knowledge Runtime;
3. Obsidian projection;
4. dynamic views и материал→знание;
5. Knowledge Intelligence I;
6. Knowledge Intelligence II — evolution/migration/recovery;
7. self-audit + Governance CI + integral regression;
8. graph evolution — Relation History / Migration / Recovery;
9. graph node lifecycle/versioning.

Таким образом прежняя формула чата

`INPUT/хаос → структурирование → проверка → knowledge → learning`

перестала быть только гипотезой: значительная часть этого пути уже материализована в CKS runtime/tests.

---

## 8. Но CKS не стал автоканонизатором

`tools/cks_knowledge_evolution.py` работает с копиями данных и не меняет SSOT/Decision/Canon автоматически.

Он реализует проверяемые операции:

- migration/normalization;
- validated state transition;
- deterministic SHA-256 snapshot;
- version diff;
- snapshot verification;
- isolated recovery.

Graph evolution расширил это, не повышая graph authority:

- Relation History;
- Graph Migration `1.0 → 2.0`;
- integrity-checked Graph Recovery snapshots;
- Node Versioning;
- Graph Object Lifecycle через общую state machine.

Интегральная regression отдельно проверяет, что:

- self-audit имеет diagnostic authority;
- governance имеет validation authority;
- hidden links имеют suggestion-only authority;
- derived views не являются SSOT;
- transition в canonical блокируется без Evidence и Decision;
- исходные записи не мутируют интегральным проходом;
- project federation сохраняет независимых владельцев Canon.

Это является сильным архитектурным инвариантом, который должен попасть в будущий Genome как кандидат после F1/F2, но не повышается туда автоматически этим checkpoint.

---

## 9. Multi-Worker Distillate остаётся отдельным принятым решением

`decisions/ADR-0001-multi-worker-distillate.md` принят и задаёт ingress из multi-worker execution environment.

Важно: он **не является** ADR независимости CKS.

В CKS существуют два ADR namespace:

- `docs/ADR/ADR-001-*`, `ADR-002-*` — Independence / Donor Isolation и другие архитектурные ADR;
- `decisions/ADR-0001-*`, `ADR-0002-*` — Multi-Worker Distillate / Knowledge-Centric Runtime.

Эта двойная нумерация требует явной source-map/authority документации, иначе AI легко смешивает `ADR-001` и `ADR-0001`.

Multi-Worker Distillate задаёт:

- worker emits distillate object;
- worker не получает прямой доступ к CKS database;
- raw distillate и approved knowledge revision-oriented / immutable;
- raw не становится Canon без validation;
- secure/private payload ограничивается;
- KAT9I/proxy выступает boundary transport, а не владельцем CKS knowledge.

Он описывает ingress, а не переносит worker orchestration внутрь CKS.

---

## 10. Проверка предыдущих GAP и их текущий статус

### CKS-DRIFT-001 — SSOT registry указывает несуществующий architecture path

**СТАТУС: ПОДТВЕРЖДЁН, открыт #29.**

`control/ssot-registry.yaml` по-прежнему содержит:

`architecture.path: architecture/`

Но корневого каталога `architecture/` нет.

Фактические архитектурные материалы находятся как минимум в:

- `/ARCHITECTURE.md`;
- `/docs/ARCHITECTURE.md`;
- `/docs/architecture/`;
- `/docs/ADR/`;
- `/decisions/`.

### CKS-DRIFT-002 — Self Audit не ловит CKS-DRIFT-001

**СТАТУС: ПОДТВЕРЖДЁН, открыт #29.**

`tools/cks_self_audit.py::check_ssot_registry()` проверяет marker `architecture:`, но existence значения `architecture.path` не проверяет.

### CKS-DRIFT-003 — документы разных эпох выглядят одновременно текущими

**СТАТУС: ЧАСТИЧНО СМЯГЧЁН, НЕ УСТРАНЁН.**

Новый `docs/CKS_CURRENT_WORKING_STATE_SNAPSHOT_2026-09-17.md` объясняет различие frozen Core v1.2 и evolving working layer v1.5.

Но formal source map всё ещё недоопределён, а broken architecture pointer остаётся.

### CKS-DRIFT-004 — слабая repository mutation boundary

**СТАТУС: ПОДТВЕРЖДЁН, открыт #30.**

`main` остаётся `protected=false`.

История CKS в основном развивается direct commits в `main`; PR inventory на момент аудита содержит только один draft/unmerged PR #3.

Это означает, что repository governance слабее внутренней модели Evidence/Proposal/Decision/Review.

### CKS-GAP-RELATION-HISTORY / GRAPH-MIGRATION / GRAPH-RECOVERY

**СТАТУС: SUPERSEDED / CLOSED BY IMPLEMENTATION.**

Они были реальными gaps Stage A, но закрыты Stage B и подтверждены CI. Их нельзя продолжать перечислять как текущие проблемы.

### CKS-GAP-NODE-VERSIONING

**СТАТУС: SUPERSEDED / CLOSED BY IMPLEMENTATION.**

Stage D добавил Graph Object Lifecycle / Node Versioning и regression test.

---

## 11. Проверка старых рассуждений Architecture Forensics

### Было слишком грубо

`CKS = knowledge / decisions / learning`

### Исправленная рабочая модель

`CKS = frozen knowledge-governance core + evolving knowledge runtime + graph/traceability + intelligence/evolution/recovery + derived views + validation/self-audit`

при неизменной внешней границе:

`CKS ≠ KAT9I execution orchestrator`.

### Было ошибочно

`ADR-0001 = CKS Independence`.

Исправление:

- `docs/ADR/ADR-001-CKS-INDEPENDENCE.md` = Independence;
- `decisions/ADR-0001-multi-worker-distillate.md` = Multi-Worker Distillate.

### Было преждевременно

`CKS #22 CORE KERNEL integration` как основание общего ядра.

Исправление:

#22 является roadmap/proposal Issue, а не Accepted ADR. Он остаётся DATA до F1/F2/F3.

### Было ошибочно считать current

`Council v0.1`.

Исправление:

PR #3 остаётся `OPEN / DRAFT / UNMERGED`; его 50 commits — отдельный historical/experimental donor внутри собственного CKS history, не current Canon.

---

## 12. Влияние на F0→F4 #233

### F0

CKS commit history уже полностью перечислена по REST pages 1–7; page 8 empty. PR inventory также выполнен.

Но semantic review ещё не завершён: необходимо проверить критические commit-группы, PR #3 и absorption research tracks.

### F1

Реестр потерянных идей должен различать:

- потеряно в KAT9I;
- потеряно/не смержено в CKS;
- уже независимо реализовано в CKS;
- дублируется обеими системами;
- является общим semantic invariant;
- является только boundary concern.

Первичные CKS candidates:

- Council v0.1 PR #3;
- deferred #8;
- Graveyard verification #5;
- Distillation Pipeline #9/#14;
- Learning/Ownership/Canon Evidence research #21–#27;
- agent/context boundaries из #6.

### F2

ABC/XYZ нельзя проводить до absorption check, иначе уже реализованную CKS-функцию можно ошибочно классифицировать как «потерянную функцию KAT9I».

### F3

Completeness Gate дополнить проверкой:

`KAT9I candidate → CKS ownership check → shared/boundary/independent classification`.

### F4

`CKS_ARCHITECTURE_GENOME.md` должен выводиться из собственной CKS lineage и current accepted decisions, а не из KAT9I assumptions.

`CORE_KERNEL_CONTRACT_v1` должен появляться только после двух независимых Genome и описывать договор между ядрами, а не третье ядро над ними.

---

## 13. Disconnect-safe continuation

Новый рабочий чат начинает с:

1. KAT9I_OS #233;
2. `История/CKS_ARCHAEOLOGY_STAGE1_CHECKPOINT_20260917.md`;
3. fresh CKS HEAD;
4. drift check относительно `acc429ca6497b45810e0285220e0a9a8adf4e709`;
5. #29/#30;
6. semantic review PR #3 и research-track absorption matrix.

После каждого крупного блока повторно проверяются предыдущие выводы.

Этот документ не завершает CKS archaeology и не является доказательством F0/F1 completeness.