# CKS Archaeology — Stage 1 Checkpoint — 2026-09-17

Status: **DATA ONLY / NON-CANONICAL / DISCONNECT-SAFE CHECKPOINT**  
Governing work item: `KAT9I_OS #233`  
Implementation Worker: ChatGPT  
Independent QA: Antigravity (AGY)

## 0. SSoT preflight

Этот файл не является Canon CKS или KAT9I_OS и не заменяет профильные SSoT.

Рабочее правило Stage 1:

`fresh HEAD → current SSoT → previous-result regression check → history scan → correction log → checkpoint`.

Любой вывод из старого чата считается только гипотезой, пока не подтверждён текущим GitHub Evidence.

Source anchors на момент завершения этого прохода:

- KAT9I_OS `main`: `4f01aa530584f591ffbc1146fd2af09a92389cc2`;
- CKS `main`: `acc429ca6497b45810e0285220e0a9a8adf4e709`;
- CKS current system state: baseline `CKS_v1.2`, operational `v1.3`, runtime `v1.4`, development/current `v1.5`; Core frozen, Runtime evolving.

CKS изменялся во время аудита, поэтому следующие проходы обязаны сначала перечитать HEAD и проверить drift относительно этого anchor.

---

## 1. Что фактически просмотрено

### Commit history

Проверена последовательность GitHub REST `commits?per_page=100` по страницам 1–7. Страница 8 вернула пустой список.

Следовательно, на указанной revision выполнен полный проход доступной линейной commit-history `main`, а не выборка последних commit.

Это ещё не означает содержательный diff-review каждого commit. Stage 1 теперь разделяет:

- `HISTORY_ENUMERATED = YES` — вся commit-линия перечислена;
- `SEMANTIC_REVIEW_COMPLETE = NO` — содержательные diff критических эпох ещё продолжают проверяться.

### PR history

На момент проверки найден один PR CKS:

- `PR #3 Add CKS Council v0.1` — `OPEN + DRAFT + UNMERGED`, 50 commits, branch `council-v0.1`.

Он не является current Canon и должен рассматриваться как отдельный источник historical/experimental DATA до явного решения.

### Issue history

Просмотрен полный актуальный набор Issues `#1–#30` как минимум на уровне title/body для восстановления архитектурной линии, GAP, deferred ideas и migration records.

---

## 2. Эпохи развития CKS, восстановленные из истории

### Epoch A — Bootstrap / contracts / governance foundation

Ранний CKS формировался вокруг:

- независимого knowledge/decision/evidence слоя;
- object/protocol/schema foundation;
- review и promotion protocols;
- validation scaffolding;
- agent-role/config experiments;
- явной границы с KAT9I runtime.

В этой эпохе уже появляется принцип, который пережил последующие версии: Knowledge lifecycle и Execution lifecycle не должны сливаться в один ownership-domain.

### Epoch B — Bootstrap 1.0 → v1.2 freeze

Коммиты и Issues фиксируют:

- Bootstrap scope/boundaries;
- phased roadmap;
- отделение deferred features от bootstrap;
- migration/chat preservation;
- Legacy isolation;
- CKS v1.2 closure/frozen Core;
- правило `GAP → Evidence → Proposal → Decision → Minimal Change`.

Accepted `docs/ADR/ADR-001-CKS-INDEPENDENCE.md` прямо закрепляет независимость CKS от KAT9I_OS.

Accepted `docs/ADR/ADR-002-DONOR-ISOLATION.md` запрещает donor-идеям менять Canon напрямую и задаёт adoption pipeline через Research/Audit/ABC-XYZ/Decision.

### Epoch C — v1.3 gap-driven research

После заморозки Core работа не остановилась, а была вынесена в исследовательские tracks:

- Learning Layer;
- Ownership Model;
- Canon Evidence Guard;
- Graveyard verification;
- Evidence Matrix;
- Decision Quality;
- Knowledge lifecycle metrics;
- Research isolation;
- Automation guards;
- Review Gate.

В истории есть отдельные ABC/XYZ и Evidence Pack артефакты. Это важно: `frozen Core` не означает `frozen system`.

### Epoch D — graph / traceability / governance / intelligence platform

Затем CKS получил сначала модели, затем рабочие реализации:

