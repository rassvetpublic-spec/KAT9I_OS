# CKS Archaeology — Stage 1B Council PR #3 — 2026-09-17

Status: **DATA ONLY / NON-CANONICAL / DISCONNECT-SAFE CHECKPOINT**  
Governing work item: `KAT9I_OS #233`  
Implementation Worker: ChatGPT  
Independent QA: Antigravity (AGY)

## 0. Scope and SSoT preflight

This bounded pass reviews **CKS PR #3 (`feat: CKS Council v0.1`) only**.

Fresh CKS main anchor: `e9e8c74e7372944fe985033de20fff89258c8ab4`.

PR #3 remains OPEN and therefore its branch is Evidence / Proposal, not Canon. No Council artifact is promoted merely because it is internally coherent or has passing branch CI.

Current-main authority references used in this pass:

- `control/automation-governance.yaml`;
- `config/lifecycle.yaml`;
- `schemas/decision_record_v1.yaml`;
- `schemas/promotion_request_v1.yaml`;
- current CKS repository state and Stage 1A findings.

Previous Stage 1A regression guards remain active:

- green CI alone is not proof of semantic implementation;
- #29 architecture SSoT pointer gap remains unresolved;
- #30 unprotected `main` remains unresolved;
- fresh main wins over historical branch proposals.

## 1. PR #3 factual status

PR #3 proposes a Council v0.1 governance/orchestration layer around:

`Proposal → Review → Decision → Human Gate → Implementation → Archive`.

Its branch includes, among other things:

- Council workflow/FSM;
- proposal/review/decision records;
- requirement for multiple review branches and a disagreement branch;
- human authorization gate;
- bounded cycle count;
- Bridge design for external execution;
- archive/decision-memory concepts;
- validators, tests and CI.

The recorded technical review said `READY_FOR_HUMAN_GATE`, explicitly did **not** approve adoption, and left two recommendations: verify `base_reference` against actual merge-base and add a full lifecycle integration test.

Therefore the correct forensic status is:

`HIGH-VALUE OPEN PROPOSAL / NOT CANON`.

## 2. Concept absorption matrix

Classification meanings:

- `ABSORBED` — the semantic principle exists on current main independently of PR #3.
- `PARTIALLY_ABSORBED` — main contains the principle, but not the full Council semantics/contract.
- `UNIQUE_OPEN` — meaningful PR #3 concept not verified as current-main Canon.
- `SUPERSEDED` — later main model makes the exact PR #3 mechanism unnecessary or obsolete.
- `EXTERNAL_EXECUTION_DETAIL` — useful boundary design, but not a CKS knowledge-core responsibility.

| Council concept | Current-main evidence | Classification | Forensic result |
|---|---|---|---|
| Automation/Proposal is not Decision | `automation_is_not_decision: true`; `decision_record_v1` is a distinct object | ABSORBED | Keep as CKS invariant, provenance is no longer PR #3 alone |
| Automation cannot change Canon | `automation_is_not_canon_change: true`; promotion to Canon requires evidence + decision reference | ABSORBED | Strong current-main invariant |
| Evidence before acceptance/promotion | lifecycle requires evidence before acceptance; promotion requires evidence | ABSORBED | Strong current-main invariant |
| Separate Decision object with rationale/options/evidence refs | `decision_record_v1.yaml` | ABSORBED | Council does not own this concept anymore |
| Human final authority for every Council approval | main requires review, but the inspected current schemas do not encode a universal human-authority identity/gate for all decisions | PARTIALLY_ABSORBED | Do not claim universal Human Gate from current main without separate authority Evidence |
| At least two reviews | no equivalent requirement verified in inspected main contracts | UNIQUE_OPEN | Candidate governance policy, not invariant yet |
| Mandatory disagree branch before approval | no equivalent requirement verified in inspected main contracts | UNIQUE_OPEN | Valuable anti-groupthink experiment; not Canon |
| Fixed anti-loop `cycle_limit: 3` | no exact main rule verified | UNIQUE_OPEN | Treat as implementation policy/experiment, not Core invariant |
| Preserve rejected/failure context | `preserve_rejected_context: true`; Graveyard schemas exist | ABSORBED | General principle survives without Council |
| “Learn decisions, not raw discussion” | Decision/evidence schemas exist, but no inspected main contract proves the exact exclusion rule for raw discussion | PARTIALLY_ABSORBED | Retain wording as hypothesis until knowledge-ingest policy proves it |
| Proposal/Review/Decision Council as a dedicated CKS orchestration subsystem | no current-main Council subsystem verified | UNIQUE_OPEN | Must compete against simpler current governance, not be assumed missing functionality |
| Council self-use | PR itself separates it from v0.1 scope | UNIQUE_OPEN / DEFERRED-IN-PR | Not evidence of current architecture |
| External Bridge: Council does not mutate target repo | consistent with CKS independence, but implementation belongs to integration/execution boundary | EXTERNAL_EXECUTION_DETAIL | Evaluate later against KAT9I boundary contract |
| Bridge one-writer rule | execution-boundary concern; not current CKS knowledge-core ownership | EXTERNAL_EXECUTION_DETAIL | Candidate shared boundary invariant only after KAT9I comparison |
| Bridge idempotency via job/payload hash | execution transport concern | EXTERNAL_EXECUTION_DETAIL | Preserve for later cross-system contract comparison |
| Revision/base-reference verification | technical review explicitly says automatic merge-base check is still missing | UNIQUE_OPEN GAP | Strong candidate for revision-binding checklist; not implemented by PR #3 as reviewed |
| Full Proposal→Review→Validation→Decision→Human Gate integration test | technical review explicitly requests it | UNIQUE_OPEN GAP | PR #3 CI cannot be treated as full lifecycle proof |

