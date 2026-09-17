# KAT9I Archaeology — Stage 2A PRs #70–#76 — 2026-09-17

Status: **DATA ONLY / NON-CANONICAL / DISCONNECT-SAFE CHECKPOINT**  
Governing work item: `KAT9I_OS #233`  
Implementation Worker: ChatGPT  
Independent QA: Antigravity (AGY)

## 0. Scope and SSoT preflight

This bounded pass reviews only merged KAT9I_OS PRs `#70`–`#76` against current KAT9I `main`.

Fresh KAT9I main anchor: `4f01aa530584f591ffbc1146fd2af09a92389cc2`.

Authority rule for this pass:

`current main Canon/contracts > merged historical PR text > forensic interpretation`.

The purpose is to distinguish:

- concepts that remain current accepted architecture;
- implementation/prototype details that must not be mistaken for production runtime;
- historical QA/evidence lessons;
- candidates for the Lost-Ideas Registry.

Previous CKS Stage 1A–1F results are not used as authority for KAT9I; they are only cross-system context. Donor material is excluded.

---

## 1. PR #70 — machine contracts and schema SSoT

Historical change:

- selected JSON Schema Draft 2020-12 as canonical cross-language contract format;
- created `schemas/v1/` as physical schema SSoT;
- introduced fail-closed `additionalProperties: false`;
- introduced version incompatibility semantics;
- seeded Task/Evidence/Security/Capability/SystemEvent contracts.

Current-main verification:

- current architecture register still marks ADR-034 as `ACCEPTED`;
- current register still names `schemas/v1/` as the physical schema SSoT;
- current `schemas/v1/` directory exists and contains the evolved contract family.

Forensic classification:

`ABSORBED / CURRENT CANON FOUNDATION`.

This is not a lost idea. It is one of the strongest surviving KAT9I invariants:

`one machine-contract SSoT + explicit versioning + fail-closed validation`.

---

## 2. PR #71 — machine Module Registry and dependency graph

Historical change:

- formalized `ModuleRegistry.json`;
- created physical `modules_registry.json`;
- required canonical-owner references instead of copied architecture prose;
- added DAG/cycle detection, dependency validation and contract-coverage checks;
- enforced unique canonical responsibility.

Current-main verification:

- ADR-035 remains `ACCEPTED`;
- `modules_registry.json` remains the accepted physical registry;
- architecture register still requires unique responsibility and DAG dependencies;
- canonical responsibility points to `docs/architecture/27_MODULE_REGISTRY_AND_RESPONSIBILITY_MAP.md` rather than making the registry a competing architecture SSoT.

Forensic classification:

`ABSORBED / CURRENT CANON FOUNDATION`.

Important SSOT implication:

`machine registry = executable index/validator of ownership, not a second owner of architectural meaning`.

---

## 3. PR #72 — external QA remediation and Evidence honesty

Historical change:

- repaired an incorrect mapping between OQ-004 and Worker-isolation work;
- restored OQ-004 to the Electron↔Core IPC question;
- corrected deferred-status semantics;
- removed an overclaim that substring tests proved browser/navigation behavior;
- explicitly downgraded that evidence to structural evidence.

Current-main relation:

The exact text is historical, but the semantic lesson is now covered by stronger current principles:

- ADR-004 `Evidence-first`;
- independent QA model;
- later exact-revision / ChangeSet / Integration Evidence rules;
- no assertion from a Worker or CI label is sufficient without evidence appropriate to the claimed behavior.

Forensic classification:

`ABSORBED AS EVIDENCE-METHOD INVARIANT / HISTORICAL QA EVIDENCE`.

Important correction for our current archaeology:

`test existed / test passed / claimed behavior was actually exercised` are separate facts.

This directly reinforces the CKS Stage 1A false-green CI correction and must be applied to old KAT9I PRs as well.

Lost-idea status:

No standalone missing subsystem found here. The valuable content is methodology and provenance discipline.

---

## 4. PR #73 — Identity / Role / Trust / Capability / Human Approval

Historical change:

- separated Identity, Role, Trust Level and Capability Grant;
- introduced `Identity.json` and `ApprovalRecord.json`;
- bound local Windows identity without storing passwords;
- bound Human Approval to `task_id` + `action_hash` + nonce + expiration;
- prohibited Worker-generated Human Approval.

