# CKS Archaeology — Stage 1D Issues #21–#27 — 2026-09-17

Status: **DATA ONLY / NON-CANONICAL / DISCONNECT-SAFE CHECKPOINT**  
Governing work item: `KAT9I_OS #233`  
Implementation Worker: ChatGPT  
Independent QA: Antigravity (AGY)

## 0. Scope, fresh anchor and regression

This bounded pass reviews only CKS Issues `#21`–`#27` against current CKS `main`, while re-checking Stage 1A–1C conclusions.

Start anchor inherited from Stage 1C: `302660ecca9f039f274c73905235577fa27b0d41`.

During this pass CKS `main` advanced to:

`20d4263a0ff78701c73fffe2f0840f6fa6669b2d`.

Compare `302660e... → 20d4263...` shows exactly two added audit documents:

- `docs/CKS_POST_SNAPSHOT_INTEGRITY_AUDIT_STAGE_E3_1_A_2026-09-17.md`;
- `docs/CKS_POST_SNAPSHOT_INTEGRITY_AUDIT_STAGE_E3_1_B_2026-09-17.md`.

No runtime/control/schema file changed in that delta. Therefore Stage 1A–1C functional conclusions remain valid, but this checkpoint is anchored to the newer HEAD.

## 1. Issue #21 — GAP register: Learning, Ownership, Canon Evidence Automation

Issue #21 is a useful umbrella GAP register, but current main has already absorbed parts of all three topics.

### Learning Layer Separation

Current CKS already separates Knowledge Runtime and Knowledge Intelligence through accepted ADR-0002, and has executable evolution, quality, graph and recovery tooling. `cks_knowledge_evolution.py` explicitly validates/migrates/evolves/snapshots knowledge without automatic Decision/Canon authority.

What is **not** proven is a distinct autonomous Learning Layer that closes a metric → proposal → validated improvement loop.

Forensic status:

`PARTIALLY_ABSORBED / LEARNING LOOP GAP REMAINS`.

### Ownership Model

The current unified knowledge-object schema requires an `owner`, but current inspected contracts do not formalize the requested distinction:

`Owner != Authority != Agent != Reviewer`.

Stage 1B already found that review/authority metadata is not visibly bound inside `decision_record_v1` itself.

Forensic status:

`PARTIALLY_ABSORBED / ROLE-SEPARATION GAP REMAINS`.

### Canon Evidence Automation

Current main already enforces substantial pieces:

- `automation_is_not_decision: true`;
- `automation_is_not_canon_change: true`;
- `approval_requires_review: true`;
- canonical knowledge transition requires Evidence plus Decision reference;
- `promotion_request_v1` requires Evidence and Decision reference for Canon promotion.

Therefore this is not a greenfield GAP anymore.

Still missing from the exact Issue formulation:

- no verified requirement that History is part of every Canon-candidate guard;
- no single inspected end-to-end guard binds reviewer/authority evidence, Decision, Evidence and history into one promotion proof;
- no independent proof in this bounded pass that the entire guard is exercised in one integration path.

Forensic status:

`PARTIALLY_IMPLEMENTED / END-TO-END PROMOTION EVIDENCE GAP`.

## 2. Issue #22 — CKS Knowledge Learning Roadmap + CORE KERNEL integration

The existing archaeology comment on #22 is correct and remains valid after the current HEAD drift.

The phrase `CORE KERNEL (общий слой)` must **not** be read as an accepted third shared kernel.

Safe current interpretation:

`future shared contract = boundary/meta-invariant contract between independent KAT9I and CKS kernels`.

In particular:

- KAT9I task lifecycle is not CKS knowledge lifecycle;
- one shared State Machine is not justified;
- shared candidates may be transition semantics, Evidence/provenance, authority class, revision binding, anti-loop/recovery semantics and feedback transport;
- any concrete common implementation must wait for the later completeness gate.

Issue #22 remains:

`PROPOSAL / ROADMAP / NOT CANON`.