## 3. Corrections to previous reasoning

### Correction 1 — Council is not the missing CKS decision engine

Earlier reasoning risked treating Council as the natural future Decision layer. Current main already contains explicit Decision, Evidence, lifecycle and promotion contracts.

Corrected view:

> Council is a **candidate governance/orchestration policy on top of existing CKS primitives**, not proof that CKS lacks decision/evidence primitives.

### Correction 2 — “Human Gate is already CKS Canon” was too strong

PR #3 mandates a Human Gate, and its review respects it. Current main inspected in this pass proves `approval_requires_review`, but does not by itself prove the same universal Human Gate semantics for every Decision/Canon transition.

Status changed to `PARTIALLY_ABSORBED / NEEDS AUTHORITY-MAP REVIEW`.

### Correction 3 — two-review + disagree-branch is not a shared CORE invariant yet

It is an interesting anti-groupthink mechanism, but hard-coding it into `CORE_KERNEL_CONTRACT_v1` now would import an **unmerged policy choice** from PR #3.

The more defensible cross-system invariant remains weaker:

`Proposal ≠ Decision; significant promotion requires independent challenge/review appropriate to risk.`

Exact reviewer count and mandatory disagreement remain policy-level candidates.

### Correction 4 — Council Bridge is mostly not CKS Core

One-writer, external mutation, idempotency, revision checks and retry/failure transport are valuable, but most belong to the boundary between knowledge/governance and execution systems.

They must later be compared with KAT9I's existing execution/evidence/promotion contracts before any shared contract is written.

## 4. Weak points found in current main while checking PR #3

### CKS-WEAK-007 — Review requirement is stronger than the visible Decision schema

Current governance says `approval_requires_review: true`, but `decision_record_v1.yaml` contains context/options/rationale/evidence/status and no explicit fields for:

- reviewer identity;
- review references;
- authority identity;
- approval timestamp/signature;
- disagreement/challenge evidence.

This does not prove a defect by itself; those records may intentionally live elsewhere. But it creates a **traceability question** for Stage 1E authority-map work: where exactly is review/authority evidence bound to an accepted/canon Decision?

### CKS-WEAK-008 — Generic lifecycle and knowledge/decision lifecycles may be conflated

`config/lifecycle.yaml` defines `BACKLOG → ANALYSIS → DESIGN → IMPLEMENTATION → QA → ACCEPTED → COMPLETED`, which looks like a project/change lifecycle rather than the full modern Knowledge Runtime lifecycle.

Until ownership is reconciled, this file must not be assumed to be the authoritative knowledge-state machine merely because it is named `lifecycle.yaml`.

This strengthens the need for Stage 1E SSoT/authority reconciliation.

## 5. SSOT implications

PR #3 is useful precisely because several of its ideas later appear independently in current-main contracts. But provenance must be recorded correctly:

- current-main Canon/control wins for present behavior;
- PR #3 remains historical Evidence for evolution and alternative policy design;
- absorbed concepts should point to their current owner, not continue to cite PR #3 as operational authority;
- unique concepts remain candidates only;
- Bridge details must not silently move CKS into KAT9I execution ownership.

No new SSoT is created by this checkpoint.

## 6. Lost-ideas seed from PR #3

Candidates to carry into Stage 1F lost-ideas consolidation:

- `CKS-LOST-C01`: mandatory disagree/challenge branch before high-impact approval — `UNIQUE_OPEN`;
- `CKS-LOST-C02`: explicit multi-review threshold — `UNIQUE_OPEN`;
- `CKS-LOST-C03`: bounded review loop policy — `UNIQUE_OPEN`, exact value not invariant;
- `CKS-LOST-C04`: decision-memory-first learning vs raw-discussion learning — `PARTIALLY_ABSORBED`;
- `CKS-LOST-C05`: revision/merge-base verification at governance boundary — `OPEN GAP`;
- `CKS-LOST-C06`: end-to-end lifecycle integration test — `OPEN GAP`;
- `CKS-BOUNDARY-C01`: one-writer external execution bridge — `EXTERNAL_EXECUTION_DETAIL`;
- `CKS-BOUNDARY-C02`: idempotent hashed external job/evidence transport — `EXTERNAL_EXECUTION_DETAIL`.

These are registry seeds only. No ABC×XYZ or Genome-value class is assigned yet.

## 7. Stage 1B completion condition

Stage 1B is COMPLETE for the bounded question: **what unique Council semantics remain after comparison with current CKS main?**

It is not a verdict on whether PR #3 should merge.

Next bounded part: **Stage 1C — Issues #5/#8/#9/#14 only**, beginning again with fresh CKS HEAD and regression of Stage 1A + 1B conclusions.

Genome/Kernel synthesis remains BLOCKED until the later completeness gate.