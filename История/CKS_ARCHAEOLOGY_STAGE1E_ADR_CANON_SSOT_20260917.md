# CKS Archaeology — Stage 1E ADR namespace + Canon/SSoT authority map — 2026-09-17

Status: **DATA ONLY / NON-CANONICAL / DISCONNECT-SAFE CHECKPOINT**  
Governing work item: `KAT9I_OS #233`  
Implementation Worker: ChatGPT  
Independent QA: Antigravity (AGY)

## 0. Fresh-head regression

Fresh CKS `main` at Stage 1E start:

`db5d0e5fb521f2747a2fadc8c077f2b17851239f`

No drift from corrected Stage 1C/1D anchor was observed at start of this substage.

## 1. ADR namespace collision found

The current `decisions/` directory contains:

- `decisions/ADR-0001-multi-worker-distillate.md` — accepted Multi-Worker Distillate;
- `decisions/ADR-0002-knowledge-centric-runtime.md` — accepted Knowledge Runtime / Knowledge Intelligence split;
- `decisions/ARCHITECTURE_DECISION_RECORD.md` — document whose internal heading also declares `ADR-0001: CKS as independent knowledge system` with status ACCEPTED.

Therefore CKS currently has **two different accepted concepts claiming ADR-0001 identity**.

This is not merely naming noise: `CKS_CANON_SOURCE_MAP_v1.md` explicitly places ADR at the top of the trust order. Duplicate ADR identity makes exact provenance ambiguous for both humans and agents.

Forensic classification:

`CKS-GAP-ADR01 = ACCEPTED ADR IDENTITY COLLISION / AUTHORITY AMBIGUITY`

No renumbering is performed in this forensic pass. Resolving it requires normal CKS decision/change procedure and preservation of historical aliases.

## 2. Decision authority map

Current evidence supports this hierarchy of *types*, but not yet a complete path-level map:

1. accepted ADR / accepted Decision;
2. Evidence supporting that Decision;
3. current rules/schemas implementing the accepted decision;
4. derived views/analytics below authority level.

`decisions/README.md` defines the Decision layer as accepted decisions with context, alternatives, rationale, evidence and lifecycle status.

`control/automation-governance.yaml` reinforces:

- automation is not Decision;
- automation is not Canon change;
- approval requires review.

`control/system-state.yaml` reinforces:

- Core frozen;
- runtime evolving;
- experiments isolated;
- Proposal is not Decision;
- Experiment is not Canon.

These are strong authority-separation invariants.

## 3. SSoT registry drift remains real

`control/ssot-registry.yaml` declares:

`architecture.path: architecture/`

but Issue #29 records that root `architecture/` does not exist and current architectural materials live elsewhere, including `/ARCHITECTURE.md`, `/docs/ARCHITECTURE.md`, and `/docs/architecture/`.

`docs/architecture/CKS_CANON_SOURCE_MAP_v1.md` still says concrete canonical paths need further clarification.

Therefore there is no defensible basis yet for claiming a single fully resolved path-level architecture SSoT.

Forensic status:

`CKS-GAP-SSOT01 = ARCHITECTURE POINTER DRIFT / PATH AUTHORITY UNRESOLVED`

## 4. Current safe authority rules

Until #29 and the ADR collision are resolved, the safe interpretation is:

- accepted Decision semantics outrank proposal/research text;
- current implementation must be tied back to Decision/Evidence where possible;
- historical/bootstrap/audit documents are context/evidence, not automatic Canon;
- analytics, graph, Obsidian views and automation do not gain Decision/Canon authority;
- CKS and KAT9I remain separate authority domains;
- no third shared SSoT is created by the future CORE contract hypothesis.

## 5. Stage 1B/1C/1D regression impact

### Stage 1B
Holds, but this Stage 1E strengthens its authority-traceability concern: review is required, yet the visible Decision layer and duplicate ADR namespace show that identity/authority binding needs explicit reconciliation.

### Stage 1C
Holds. Graveyard/Distillation remain partially implemented/integration gaps. Stage 1E adds that any future promotion must cite an unambiguous Decision identity and valid SSoT path.

### Stage 1D
Holds. The Ownership Model research candidate is strengthened by concrete ADR/SSoT identity ambiguity; however, the exact Owner/Authority/Agent/Reviewer model remains unapproved.

## 6. Lost-ideas / gap seeds

- `CKS-GAP-ADR01`: duplicate accepted `ADR-0001` identity — `P0 TRACEABILITY GAP CANDIDATE`.
- `CKS-GAP-ADR02`: migration/alias strategy for historical ADR identifiers — `NEEDS DECISION`.
- `CKS-GAP-SSOT01`: stale `architecture.path` in SSoT registry — `OPEN #29`.
- `CKS-GAP-SSOT02`: path-level Canon source map incomplete — `OPEN TRACEABILITY GAP`.
- `CKS-GAP-AUTH01`: accepted Decision should be bindable to review/authority evidence without ambiguity — `SUPPORTED GAP CANDIDATE`.
- `CKS-BOUNDARY-A01`: cross-project shared contract must reference each project's authoritative Decisions, not become a new third Canon — `ACTIVE BOUNDARY INVARIANT CANDIDATE`.

No canonical ABC×XYZ or Genome-value assignment is finalized here.

## 7. Stage 1E completion state

Stage 1E is **COMPLETE for the bounded question: ADR identity + Canon/SSoT authority map**.

Major new finding: accepted ADR namespace collision exists on current `main`.

Next bounded part: **Stage 1F — consolidate CKS lost-ideas/gap registry from 1A–1E, deduplicate, mark absorbed/superseded/open, and run POST-CHECKPOINT regression**.

Genome/Kernel synthesis remains BLOCKED by #233 F0–F3.