## 3. Issue #23 — Learning Layer Proposal

Issue #23 asks for an Evidence/Decision chain before introducing a Learning Layer and explicitly freezes Core.

Current main already has:

- Knowledge Intelligence diagnostics;
- Knowledge Health Score metrics;
- Knowledge Evolution operations;
- lifecycle/history/source/evidence data;
- no automatic Decision/Canon authority for analytics.

These mechanisms provide inputs for learning but do not by themselves prove an autonomous self-improvement loop.

The important distinction is:

`analytics + metrics + evolution primitives != autonomous Learning Layer`.

Forensic status:

`RESEARCH / PARTIALLY SUBSUMED PRIMITIVES / DECISION STILL REQUIRED`.

## 4. Issue #24 — Ownership Model Proposal

The proposal remains materially open.

Verified current main:

- `owner` is a required knowledge-object field;
- automation and analytics are explicitly denied Decision/Canon authority;
- review is required for approval.

Not yet verified as one formal model:

- Authority identity;
- Agent identity/capability;
- Reviewer identity;
- separation constraints between those roles;
- binding of role evidence to accepted/canonical decisions.

Therefore #24 is not duplicate work, but it must start from existing `owner` and governance semantics rather than introduce a parallel ownership system.

Forensic status:

`OPEN RESEARCH GAP / MUST EXTEND, NOT DUPLICATE, CURRENT CONTRACTS`.

## 5. Issue #25 — Canon Evidence Guard

Issue rule:

`Decision + Evidence + History = Canon candidate`.

Current main already has a strong partial guard:

- state-machine transition to `canonical` requires at least one Evidence item and Decision reference;
- promotion request to `canon` requires Evidence and Decision reference;
- automation cannot itself create Canon;
- approval requires review.

But the exact Issue rule is not fully encoded by the inspected contracts:

- History is not an explicit prerequisite in the canonical transition validator;
- reviewer/authority evidence is not visibly part of the promotion request schema;
- one end-to-end Canon-candidate proof bundle is not verified here.

Forensic status changes from generic research to:

`PARTIALLY_IMPLEMENTED / GUARD-COMPLETENESS GAP`.

This should be treated as refinement/hardening, not a new Canon subsystem.

## 6. Issue #26 — Evidence Pack 001 Review

Issue #26 is a research packaging task for Learning, Ownership and Canon Guard.

Because #21/#23/#24/#25 were created before several current-main capabilities matured, the Evidence Pack must be re-baselined against current HEAD before it can support a Decision.

An exact repository search in this bounded pass did not verify a current artifact named `Evidence Pack 001`.

Required forensic interpretation:

`EVIDENCE PACK TASK OPEN / CONTENT MUST DESCRIBE DELTA, NOT ASSUME ZERO IMPLEMENTATION`.

The pack should explicitly separate:

- already-implemented primitives;
- still-missing contracts;
- missing executable proof;
- policy choices that remain research.

## 7. Issue #27 — Research Package 001 / ten tracks

Issue #27 is valuable as an idea-preservation umbrella but is too coarse to be used as a direct implementation queue without re-baselining.

Track-by-track current forensic classification:

| Track | Current status |
|---|---|
| Learning Layer | primitives exist; autonomous loop remains research |
| Ownership Model | owner exists; role/authority separation remains open |
| Canon Evidence Guard | partially implemented; completeness/integration gap |
| Graveyard Verification | specified + partial runtime; end-to-end test gap from Stage 1C |
| Evidence Matrix | not verified as one authoritative current contract in this bounded pass |
| Decision Quality Model | research candidate; no authority promotion implied |
| Knowledge Lifecycle Metrics | partially absorbed: Knowledge Health Score/Intelligence metrics exist |
| Research Isolation Rules | principle already present: research/proposals cannot auto-change Core/Canon |
| Automation Guard Expansion | baseline guard already exists in `automation-governance.yaml`; expansion remains research |
| v1.3 Review Gate | no new Core promotion until normal GAP → Evidence → Proposal → Decision path |

