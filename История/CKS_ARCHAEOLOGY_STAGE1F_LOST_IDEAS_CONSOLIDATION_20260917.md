# CKS Archaeology — Stage 1F Lost-Ideas / Gap Consolidation — 2026-09-17

Status: **DATA ONLY / NON-CANONICAL / DISCONNECT-SAFE CHECKPOINT**  
Governing work item: `KAT9I_OS #233`  
Implementation Worker: ChatGPT  
Independent QA: Antigravity (AGY)

## 0. Fresh-head and regression gate

Fresh CKS `main` at Stage 1F start:

`db5d0e5fb521f2747a2fadc8c077f2b17851239f`

No drift from corrected Stages 1C–1E was observed at start of consolidation.

This document consolidates **only CKS Stage 1A–1E findings**. It does not claim #233 F0/F1 completeness for KAT9I history, predecessor repos, Rules Hub, all closed PRs, or donors.

## 1. Deduplication rule

Items are merged when they describe the same underlying concern across multiple Issues/checkpoints. The resulting classes are:

- `CURRENT_INVARIANT` — semantic rule already present in current CKS;
- `OPEN_GAP` — evidenced unresolved capability/traceability problem;
- `RESEARCH_ONLY` — idea preserved without sufficient GAP/Decision proof;
- `BOUNDARY_CANDIDATE` — cross-system concern requiring KAT9I comparison;
- `SUPERSEDED_INTERPRETATION` — older framing contradicted by current architecture;
- `HISTORICAL_EVIDENCE` — useful evolution evidence, not current authority.

## 2. Current invariants preserved

| ID | Invariant | Current status | Main evidence line |
|---|---|---|---|
| `CKS-INV-01` | Proposal/automation is not Decision | CURRENT_INVARIANT | automation governance + lifecycle rules |
| `CKS-INV-02` | Automation/analytics cannot create Canon by themselves | CURRENT_INVARIANT | automation governance + ADR-0002 boundaries |
| `CKS-INV-03` | Evidence/Decision linkage is required for Canon promotion semantics | CURRENT_INVARIANT | lifecycle/promotion contracts |
| `CKS-INV-04` | CKS knowledge lifecycle is distinct from KAT9I execution/task lifecycle | CURRENT_INVARIANT | accepted independence Decision + ADR-0002 + bootstrap boundaries |
| `CKS-INV-05` | Rejected/history material is preserved but not active knowledge automatically | CURRENT_INVARIANT | Graveyard protocol/spec/lifecycle |
| `CKS-INV-06` | Core frozen; Runtime evolving; experiments isolated | CURRENT_INVARIANT | `control/system-state.yaml` |
| `CKS-INV-07` | CI success is Evidence, not Canon | CURRENT_INVARIANT | Stage 1A regression / post-snapshot audit behavior |

These invariants are not “lost ideas”; they are retained here to prevent false rediscovery.

## 3. Consolidated OPEN GAP registry

### `CKS-GAP-01` — Architecture SSoT path authority

Sources: Stage 1A, Stage 1E, CKS #29.

Problem:
`control/ssot-registry.yaml` points `architecture.path` to missing root `architecture/`; Canon source map still lacks exact authoritative paths.

Status: `OPEN_GAP`.

Do not infer a replacement path without Decision.

### `CKS-GAP-02` — ADR identity collision

Source: Stage 1E.

Problem:
current `decisions/` contains accepted Multi-Worker Distillate as `ADR-0001`, while `ARCHITECTURE_DECISION_RECORD.md` independently declares accepted `ADR-0001: CKS as independent knowledge system`.

Status: `OPEN_GAP / TRACEABILITY`.

Needs migration/alias decision, not silent renaming.

### `CKS-GAP-03` — Review/authority evidence binding

Sources: Stage 1B, 1D, 1E; #24 research.

Problem:
review is required, but inspected Decision contracts do not provide one unambiguous binding for reviewer/authority identity and challenge evidence.

Status: `OPEN_GAP CANDIDATE / NEEDS AUTHORITY-MAP DECISION`.

### `CKS-GAP-04` — Graveyard end-to-end verification

Sources: Stage 1C, #5.

Problem:
Graveyard is specified and partially implemented, but full persistence → exclusion from active/Canon → rejected-history retrieval → non-automatic resurrection path lacks one verified end-to-end test.

Status: `OPEN_VERIFICATION_GAP`.

### `CKS-GAP-05` — Distillation integration authority

Sources: Stage 1C, #9/#14.

Problem:
Distillate, ingestion, Decision/Evidence, Graveyard and Bootstrap primitives exist, but exact authority/relationship chain and Snapshot recovery contract are not verified as one stabilized end-to-end protocol.

Status: `OPEN_INTEGRATION_GAP`.

### `CKS-GAP-06` — Canon Guard completeness

Sources: Stage 1D, #25.

Problem:
essential safety principle exists, but History + Decision + Evidence + review/authority trace is not verified as one complete machine-checkable promotion bundle.

Status: `OPEN_HARDENING_GAP`.