Current-main verification:

- ADR-036 remains `ACCEPTED`;
- current architecture register still cites `Identity.json`, `ApprovalRecord.json` and Security as canonical owners;
- current `schemas/v1/` still contains `ApprovalRecord.json` and `CapabilityGrant.json`;
- Worker still cannot be treated as the source of Human Approval.

Forensic classification:

`ABSORBED / CURRENT CANON FOUNDATION`.

Potential Genome-level invariant candidate, still not promoted here:

`Identity != Role != Capability != Approval authority`.

This is especially relevant later when comparing CKS Owner/Authority/Agent/Reviewer separation, but the two lifecycle models must not be collapsed automatically.

---

## 5. PR #74 — Event Journal / Checkpoint / Replay Recovery

Historical change:

- append-only JournalEvent contract;
- Checkpoint contract;
- `operation_id` idempotency;
- `lease_generation` fencing;
- replay/recovery semantics;
- retention/compaction rules.

Current-main verification:

- ADR-037 remains `ACCEPTED`;
- `JournalEvent.json` and `Checkpoint.json` remain current canonical contracts;
- current architecture still requires replay from last confirmed Checkpoint plus subsequent events;
- duplicate side effects are blocked through operation identity;
- stale Worker generations are rejected through fencing.

Forensic classification:

`ABSORBED / CURRENT CANON FOUNDATION`.

This is a major surviving KAT9I invariant family:

`durable event history + checkpoint + idempotency + fencing + replay recovery`.

No evidence in this pass that this idea was lost.

---

## 6. PR #75 — separate Core process and Electron IPC

Historical architectural decision:

- Core is physically separate from Electron;
- UI failure must not destroy active task state;
- narrow typed IPC boundary;
- reconnect/state resynchronization;
- shell/eval not exposed through Renderer.

Current-main verification:

- ADR-038 remains `ACCEPTED`;
- OQ-002 and OQ-004 remain accepted;
- current `CoreIpcMessage.json` remains in `schemas/v1/`;
- current architecture still describes a physically separate Rust Core Runtime and restricted IPC.

### Critical forensic correction

The historical PR title says `Prototype Rust Core Runtime`, but the implementation artifact that remains in current main is:

`scripts/core_ipc_prototype.py`.

That file is a **Python prototype** modelling the intended Rust-Core boundary. Therefore historical evidence supports:

- architecture/boundary semantics;
- IPC behavior prototype;
- reconnect/isolation tests;

but **does not prove that a production Rust Core Runtime existed in PR #75**.

Correct evidence statement:

`Rust Core architecture ACCEPTED; Python boundary prototype implemented and tested`.

Incorrect overclaim to avoid:

`PR #75 implemented the production Rust Core`.

Forensic classification:

- boundary architecture: `ABSORBED / CURRENT CANON FOUNDATION`;
- Python prototype: `HISTORICAL/REFERENCE IMPLEMENTATION`, not Core Genome itself.

This is an important candidate for the global lost-ideas/runtime-gap registry: later F0 must determine when/where the intended Rust runtime moved from prototype semantics to executable production implementation, or whether that migration remains incomplete.

Seed:

`KAT9I-GAP-RUNTIME-001`: trace `accepted Rust Core boundary → Python prototype → actual Rust runtime implementation status`.

---

## 7. PR #76 — Windows Secret Store / SecretRef

Historical architectural decision:

- secret values remain outside TaskContract/Knowledge/logs/cache;
- ordinary contracts carry only `SecretRef`;
- Windows DPAPI selected for first Windows implementation;
- secret access requires scoped capability;
- revocation/check-exists semantics.

Current-main verification:

- ADR-039 remains `ACCEPTED`;
- `SecretRef.json` remains canonical;
- current architecture still states that secrets are stored separately and normal system objects carry references;
- `scripts/windows_secret_store.py` remains present as a Windows DPAPI prototype.

### Architecture vs implementation correction

The stable invariant is not “DPAPI must exist forever”. Current architecture already distinguishes architectural responsibility from replaceable implementation choices elsewhere.

