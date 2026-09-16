# CKS Current-State Delta — 2026-09-17

Status: **DATA ONLY / NON-CANONICAL / FORENSIC INPUT**  
Parent work item: KAT9I_OS #233  
Purpose: зафиксировать, насколько CKS изменился за время donor-аудита, до продолжения Architecture Genome.

## 1. Exact revision

Проверено по `rassvetpublic-spec/CKS` ветка `main`.

Exact HEAD на момент повторного аудита:

`a499436faa0fe86411962fcd6422357628a2b941`

Commit message:

`ci(knowledge): add stage 7 full self-audit and integral regression`

CKS менялся непосредственно во время нашего аудита, поэтому дальнейшие выводы о границе KAT9I ↔ CKS обязаны иметь revision binding.

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
- интегральную stage-7 regression-проверку.

Следствие: CKS нельзя больше моделировать как «пассивное хранилище памяти» KAT9I_OS. Это автономная knowledge system со своим Core, governance, lifecycle, schemas, runtime и диагностической аналитикой.

---

## 3. Граница CKS ↔ KAT9I подтверждена, а не размыта

Текущий `ARCHITECTURE.md` CKS продолжает фиксировать:

- CKS — независимая система работы с контекстом, знаниями, решениями, доказательствами и историей;
- CKS не является исполнительным слоем;
- KAT9I_OS владеет исполнением, рабочими процессами и операциями;
- внутреннее состояние CKS не принадлежит KAT9I_OS.

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
7. self-audit + Governance CI + integral regression.

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

Stage-7 regression отдельно проверяет, что:

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

`ADR-0001-multi-worker-distillate.md` принят и задаёт:

- worker emits distillate object;
- worker не получает прямой доступ к CKS database;
- raw distillate и approved knowledge revision-oriented / immutable;
- raw не становится Canon без validation;
- secure/private payload ограничивается;
- KAT9I/proxy выступает boundary transport, а не владельцем CKS knowledge.

Важно не смешивать этот ADR с общим устройством CKS: он описывает ingress из multi-worker execution environment, а не переносит worker orchestration внутрь CKS.

---

## 10. Зафиксированные проблемы/дрейф текущего состояния

### CKS-DRIFT-001 — SSOT registry указывает несуществующий architecture path

`control/ssot-registry.yaml` содержит:

`architecture.path: architecture/`

Но на текущем `main` корневого каталога `architecture/` нет.

Фактические архитектурные материалы находятся как минимум в:

- `/ARCHITECTURE.md`;
- `/docs/ARCHITECTURE.md`;
- `/docs/architecture/`.

Это создаёт ambiguity источника архитектурного SSOT.

### CKS-DRIFT-002 — Self Audit не ловит CKS-DRIFT-001

`tools/cks_self_audit.py::check_ssot_registry()` проверяет наличие marker `architecture:`, но фактическое существование `architecture.path` не проверяет. Физически проверяются `tools/`, `engine/`, `obsidian/`.

Следовательно текущий self-audit может PASS при сломанной architecture SSOT pointer.

### CKS-DRIFT-003 — документы разных эпох выглядят одновременно текущими

Одновременно присутствуют:

- README с описанием стабильного/frozen CKS v1.2;
- `control/system-state.yaml` с `current_version: CKS_v1.5`, baseline v1.2 / operational v1.3 / runtime v1.4 / development v1.5;
- старый `docs/history/CKS_STATE_CURRENT_v1.md`, описывающий период до сложной автоматизации;
- рабочий `docs/architecture/CKS_CANON_SOURCE_MAP_v1.md`, который всё ещё говорит, что пути текущего канона нужно уточнить;
- новый accepted Runtime/Intelligence layer.

Часть этого различия объясняется разделением frozen Core и evolving Runtime, но человек или AI без source map легко выберет устаревший файл как current truth.

Это не доказательство архитектурной ошибки, но подтверждённый documentation/authority drift, который нужно учесть до CKS Genome.

---

## 11. Что меняется в нашей Architecture Forensics

### Было слишком грубо

`CKS = knowledge / decisions / learning`

### Теперь рабочая модель точнее

`CKS = frozen knowledge-governance core + evolving knowledge runtime + intelligence/evolution/recovery + derived views + validation/self-audit`

при неизменной внешней границе:

`CKS ≠ execution orchestrator`.

Следовательно:

- CKS нельзя использовать как модуль KAT9I;
- KAT9I нельзя делать владельцем CKS lifecycle;
- общий CORE_KERNEL не должен владеть CKS Canon;
- shared contract должен описывать только межсистемные инварианты: identity/reference, provenance, evidence, revision binding, authority class, proposal/decision separation, feedback/learning event transport;
- KAT9I task state и CKS knowledge state должны оставаться раздельными.

---

## 12. Влияние на F0→F4 #233

### F0

Нужно добавить полноценную CKS lineage: не только происхождение, но и переход от static knowledge contracts к executable Knowledge Runtime/Intelligence/Evolution.

### F1

Реестр потерянных идей теперь должен уметь различать:

- потеряно в KAT9I;
- уже независимо реализовано в CKS;
- дублируется обеими системами;
- является общим semantic invariant;
- является только boundary concern.

### F2

ABC/XYZ нельзя проводить до этого cross-check, иначе уже реализованную CKS-функцию можно ошибочно классифицировать как «потерянную функцию KAT9I».

### F3

Completeness Gate дополнить проверкой:

`KAT9I candidate → CKS ownership check → shared/boundary/independent classification`.

### F4

`CKS_ARCHITECTURE_GENOME.md` должен выводиться из собственного CKS lineage и current accepted decisions, а не из KAT9I assumptions.

`CORE_KERNEL_CONTRACT_v1` должен появляться только после двух независимых Genome и описывать договор между ядрами, а не третье ядро над ними.

---

## 13. Статус

Этот документ не завершает CKS archaeology.

Он фиксирует только **current-state delta** на exact CKS revision и блокирует использование старой упрощённой модели CKS в дальнейшей архитектурной работе.

Следующее действие #233 остаётся прежним: закончить F0 history, затем F1 lost-ideas registry, затем F2 ABC/XYZ.