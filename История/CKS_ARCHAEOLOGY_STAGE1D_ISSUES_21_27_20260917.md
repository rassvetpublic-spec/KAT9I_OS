# CKS Archaeology — Stage 1D Issues #21–#27 — 2026-09-17

Status: **DATA ONLY / NON-CANONICAL / DISCONNECT-SAFE CHECKPOINT**  
Governing work item: `KAT9I_OS #233`  
Implementation Worker: ChatGPT  
Independent QA: Antigravity (AGY)

## 0. Fresh-head regression

Fresh CKS `main` before this bounded pass:

`db5d0e5fb521f2747a2fadc8c077f2b17851239f`

The previous Stage 1D draft was anchored to older `20d4263...`. It is therefore historical only. Stage 1D is rechecked against `db5d0e5f...`.

Stage 1C had already established that the larger `302660e... → db5d0e5f...` delta contains functional workflow/validator changes, so no blanket “documentation-only drift” claim is reused here.

## 1. Issue #21 — v1.3 GAP register

Issue #21 is an umbrella Research register for:

1. Learning Layer Separation
2. Ownership Model
3. Canon Evidence Automation

It explicitly proposes no Core change and requires `GAP → Evidence → Proposal → Decision → Minimal Change`.

Forensic status:

`RESEARCH UMBRELLA / NOT CANON / NEEDS PER-TRACK EVIDENCE`

## 2. Issue #22 — Knowledge Learning Roadmap + CORE KERNEL integration

The Issue body contains an older shared-`CORE KERNEL` hypothesis. Its own later archaeology comment already corrects that interpretation after CKS Runtime/Intelligence growth.

Current safe interpretation:

`future shared artifact = boundary/meta-invariant contract between independent KAT9I and CKS kernels`

not a third owning Core or one shared state machine.

Useful candidate meta-invariants remain Evidence/provenance, authority class, revision binding, transition semantics, anti-loop/recovery and feedback transport. None is promoted merely because #22 lists it.

Forensic status:

`SUPERSEDED INTERPRETATION / ACTIVE BOUNDARY-CONTRACT HYPOTHESIS`

## 3. Issue #23 — Learning Layer Proposal

Issue #23 is Research-only and requires Evidence/Decision before change.

Current CKS already has Knowledge Runtime, Knowledge Intelligence, metrics/analytics and evolution primitives. Therefore the unresolved question is not “does learning-related machinery exist?” but whether a distinct autonomous Learning Layer adds value without duplicating those mechanisms or acquiring Decision/Canon authority.

Forensic status:

`RESEARCH GAP CANDIDATE / PARTIALLY ABSORBED CONCERNS / SEPARATE LAYER NOT PROVEN`

## 4. Issue #24 — Ownership Model Proposal

Issue #24 proposes:

`Owner != Authority != Agent != Reviewer`

This remains Research-only.

Stage 1B already found the related traceability question: governance requires review, while the visible Decision schema does not itself bind reviewer/authority metadata. That gives #24 a plausible evidence basis, but the exact role model is not current Canon.

Forensic status:

`SUPPORTED GAP CANDIDATE / POLICY MODEL NOT YET CANON`

## 5. Issue #25 — Canon Evidence Guard

Issue #25 defines `Decision + Evidence + History = Canon candidate` and explicitly denies automation the authority to create Canon.

Current main already absorbs the essential safety principle: automation is not Decision/Canon authority and canonical promotion depends on Decision/Evidence semantics.

Remaining value is guard completeness and end-to-end proof, especially History/review/authority binding, not creation of another Canon subsystem.

Forensic status:

`PRINCIPLE ABSORBED / GUARD-COMPLETENESS GAP`

## 6. Issue #26 — Evidence Pack 001 Review

Issue #26 packages research Evidence for Learning, Ownership and Canon Guard. It is process/Evidence work, not an architecture Decision.

Because current CKS matured after these Issues were opened, any Evidence Pack must describe current delta rather than assume zero implementation.

Forensic status:

`RESEARCH EVIDENCE PACKAGE / REBASE TO CURRENT MAIN REQUIRED`

## 7. Issue #27 — Research Package 001 / ten tracks

Issue #27 is an idea-preservation/research index, not proof of ten missing architecture components.

Several tracks overlap already-known mechanisms or gaps:

- Graveyard Verification → Stage 1C / #5;
- Knowledge Lifecycle Metrics → existing Runtime/Intelligence analytics direction;
- Automation Guard Expansion → existing automation-governance baseline;
- Ownership/Decision Quality/Review Gate → governance research;
- Evidence Matrix → likely traceability/tooling concern until proven architectural.

Forensic status:

`RESEARCH BACKLOG / DECOMPOSE AND REBASE BEFORE PROMOTION`

## 8. Corrections

- `CKS-CORR-1D-01`: #22 does not establish a shared third Core; only boundary-contract hypothesis survives.
- `CKS-CORR-1D-02`: #23 must first prove a separate Learning Layer is needed beyond Runtime/Intelligence/Evolution.
- `CKS-CORR-1D-03`: #24 has a real traceability basis, but exact role semantics remain policy research.
- `CKS-CORR-1D-04`: #25's safety principle is already absorbed; remaining work is executable guard coverage/evidence.
- `CKS-CORR-1D-05`: #27 is a research queue, not a component list.
- `CKS-CORR-1D-06`: previous Stage 1D anchor `20d4263...` is stale; this checkpoint is re-anchored to `db5d0e5f...`.

## 9. Lost-ideas / gap seeds

- `CKS-GAP-O01`: bind review/authority evidence to accepted/canonical decisions — `SUPPORTED GAP CANDIDATE`.
- `CKS-RESEARCH-L01`: determine whether a separate Learning Layer adds value beyond current Runtime/Intelligence/Evolution — `RESEARCH_ONLY`.
- `CKS-GUARD-C01`: machine-verifiable Canon Evidence Guard completeness — `PARTIALLY ABSORBED / VERIFY COVERAGE`.
- `CKS-RESEARCH-Q01`: Decision Quality Model — `RESEARCH_ONLY`.
- `CKS-RESEARCH-M01`: Evidence Matrix / traceability view — `RESEARCH_OR_TOOLING`.
- `CKS-RESEARCH-I01`: Research Isolation Rules — `RESEARCH_ONLY`.
- `CKS-BOUNDARY-K01`: shared-kernel proposal must be evaluated as boundary contract, not third SSoT — `ACTIVE HYPOTHESIS / F4 BLOCKED`.

No canonical ABC×XYZ or Genome-value assignment is finalized here.

## 10. Stage 1D completion state

Stage 1D is **COMPLETE for bounded scope #21–#27**, rechecked against fresh CKS `main` `db5d0e5f...`.

Next bounded part: **Stage 1E — ADR namespace + Canon/SSoT authority map only**, beginning with another fresh HEAD check and regression of Stage 1C/1D.

Genome/Kernel synthesis remains BLOCKED by #233 F0–F3.