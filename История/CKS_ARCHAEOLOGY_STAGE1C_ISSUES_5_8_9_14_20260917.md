# CKS Archaeology — Stage 1C Issues #5/#8/#9/#14 — 2026-09-17

Status: **DATA ONLY / NON-CANONICAL / DISCONNECT-SAFE CHECKPOINT**  
Governing work item: `KAT9I_OS #233`  
Implementation Worker: ChatGPT  
Independent QA: Antigravity (AGY)

## 0. Fresh-head regression first

Previous Stage 1C draft was anchored to `302660ecca9f039f274c73905235577fa27b0d41` and stated that no new drift existed. That statement is now stale.

Fresh CKS `main` at re-check:

`db5d0e5fb521f2747a2fadc8c077f2b17851239f`

Delta `302660e... → db5d0e5f...` = **17 commits**. The delta is not documentation-only: three workflows were modified, two workflows were removed, bootstrap/control validators changed, and a new workflow-exit-semantics test was added. Therefore all current-state claims in this checkpoint are re-anchored to `db5d0e5f...`.

The Graveyard protocol blob remains unchanged (`a1b58372815b417671bdb96a0a00569a4f5b8474`), so the bounded Graveyard semantic conclusions below survive this regression. Stage 1A/1B remain historical Evidence, but their freshness must not be inferred beyond their recorded anchors.

## 1. Issue #5 — rejected-idea / Graveyard lifecycle

Issue #5 is OPEN. Its original `MISSING_VERIFIABLE_CAPABILITY` wording is too broad if read as “nothing exists”. Current repository state already contains Graveyard schema/protocol/spec and terminal rejected/archived semantics.

Correct forensic status:

`PARTIALLY_IMPLEMENTED / MISSING END-TO-END VERIFICATION`

Still not proven end-to-end in the evidence reviewed here:

- rejection reason/provenance survives the complete persistence path;
- rejected objects are excluded from active/Canon query results;
- rejected history is retrievable through the intended access path;
- resurrection is not automatic;
- one integration test proves the whole sequence.

This is a verification gap, not permission to expand Core.

## 2. Issue #8 — deferred architecture ideas / “Штурм”

Issue #8 remains `AZ / research_only`.

Preserved candidates:

- Semantic Context Scoping / vector retrieval;
- LLM Anti-Poisoning review;
- Distributed GitHub Bus;
- F-092 Agent Boundary;
- F-093 Context Package Boundary.

No candidate has a verified GAP → Evidence → Proposal → Decision chain sufficient for Core promotion. These items belong in the lost-ideas/research registry, not the current architecture contract.

## 3. Issue #9 — Chat Distillation Pipeline

Issue #9 remains an active supporting-architecture task. Current main already contains several primitives around Distillate, ingestion, Decision/Evidence, Graveyard and Bootstrap, so #9 is not greenfield.

Stable ownership boundary retained:

`RAW CHAT → Distillate → Decision → Evidence → Learning Event → Bootstrap Snapshot`

CKS owns knowledge validation/storage semantics. It does not become the KAT9I Worker/task execution lifecycle. Snapshot restores context/state but does not control execution.

Forensic status:

`PARTIALLY_ABSORBED / ACTIVE INTEGRATION GAP`

## 4. Issue #14 — implementation plan for #9

Issue #14 is OPEN and has no comments. It explicitly blocks automatic processing until object contracts, decision-extraction rules, Distillation output format and Snapshot linkage are stabilized.

Some prerequisites already exist; this Issue therefore cannot be described as blocked on all schemas. But it also cannot prove that automation is ready.

Correct status:

`PREREQUISITES PARTIALLY SATISFIED / AUTOMATION GATE STILL CLOSED`

## 5. Corrections and conflict checks

- `CKS-CORR-1C-01`: Issue #5 is not wholly missing; it is partially implemented with missing end-to-end proof.
- `CKS-CORR-1C-02`: Issue #8 must not be promoted into Genome/Foundation directly; it remains Research/Graveyard material.
- `CKS-CORR-1C-03`: Issue #9 defines an integration target over existing primitives; #14 is only an implementation-plan dependency and cannot prove completion.
- `CKS-CORR-1C-04`: the new 17-commit delta disproves the earlier draft statement that there was no post-Stage-1B drift. Fresh-head regression is mandatory at every substage.

## 6. Lost-ideas / gap seeds

- `CKS-GAP-G01`: Graveyard end-to-end persistence/query/non-resurrection proof — `OPEN VERIFICATION GAP`.
- `CKS-RESEARCH-R01`: Semantic Context Scoping — `RESEARCH_ONLY`.
- `CKS-RESEARCH-R02`: LLM Anti-Poisoning review — `RESEARCH_ONLY`.
- `CKS-RESEARCH-R03`: Distributed GitHub Bus — `RESEARCH_ONLY`.
- `CKS-GAP-G02`: F-092 Agent Boundary — `GAP_CANDIDATE / NEEDS EVIDENCE`.
- `CKS-GAP-G03`: F-093 Context Package Boundary — `GAP_CANDIDATE / NEEDS EVIDENCE`.
- `CKS-FLOW-D01`: Chat Distillation → Decision/Evidence/Learning/Snapshot chain — `ACTIVE SUPPORTING ARCHITECTURE`.
- `CKS-PLAN-D02`: automatic Distillation implementation plan — `BLOCKED ON CONTRACT STABILITY`.

No canonical ABC×XYZ or Genome-value assignment is finalized here; #233 requires F1 completion first.

## 7. Stage 1C completion state

Stage 1C is **COMPLETE for the bounded scope #5/#8/#9/#14**, rechecked against fresh CKS `main` `db5d0e5f...`.

Next bounded part: **Stage 1D — Issues #21–#27 only**, again starting from a fresh CKS HEAD and regression of Stage 1A–1C conclusions.

Genome/Kernel synthesis remains BLOCKED by #233 F0–F3 gates.