# CKS Archaeology — Stage 1C Issues #5/#8/#9/#14 — 2026-09-17

Status: **DATA ONLY / NON-CANONICAL / DISCONNECT-SAFE CHECKPOINT**  
Governing work item: `KAT9I_OS #233`  
Implementation Worker: ChatGPT  
Independent QA: Antigravity (AGY)

## 0. Scope and fresh-anchor regression

This bounded pass reviews only CKS Issues `#5`, `#8`, `#9`, `#14` against fresh CKS `main`.

Fresh CKS main anchor at start and re-check: `302660ecca9f039f274c73905235577fa27b0d41`.

No new CKS drift was observed relative to the post-Stage-1B anchor already recorded in PR #239. Therefore the prior Stage 1A/1B conclusions remain valid unless explicitly corrected below.

Regression guards retained:

- green CI alone is not proof that the advertised semantic path is exercised;
- current main wins over historical Issue wording when the repository has evolved;
- Issue/Proposal/Research material is not Canon by existence alone;
- rejected/archive material remains DATA/history unless promoted through the current lifecycle;
- CKS knowledge lifecycle and KAT9I task lifecycle remain separate ownership domains.

## 1. Issue #5 — rejected idea / Graveyard lifecycle

### Historical claim

Issue #5 recorded `MISSING_VERIFIABLE_CAPABILITY` for a full rejected-idea lifecycle and correctly refused a synthetic PASS.

### Current-main delta

The gap has narrowed materially since the Issue was written.

Verified current-main artifacts now include:

- `schemas/graveyard_item_v1.yaml` with archived/review_candidate/restored states;
- `protocols/graveyard_protocol.md` preserving original idea, rejection reason, evidence, revival conditions and review date;
- `docs/DECISION_GRAVEYARD_SPEC.md` with archived → review candidate → restored/closed semantics;
- `control/lifecycle-state-model.yaml` declaring archived/rejected terminal and automation-not-decision;
- `tools/cks_knowledge_state_machine.py` making `rejected` and `archived` terminal in the knowledge runtime;
- `schemas/cks-knowledge-object.schema.json` carrying source/evidence/history and rejected/archived states;
- `council/pilot/CKS_1.2_GRAVEYARD_LIFECYCLE_VALIDATOR_SPEC.md` defining the expected rejected-history checks.

### What is still not verified

In the bounded current test tree inspected here, no dedicated Graveyard runtime/integration test was found that proves all Issue #5 acceptance criteria end-to-end, especially:

- persistence of rejection reason/provenance through the actual storage path;
- exclusion from active knowledge/Canon in a real query path;
- historical retrieval of the rejected object;
- attempted resurrection being rejected by executable integration evidence rather than only schema/state-machine rules.

Therefore Issue #5 should **remain open**, but its forensic status changes from `MISSING_CAPABILITY` to:

`PARTIALLY_IMPLEMENTED / MISSING END-TO-END VERIFICATION`.

This is a correction to any earlier reading that treated #5 as still completely unimplemented.

## 2. Issue #8 — deferred architecture ideas / “Штурм”

Issue #8 contains research candidates:

- Semantic Context Scoping / vector RAG;
- LLM anti-poisoning review;
- Distributed GitHub Bus;
- F-092 Agent Boundary;
- F-093 Context Package Boundary.

The existing ABC/XYZ comment classifies them `AZ / research_only`, which remains consistent with current evidence.

In this bounded pass no current-main canonical implementation was verified for the exact vector-RAG, anti-poisoning-neuro-review, or distributed-GitHub-bus proposals. Current CKS does have richer Knowledge Runtime/Intelligence machinery, but that does not promote these exact Issue #8 mechanisms automatically.

Forensic status remains:

`RESEARCH / GRAVEYARD CANDIDATES / NO CORE PROMOTION`.

Important preservation rule: these ideas stay searchable as possible future experiments, but are not permitted to rewrite current Core or boundary contracts without a fresh GAP → Evidence → Proposal → Decision path.

## 3. Issue #9 — Chat → Decision → Graveyard → Bootstrap Snapshot

### What current main already has

Several requested primitives now exist independently of the Issue:

- `schemas/distillate_object_v1.yaml`;
- `protocols/ingestion_protocol.md`;
- `protocols/result_ingestion_protocol.md`;
- `docs/CONTEXT_INGESTION_PIPELINE.md`;
- Decision/Evidence/Context/Artifact/Candidate schemas in the registries;
- Graveyard schema/protocol/spec;
- Bootstrap snapshots and chat-migration standard;
- accepted ADR-0001 for Multi-Worker Distillate;
- accepted ADR-0002 for the Knowledge Runtime / Knowledge Intelligence split.

This proves that Issue #9 is no longer a blank architecture proposal.

### What remains open

The exact acceptance package requested by #9 is not yet fully verified:

- no dedicated `Chat Distillation Protocol v1` was verified in current main under that explicit authority;
- the Object Registry still describes Snapshot as `проектируется` rather than a stabilized formal schema;
- the exact relation `Decision → Evidence → Experiment → Result → Learning Event` is not yet verified as one enforceable contract;
- no end-to-end recovery test was verified proving that a new chat can reconstruct required state solely from the CKS Snapshot package;
- raw discussion/history still requires a precise retention/exclusion policy so that CKS stores validated meaning without losing useful rejected alternatives.

Forensic status:

`PARTIALLY_ABSORBED / ACTIVE GAP`.

The Issue remains useful as the integration target connecting already-existing primitives.

## 4. Issue #14 — Distillation Pipeline implementation plan

Issue #14 says automation begins after object contracts, extraction rules, distillation result format, and Snapshot linkage are stabilized.

Current-main evidence shows that the prerequisite set is partly present:

- object contracts and registries exist;
- distillate format exists;
- ingestion/result protocols exist;
- decision/evidence lifecycle exists.

But the same evidence also shows unfinished prerequisites:

- Snapshot is not yet a stabilized registered schema;
- Candidate Object is still marked as requiring audit in the schema registry;
- the exact Chat Distillation authority/protocol is not established as a single current SSoT;
- Graveyard lifecycle still lacks full executable acceptance evidence.

Therefore #14 should not be treated as blocked on *all* schemas, nor as ready for broad automation.

Corrected status:

`PREREQUISITES PARTIALLY SATISFIED / AUTOMATION GATE STILL CLOSED`.

## 5. Cross-issue consistency findings

### CKS-WEAK-009 — Graveyard specification outruns executable proof

The repository now has enough schema/protocol/state-machine material that calling Graveyard “missing” is stale, but not enough bounded test evidence to call the complete lifecycle verified.

Required distinction:

`SPECIFIED + PARTIAL RUNTIME != END-TO-END VERIFIED`.

### CKS-WEAK-010 — Distillation authority is distributed across multiple artifacts

Issue #9, ADR-0001, `distillate_object_v1`, ingestion protocols, bootstrap docs and registries all describe adjacent parts of distillation. A single authority map is still needed to state which artifact owns:

- Worker output contract;
- validation/promotion boundary;
- Graveyard routing;
- Snapshot assembly;
- Learning Event creation;
- cross-system handoff to KAT9I.

This is an SSoT/traceability problem, not evidence that another execution engine is needed.

### CKS-WEAK-011 — Distillate wording risks execution-boundary confusion

`distillate_object_v1.yaml` describes transfer from Worker to KAT9I_OS, while CKS Issue #9 describes a CKS distillation pipeline. These are compatible only if the boundary is explicit: Worker/KAT9I may produce or transport candidate artifacts, while CKS owns knowledge validation/storage semantics. No direct Worker authority over CKS Canon is implied.

This must later be reconciled against KAT9I #216/#217 rather than solved by duplicating schedulers or knowledge stores.

## 6. Previous-result regression verdict

Stage 1A: **holds**. The false-green CI lesson and #29/#30 governance gaps are not invalidated by this pass.

Stage 1B: **holds**. Council remains a non-canonical governance proposal; current main already owns Decision/Evidence/promotion primitives. Stage 1C strengthens the conclusion that exact review-count/disagree-branch policies must not be smuggled into a shared Core contract.

Correction introduced by Stage 1C:

- Issue #5 is **not** “fully missing” anymore; it is partially implemented but lacks complete executable verification.
- Issues #9/#14 are **not** greenfield; they are integration/stabilization tasks over primitives that already exist.

## 7. Lost-ideas / completeness seeds

Carry forward into Stage 1F without promotion:

- `CKS-LOST-G01`: dedicated Graveyard end-to-end validator covering all #5 acceptance criteria;
- `CKS-LOST-G02`: explicit rejected-history query/retrieval path distinct from active knowledge;
- `CKS-LOST-D01`: canonical Chat Distillation Protocol linking context split → candidates → validation → Decision/Evidence/Graveyard → Snapshot;
- `CKS-LOST-D02`: formal Snapshot schema + restore test;
- `CKS-LOST-D03`: explicit Learning Event object/relationship contract for distillation outcomes;
- `CKS-RESEARCH-R01`: Semantic Context Scoping/vector retrieval candidate;
- `CKS-RESEARCH-R02`: anti-poisoning independent review candidate;
- `CKS-RESEARCH-R03`: distributed GitHub bus candidate;
- `CKS-BOUNDARY-D01`: authoritative ownership map for Worker/KAT9I/CKS distillate transport vs knowledge promotion.

These are forensic registry seeds only. No ABC×XYZ or Genome/Core promotion is assigned here.

## 8. Stage 1C completion condition

Stage 1C is COMPLETE for the bounded question: **what do CKS Issues #5/#8/#9/#14 still represent after comparison with current main?**

Result:

- #5: narrowed implementation/verification gap;
- #8: research-only ideas preserved;
- #9: active integration gap over existing primitives;
- #14: partial prerequisites, automation gate still closed.

Next bounded part per PR #239 work order: **Stage 1D — Issues #21–#27 only**, again beginning with fresh CKS HEAD and regression of Stage 1A–1C conclusions.

Genome/Kernel synthesis remains BLOCKED until the later completeness gate.