The stronger invariant is:

`secret value is outside ordinary contracts/state + access is capability-scoped + reference is non-secret + revocation is explicit`.

DPAPI is the accepted first Windows implementation.

Forensic classification:

- SecretRef boundary/security semantics: `ABSORBED / CURRENT CANON FOUNDATION`;
- DPAPI implementation: `ACCEPTED FIRST IMPLEMENTATION / PLATFORM-SPECIFIC`;
- Python secret-store artifact: `REFERENCE/PROTOTYPE IMPLEMENTATION` unless later runtime evidence proves production ownership.

Seed:

`KAT9I-GAP-RUNTIME-002`: trace prototype Secret Store ownership into the actual runtime/module implementation and verify that current production path does not depend on the Python prototype being mistaken for Core runtime.

---

## 8. Cross-PR architecture line recovered

PRs #70–#76 form a coherent early machine-contract/runtime-foundation sequence:

1. contracts get one physical SSoT;
2. modules get one machine-readable ownership/dependency registry;
3. Evidence claims are corrected when proof is weaker than wording;
4. identity/capability/human authority are separated;
5. state-changing execution gets journal/checkpoint/idempotency/fencing semantics;
6. UI is physically separated from Core through a narrow IPC contract;
7. secret values are removed from normal object flow and exposed only through scoped reference-based access.

This sequence looks much more like the early KAT9I kernel than a collection of independent features.

However this checkpoint does **not** promote that observation into `KAT9I_ARCHITECTURE_GENOME.md`; global F0/F1 is incomplete.

---

## 9. Regression against previous forensic work

Previous conclusion `CORE_KERNEL_CONTRACT should be a boundary/meta-invariant contract candidate, not a third authority system` still holds.

Stage 2A strengthens it:

- KAT9I already has its own mature execution-side invariants;
- several are explicitly machine-enforced and have current canonical owners;
- moving them into a new shared Core document as copied definitions would create SSoT duplication.

Therefore any future cross-system contract should reference/align semantics such as Evidence, revision binding, ownership class or replay/idempotency without stealing ownership from KAT9I's current contracts.

Correction added by this stage:

- earlier summaries sometimes spoke as though PR #75 created a Rust runtime. Exact repository evidence shows a Python prototype modelling the intended Rust boundary. This is now corrected.

---

## 10. Lost-ideas / gap seeds from Stage 2A

Carry forward without classification/promotion:

- `KAT9I-GAP-RUNTIME-001`: prove the lineage from PR #75 Python Core IPC prototype to actual Rust Core runtime implementation;
- `KAT9I-GAP-RUNTIME-002`: prove the lineage from PR #76 Python Secret Store prototype to current runtime/module ownership;
- `KAT9I-METHOD-EVIDENCE-001`: preserve semantic-strength distinction for historical CI/tests (`exists / ran / meaningful assertion / feature exercised`);
- `KAT9I-INVARIANT-CANDIDATE-001`: one physical machine-contract SSoT;
- `KAT9I-INVARIANT-CANDIDATE-002`: machine registry references canonical ownership rather than duplicating it;
- `KAT9I-INVARIANT-CANDIDATE-003`: identity/capability/approval authority separation;
- `KAT9I-INVARIANT-CANDIDATE-004`: journal/checkpoint/idempotency/fencing/replay family;
- `KAT9I-INVARIANT-CANDIDATE-005`: UI/runtime physical separation with narrow typed IPC;
- `KAT9I-INVARIANT-CANDIDATE-006`: secrets-by-reference and capability-scoped access.

All remain forensic registry seeds. No ABC×XYZ or Genome-value bucket is assigned yet.

---

## 11. Stage 2A completion

Stage 2A is COMPLETE for PRs #70–#76.

Current KAT9I main remained anchored at `4f01aa530584f591ffbc1146fd2af09a92389cc2` throughout this bounded pass.

Next bounded KAT9I history part should continue from the next historical PR cluster, beginning again with:

`fresh KAT9I HEAD → regression of Stage 2A conclusions → historical PR evidence → current-main absorption check → GitHub checkpoint`.

Genome/Core synthesis remains BLOCKED until global F0/F1/F2/F3 completeness.