- Knowledge Graph;
- Traceability Engine;
- multi-project federation;
- Governance Runner;
- Self Audit;
- event/history/audit models;
- conflict/health/version diagnostics;
- graph query/quality/dashboard layers.

Критический переход этой эпохи: архитектурные концепты начали превращаться в executable validation/runtime, при сохранении правила `automation != Decision`.

### Epoch E — Knowledge-Centric Runtime / Intelligence

`decisions/ADR-0002-knowledge-centric-runtime.md` имеет статус Accepted и формализует:

- Knowledge Runtime;
- Knowledge Intelligence;
- Project как projection графа знаний;
- rich knowledge lifecycle;
- Obsidian как derived view;
- запрет analytics/metrics/views автоматически менять Canon;
- frozen v1.2 Core при evolving working layer.

Этапы Runtime/Intelligence 2–7 получили исполняемые тесты и CI.

### Epoch F — Full Knowledge Snapshot A–D

После нашего предыдущего чтения CKS продолжил изменяться.

Stage A повторно инвентаризировал фактическую реализацию и обнаружил три реальные graph gaps:

1. Relation History;
2. Graph Migration;
3. Graph Recovery.

Stage B закрыл все три в существующем `KnowledgeGraph`, без второго graph engine, и подтвердил обратную совместимость CI.

Stage C добавил постоянные versioned self-audit/governance/CI reports и current working state snapshot.

Stage D добавил отдельные Graph Object Lifecycle / Node Versioning поверх существующей state machine и снова прогнал интегральную проверку.

Финальный working-state snapshot указывает успешный CI run `35162449046` и постоянные verified reports.

---

## 3. Regression review предыдущих наших выводов

| Предыдущий вывод | Текущая проверка | Статус |
|---|---|---|
| `CKS — независимая система, не subsystem KAT9I` | Accepted ADR-001 существует в `docs/ADR/`; root Architecture сохраняет boundary | CONFIRMED |
| `donor не может автоматически стать Canon` | Accepted ADR-002 Donor Isolation это закрепляет | CONFIRMED |
| `CKS = пассивная память/база знаний` | Knowledge Runtime/Intelligence/Graph/Evolution/Self-Audit уже исполняемые | REJECTED / OUTDATED |
| `CKS не является execution orchestrator KAT9I` | Root Architecture и current snapshot продолжают это явно закреплять | CONFIRMED |
| `общий Core должен объединить state machine CKS и KAT9I` | CKS уже имеет собственный rich lifecycle; объединение создаст ownership collision | REJECTED |
| `CORE_KERNEL_CONTRACT может быть boundary contract` | Совместимо с Independence ADR; пока только candidate до F3/F4 | SUPPORTED HYPOTHESIS |
| `Relation History / Graph Migration / Graph Recovery отсутствуют` | Это было верно в Stage A, но Stage B закрыл три gaps | SUPERSEDED |
| `Graph node lifecycle/versioning не подтверждены` | Stage D добавил отдельный механизм и CI | SUPERSEDED |
| `architecture SSOT pointer сломан` | registry всё ещё указывает `architecture/`, а current self-audit всё ещё не проверяет existence этого pointer | CONFIRMED GAP #29 |
| `CKS main не защищён` | branch `main` всё ещё `protected=false` | CONFIRMED GAP #30 |
| `ADR-001 Independence / ADR-002 Donor Isolation отсутствуют` | Они существуют в `docs/ADR/` и Accepted | REJECTED — прежний вывод был ошибочен |
| `ADR-0001 = CKS independence` | Нет: `decisions/ADR-0001-*` — Multi-Worker Distillate. Independence живёт в другом ADR namespace: `docs/ADR/ADR-001-*` | CORRECTED |
| `CKS #22 CORE KERNEL = принятое решение` | #22 — roadmap/proposal Issue, не Accepted ADR | REJECTED AS CANON |
| `Council v0.1 = часть current CKS` | PR #3 остаётся draft/unmerged | REJECTED AS CURRENT; KEEP AS DATA |

---

## 4. Новые слабые места, выявленные при regression review

### CKS-WEAK-001 — два ADR namespace

Одновременно существуют:

- `docs/ADR/ADR-001`, `ADR-002`, ...;
- `decisions/ADR-0001`, `ADR-0002`, ... .

Это не доказанная функциональная ошибка, но источник высокой ambiguity для AI и человека: `ADR-001` и `ADR-0001` означают разные решения.

