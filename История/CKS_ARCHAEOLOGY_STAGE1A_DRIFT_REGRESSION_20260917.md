# CKS Archaeology — Stage 1A Drift Regression — 2026-09-17

Status: **DATA ONLY / NON-CANONICAL / DISCONNECT-SAFE CHECKPOINT**  
Governing work item: `KAT9I_OS #233`  
Implementation Worker: ChatGPT  
Independent QA: Antigravity (AGY)

## 0. Scope

Этот проход намеренно уменьшен примерно вдвое относительно предыдущего рабочего окна.

Проверяется только:

1. drift CKS после предыдущего Stage 1 checkpoint;
2. регрессия прежних выводов относительно свежего HEAD;
3. состояние SSoT/Governance GAP #29/#30;
4. содержательность новых post-snapshot проверок E1/E2.

PR #3 Council и absorption matrix research tracks в этот подэтап **не входят**. Они остаются следующими отдельными частями Stage 1.

## 1. Fresh SSoT preflight

На момент этого checkpoint:

- KAT9I forensic branch anchor before this commit: `ddb11650672e9fb4ce014cf34ce9e02b68e8bab0`;
- previous CKS Stage 1 anchor: `acc429ca6497b45810e0285220e0a9a8adf4e709`;
- fresh CKS `main`: `e9e8c74e7372944fe985033de20fff89258c8ab4`;
- CKS `main` remains `protected=false`;
- `control/system-state.yaml` still declares `current_version: CKS_v1.5`, baseline `v1.2`, operational `v1.3`, runtime `v1.4`, development `v1.5`, `core: frozen`, `runtime: evolving`.

Rule: previous checkpoint is historical DATA. Fresh HEAD wins for current-state claims.

## 2. Drift since previous Stage 1 anchor

`acc429ca... → e9e8c74e...` = **13 commits ahead**, 0 behind.

Changed scope is concentrated in post-snapshot integrity and compatibility validation:

- compatibility audit;
- v1.6 intelligence compatibility runtime;
- v1.7 graph validation/orphan detection;
- Self Audit;
- Knowledge health/conflict diagnostics;
- CI workflows;
- new Stage E1 report;
- new Stage E2 regression tests.

This means previous Stage 1 statements about runtime completeness must be re-read through E1/E2 before reuse.

## 3. Previous-result regression review

| Previous result | Fresh verification | Status now |
|---|---|---|
| `CKS main is unprotected` | Fresh branch metadata still says `protected=false` | CONFIRMED |
| `#30 governance gap remains real` | #30 is still OPEN and current branch metadata matches its Evidence | CONFIRMED |
| `architecture SSOT pointer is stale/broken` | `control/ssot-registry.yaml` still points `architecture.path: architecture/`; fresh tree still has no top-level `architecture/` | CONFIRMED |
| `Self Audit does not validate architecture pointer existence` | Current `check_ssot_registry()` validates markers plus `tools/`, `engine/`, `obsidian/`, but still has no physical check for `architecture/` | CONFIRMED |
| `#29 remains unresolved` | #29 still OPEN; source map still says concrete Canon paths require clarification | CONFIRMED |
| `full snapshot CI proves every historical compatibility workflow is substantive` | Stage E1 found a real false-green v1.6 workflow | REJECTED / OVERCLAIM |
| `main Knowledge Runtime / Intelligence passed integrated regression` | Stage E1 explicitly preserves this narrower conclusion | CONFIRMED WITH NARROWER SCOPE |
| `historical compatibility facades are not yet covered by Self Audit` | Current Self Audit now calls `run_compatibility_audit()` and fails on compatibility integrity/execution | SUPERSEDED |
| `v1.7 helper layers may still be shallow` | Stage E2 adds executable checks for validator, orphan detector and relation facade | PARTIALLY CLOSED; deeper semantic audit still pending |
| `successful CI = Canon` | E1 restates the opposite: CI success is Evidence only, not Canon | CONFIRMED INVARIANT |

## 4. Important correction: false-green CI was real

Stage E1 documents a concrete defect in historical CKS v1.6 compatibility validation:

- workflow launched a script that previously did not substantively validate the advertised layer;
- conflict detector returned an empty result unconditionally;
- knowledge health score returned `0` unconditionally;
- therefore CI could be green without real functional verification.

The defect was repaired by turning historical v1.6 into a compatibility facade over the current runtime and adding executable tests/self-checks.

Architectural consequence for our forensic method:

> `workflow success` alone is not enough Evidence for `feature really worked`.

For historical KAT9I/CKS archaeology, every important old CI claim must distinguish:

- process executed;
- assertions were meaningful;
- advertised function was actually exercised.

This correction applies retroactively to F0 history review.

## 5. Stage E2: what improved

Fresh `tests/test_cks_post_snapshot_integrity_stage_e2.py` now explicitly checks:

- compatibility audit contains at least 14 passing checks;
- v1.7 graph validator distinguishes valid graph, broken reference and invalid relation;
- detailed v1.7 report is backed by current runtime;
- orphan detection does not treat a broken edge as valid connectivity;
- relation engine remains a real graph facade;
- repository Self Audit executes compatibility-layer validation.

Fresh Self Audit schema is `1.3` and now includes `check_compatibility_layers()`.

This closes one weakness from the previous checkpoint: Self Audit is no longer limited to the primary Runtime path.

It does **not** close #29 because architecture pointer existence is still unchecked.

## 6. Fresh CI evidence

At fresh CKS HEAD `e9e8c74e...` GitHub Actions reports multiple push workflows. At minimum the returned current-head runs include successful:

- `CKS Preflight` run `35164758211`;
- `CKS Validation` run `35164758327`.

The head commit itself is `ci(audit): include post-snapshot compatibility integrity stage E2`.

Interpretation is deliberately narrow:

`current-head workflows succeeded` = current regression Evidence.

It does **not** imply every historical implementation was always correct, nor does it promote audit reports into Canon.

## 7. SSoT review

Current authority problem remains unresolved:

- registry says architecture owner path is `architecture/`;
- path does not exist at repository root;
- real architecture material is distributed across `ARCHITECTURE.md`, `docs/ARCHITECTURE.md`, `docs/architecture/` and ADR/Decision namespaces;
- `docs/architecture/CKS_CANON_SOURCE_MAP_v1.md` explicitly says exact Canon paths still require clarification.

Therefore no forensic checkpoint may select one of those paths as authoritative by inference.

Until #29 gets a Decision, authority resolution remains manual and Evidence-driven.

## 8. New weak point discovered

### CKS-WEAK-006 — CI semantic strength must be an audited property

CKS E1 proved that a workflow can be technically green while semantically empty or weak.

This is broader than the repaired v1.6 defect. For architecture archaeology the relevant field becomes:

`CI_EXISTED / CI_RAN / ASSERTIONS_MEANINGFUL / FEATURE_EXERCISED`.

Without those four distinctions, old CI is insufficient proof that an architectural idea was actually implemented.

This rule must also be applied to KAT9I historical PR/commit review later in F0.

## 9. Stage status after this bounded pass

### Completed in Stage 1A

- fresh HEAD re-anchor;
- 13-commit drift review;
- recheck #29/#30;
- recheck SSoT registry and Source Map;
- recheck current Self Audit implementation;
- E1 false-green analysis;
- E2 compatibility/self-audit regression analysis;
- correction of previous overclaim about historical CI strength.

### Explicitly not attempted in this part

- PR #3 Council archaeology;
- Issues #5/#8/#9/#14 semantic absorption;
- Issues #21–#27 research-track absorption;
- final ADR namespace authority map;
- final CKS lost-ideas classification.

## 10. Next disconnect-safe parts

Stage 1 is now split further:

- **Stage 1B:** PR #3 Council only — identify unique vs absorbed vs obsolete concepts.
- **Stage 1C:** early research tracks #5/#8/#9/#14 only.
- **Stage 1D:** research tracks #21–#27 only.
- **Stage 1E:** ADR namespace + Canon authority/source-map reconciliation.
- **Stage 1F:** CKS lost-ideas consolidation and POST-CHECKPOINT.

Every part begins with fresh HEAD + regression of conclusions from all earlier Stage 1 parts.

No Genome/Kernel synthesis is allowed before the later F3 completeness gate.