Therefore Issue #27 should be treated as:

`RESEARCH INDEX / DELTA-REBASE REQUIRED`,

not as ten missing components.

## 8. Cross-issue corrections and risks

### CKS-WEAK-012 — Roadmap inflation from stale GAP wording

Several v1.3 Issues describe capabilities as future work even though current main now contains partial or substantial implementations.

Risk: creating duplicate subsystems because Issues are read as current architecture rather than historical work items.

Required rule:

`fresh repository capability map > stale Issue wording`.

### CKS-WEAK-013 — “Learning” is overloaded

Current CKS has analytics, quality metrics, state evolution and recovery. Calling all of that a “Learning Layer” would hide the actual missing question: how validated feedback creates a proposal/improvement without granting analytics autonomous Decision authority.

Forensic definition to preserve:

`Learning candidate = measured feedback → explicit proposal → evidence/challenge → decision → versioned change → post-change measurement`.

No automatic Canon mutation is implied.

### CKS-WEAK-014 — Ownership must not import KAT9I task ownership wholesale

CKS knowledge `owner` and KAT9I execution Worker/Reviewer/authority roles solve different lifecycle problems.

A future shared boundary contract may map role classes, but must not collapse the two ownership models into one runtime object.

### CKS-WEAK-015 — Canon Guard already exists in fragments

Creating another standalone “Canon Guard engine” would duplicate current state-machine, promotion-request and automation-governance rules.

Correct direction is contract consolidation + end-to-end evidence, not another authority layer.

## 9. Previous-result regression verdict

Stage 1A: **holds**. The semantic-CI caution remains required.

Stage 1B: **holds**. Council remains Proposal; exact reviewer-count/disagree-branch rules are not current invariants.

Stage 1C: **holds with stronger support**. Graveyard and Distillation are partially implemented; missing proof/integration remains the real gap.

New Stage 1D correction:

- #21/#25/#27 overstate “future missing capability” if read literally against current main;
- #22 shared Core Kernel remains a hypothesis and must stay a boundary-contract candidate;
- #23 Learning Layer remains research because current metrics/intelligence do not equal autonomous learning;
- #24 role separation remains genuinely open.

## 10. Lost-ideas / completeness seeds

Carry forward without promotion:

- `CKS-LOST-L01`: explicit validated learning loop: Metrics/Feedback → Proposal → Decision → Change → post-change Metrics;
- `CKS-LOST-L02`: learning-event object and traceability to improvement outcome;
- `CKS-LOST-O01`: Owner/Authority/Agent/Reviewer role-separation contract;
- `CKS-LOST-O02`: authority/review evidence binding to Decision/Canon promotion;
- `CKS-LOST-CG01`: consolidated Canon candidate evidence bundle including History + Decision + Evidence + review/authority trace;
- `CKS-LOST-CG02`: end-to-end Canon guard integration test;
- `CKS-RESEARCH-Q01`: Decision Quality Model;
- `CKS-RESEARCH-M01`: lifecycle metrics beyond current health diagnostics;
- `CKS-BOUNDARY-O01`: role-class mapping across CKS/KAT9I without lifecycle collapse.

These remain registry seeds only. No ABC×XYZ or Genome/Core promotion is assigned.

## 11. Stage 1D completion condition

Stage 1D is COMPLETE for the bounded question: **what do Issues #21–#27 still represent after comparison with current main?**

Result:

- many listed “future” capabilities are partly implemented;
- the real remaining work is learning-loop authority, role separation, guard consolidation and executable proof;
- Issue #22 cannot authorize a shared third kernel;
- Issue #27 must be re-baselined as a research index, not executed as ten greenfield modules.

Next bounded part per PR #239 work order: **Stage 1E — ADR namespace + Canon/SSoT authority map**, again beginning with fresh CKS HEAD and regression of Stage 1A–1D conclusions.

Genome/Kernel synthesis remains BLOCKED until the completeness gate.