### `CKS-GAP-07` — Semantic CI strength / historical proof quality

Source: Stage 1A.

Problem:
historical green CI can be semantically weak or false-green. Archaeology must distinguish `CI existed / ran / assertions meaningful / feature exercised`.

Status: `METHOD/GOVERNANCE GAP`, already partly addressed in newer CKS tests but still mandatory for historical evidence review.

## 4. RESEARCH_ONLY registry

| ID | Idea | Source | Why not promoted |
|---|---|---|---|
| `CKS-R-01` | Semantic Context Scoping / vector retrieval | #8 | no confirmed GAP→Decision chain |
| `CKS-R-02` | LLM Anti-Poisoning independent review | #8 | useful pattern, exact mechanism not approved |
| `CKS-R-03` | Distributed GitHub Bus | #8 | execution/topology research, not CKS Core proof |
| `CKS-R-04` | Separate autonomous Learning Layer | #21/#23 | Runtime/Intelligence/Evolution already exist; extra layer not proven necessary |
| `CKS-R-05` | Decision Quality Model | #27 | research only |
| `CKS-R-06` | Evidence Matrix as architecture component | #27 | may be view/tooling rather than architecture |
| `CKS-R-07` | fixed reviewer count / mandatory disagree branch | Council PR #3 | governance policy candidate, unmerged |
| `CKS-R-08` | fixed anti-loop review cycle count | Council PR #3 | exact value is policy/experiment, not invariant |

## 5. BOUNDARY_CANDIDATE registry

| ID | Candidate | Source | Constraint |
|---|---|---|---|
| `CKS-B-01` | revision/base-reference binding across knowledge→execution boundary | Council PR #3 | compare against KAT9I existing promotion/evidence contracts |
| `CKS-B-02` | one-writer external mutation boundary | Council PR #3 | execution concern, not CKS knowledge Core |
| `CKS-B-03` | idempotent hashed job/evidence transport | Council PR #3 | integration transport candidate |
| `CKS-B-04` | Worker/KAT9I/CKS Distillate ownership map | Stage 1C | Worker transport must not imply Canon authority |
| `CKS-B-05` | role-class mapping Owner/Authority/Agent/Reviewer across systems | Stage 1D | must not collapse task and knowledge lifecycles |
| `CKS-B-06` | future CORE artifact as boundary/meta-invariant contract | #22 / Stage 1D | must not become third SSoT or third runtime kernel |

## 6. SUPERSEDED interpretations

### `CKS-SUP-01` — “CKS is only a passive knowledge store”

Superseded by current Knowledge Runtime / Knowledge Intelligence / evolution/recovery/self-audit architecture.

### `CKS-SUP-02` — “Council is the missing CKS Decision engine”

Superseded: current main already has Decision/Evidence/lifecycle/promotion primitives. Council remains an optional governance policy proposal.

### `CKS-SUP-03` — “Issue #5 capability is entirely missing”

Superseded: Graveyard specification/runtime pieces exist; remaining gap is end-to-end proof.

### `CKS-SUP-04` — “Issues #9/#14 are greenfield architecture”

Superseded: multiple required primitives already exist; remaining work is integration/stabilization.

### `CKS-SUP-05` — “CORE KERNEL means a third shared owning kernel”

Superseded by current separation. Safe hypothesis is only boundary/meta-invariant contract pending #233 completeness.

## 7. Historical Evidence worth retaining

- Council PR #3 as alternative governance design and source of challenge/revision/idempotency ideas;
- false-green historical v1.6 CI episode as proof that CI semantic strength must be audited;
- #8 “Штурм” as preserved high-uncertainty research pool;
- #21–#27 as historical roadmap intent, but always re-baselined against current capabilities.

None of these is current Canon merely because it is preserved.

## 8. Local completeness check for CKS Stage 1

Within the bounded Stage 1A–1E material reviewed here:

- duplicate concepts have been merged;
- each retained item has a status class;
- known stale interpretations are explicitly marked superseded;
- current invariants are separated from open gaps and research;
- boundary concerns are separated from CKS-owned gaps;
- no donor material has been introduced.

Local result:

`CKS_STAGE1_UNASSESSED = 0` for the items discovered in Stages 1A–1E.

This is **not** the same as global `#233 F1 UNASSESSED = 0`. KAT9I history/predecessors/closed PRs still need completion before F3.

## 9. POST-CHECKPOINT regression

CKS main remained `db5d0e5fb521f2747a2fadc8c077f2b17851239f` through the Stage 1F start check. A new fresh-head check is required before the next forensic family begins.

No Canon/Core/SSoT mutation was made by Stage 1F.

## 10. Stage 1F state

CKS Stage 1A–1F forensic cycle is **LOCALLY COMPLETE** for the bounded sources reviewed.

The resulting registry is ready to feed #233 F1, but it is not yet eligible for final ABC×XYZ/Genome synthesis because #233 requires the full own-lineage history first.

Next forensic work should return to **KAT9I own-history F0/F1**, not donors and not final CORE synthesis.