Нельзя исправлять переименованием автоматически. Требуется включить в #29/source-map work явную карту namespace/authority.

### CKS-WEAK-002 — current Canon source map недоопределён

`docs/architecture/CKS_CANON_SOURCE_MAP_v1.md` всё ещё прямо говорит, что конкретные пути current Canon / active decisions / superseded variants требуют уточнения.

При наличии нескольких поколений docs и двух ADR namespaces это уже не косметический долг.

### CKS-WEAK-003 — GitHub governance слабее внутренней governance

История CKS почти целиком развивается direct commits в `main`; PR history содержит только один draft PR #3.

Это согласуется с фактом `protected=false` и усиливает #30: внутренние правила Evidence/Decision/Review строже, чем repository mutation boundary.

### CKS-WEAK-004 — Snapshot может быть актуальнее части control pointers

Текущий Snapshot точно описывает рабочий runtime и CI, но сам имеет статус non-Canon. При этом `ssot-registry.yaml` имеет broken architecture pointer.

Следствие: самый полезный current документ не имеет authority, а формальный pointer ведёт не туда. До закрытия #29 каждый AI-проход обязан делать ручной authority resolution.

### CKS-WEAK-005 — rapid-growth provenance risk

Между `a499436...` и текущим snapshot-lineage CKS прошёл десятки содержательных commit за короткий интервал. Это ускорило развитие, но повышает риск, что документация/registry/Issue status не успевают за runtime.

Regression-before-next-step поэтому обязателен, а не рекомендателен.

---

## 5. Поправка к Lost-Ideas Registry

До общей F1-классификации появляются CKS-specific candidates:

- `CKS-LOST-001`: Council v0.1 branch / PR #3 — draft, unmerged; проверить, какие идеи поглощены main, какие остались уникальными.
- `CKS-LOST-002`: deferred Semantic Context Scoping / LLM Anti-Poisoning / Distributed GitHub Bus из #8 — historical research candidates, не Canon.
- `CKS-LOST-003`: ранний Graveyard verification gap (#5) — проверить, был ли полностью поглощён современным lifecycle/archive/rejected механизмом.
- `CKS-LOST-004`: Learning/Ownership/Canon Evidence research tracks (#21–#27) — проверить, какие стали runtime/governance, какие остались research-only.
- `CKS-LOST-005`: Distillation Pipeline (#9/#14) — сопоставить с ADR-0001 Multi-Worker Distillate и фактическим runtime; не считать реализованным только по наличию ADR.
- `CKS-LOST-006`: early agent schemas/protocols и Context Package boundary из #6 — проверить, были изолированы как external contract, legacy или остались ownership gap.

Все эти записи пока `UNASSESSED`; никакого auto-promotion в Genome нет.

---

## 6. Stage 1 progress

### Завершено

- fresh SSoT/HEAD preflight;
- полное перечисление commit history main до пустой page 8;
- полный PR inventory;
- актуальный Issue inventory #1–#30;
- проверка Accepted Independence/Donor Isolation;
- проверка current Runtime/Intelligence state;
- проверка Full Snapshot A–D;
- regression review предыдущих выводов;
- подтверждение GAP #29 и #30.

### Не завершено

- semantic diff review всех архитектурно значимых commit-групп;
- подробный archaeology PR #3 Council branch;
- absorption check каждого research track #5/#8/#9/#14/#21–#27 против current runtime;
- точная карта двух ADR namespaces и authority;
- CKS-specific lost-idea registry до `UNASSESSED=0`.

Stage 1 поэтому остаётся `PARTIAL / RUNNING`, хотя raw commit/PR enumeration уже complete.

---

## 7. Disconnect recovery pointer

При новом чате начинать не с README и не с donor repos.

Порядок восстановления:

1. `KAT9I_OS #233`;
2. этот checkpoint;
3. fresh HEAD KAT9I + CKS;
4. проверить drift от CKS `acc429ca6497b45810e0285220e0a9a8adf4e709`;
5. проверить состояние CKS #29/#30;
6. продолжить Stage 1 semantic review, начиная с `PR #3 Council` и research-track absorption matrix;
7. после каждого блока повторно проверить предыдущие выводы.

Следующий этап не начинается, пока Stage 1 не имеет собственного `POST-CHECKPOINT` с перечислением исправленных старых выводов.