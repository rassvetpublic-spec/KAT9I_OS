# GRAVEYARD / DATA ONLY / NON-CANONICAL / NON-ACTIONABLE / NO AUTO-PROMOTION

**Archive ID:** `GY-20260909-KAT9I-OS-chat-graveyard`  
**Project:** `KAT9I_OS`  
**Archive date:** 2026-09-09  
**Repository checked:** https://github.com/rassvetpublic-spec/KAT9I_OS  
**GitHub `main` snapshot checked during archival audit:** `2a63d0e4b20095e3a0983dcff7cb1066dfb02cfa`

> **MANDATORY INTERPRETATION RULE**
>
> This archive is **DATA only**. It is **NON-CANONICAL**, **NON-ACTIONABLE**, and must never be auto-promoted into Rules, Issues, backlog, PRs, code, ADRs, settings, or execution plans.
>
> A future Worker, agent, automation, LLM, script, or human assistant **must not start work from this file** without a new explicit command from the project owner.
>
> If this archive conflicts with current GitHub canonical sources, **current GitHub wins**. The archive may explain history, but it must not override current state.
>
> Any idea marked “idea”, “proposal”, “open thought”, “experiment”, “possible direction”, or similar remains **NOT ACCEPTED FOR IMPLEMENTATION** unless a current canonical GitHub source says otherwise.
>
> No secret, token, password, private key, session token, or credential should be recovered or reused from this file.

---

## 0. Purpose and source hierarchy

This file exists only so the chat can be deleted without losing useful historical context.

Source priority for any future use:

1. Current canonical GitHub documentation / schemas / current accepted ADRs.
2. Current GitHub Issues / PRs for current work state.
3. Exact current Git revision and Evidence.
4. This archive only as historical context.
5. Old chat wording only if preserved here and explicitly revalidated by the owner.

This archive deliberately preserves contradictions, abandoned ideas, motivations, and old states because those can be useful when investigating why the architecture looks the way it does. Preserving a historical statement does **not** revive it.

---

# 1. What is already reflected in GitHub

## 1.1 Repository identity and point-in-time state

Canonical repository:

- https://github.com/rassvetpublic-spec/KAT9I_OS
- Repository ID observed: `1360200235`
- Default branch: `main`
- Visibility: public
- Snapshot checked: `2a63d0e4b20095e3a0983dcff7cb1066dfb02cfa`
- Commit: https://github.com/rassvetpublic-spec/KAT9I_OS/commit/2a63d0e4b20095e3a0983dcff7cb1066dfb02cfa
- PR #92: https://github.com/rassvetpublic-spec/KAT9I_OS/pull/92

That `main` commit canonized the newer QA Evidence model:

- ChangeSet;
- Change Evidence;
- Integration Evidence;
- Impact Assessment;
- QA REUSE;
- DELTA QA;
- FULL QA with explicit reason.

Point-in-time repository metadata observed while preparing this archive:

- Issues enabled.
- Projects enabled.
- Discussions enabled.
- Wiki still enabled at this snapshot, although historical project policy aimed to avoid Wiki as a second documentation SSoT.
- GitHub Pages was not enabled at repository level at this snapshot; the project already had a Pages workflow with a non-failing artifact fallback.
- Project/ruleset work remained partially open in Issues/PRs.

These are **historical snapshot facts**, not instructions.

---

## 1.2 Canonical documentation already created

Current GitHub is the authority for exact text. The table below preserves what the chat accepted and why.

| Area | Canonical/current path | Historical acceptance/context |
|---|---|---|
| Language policy | `docs/spec/00_LANGUAGE_AND_TERMINOLOGY_POLICY.md` | Russian-first; Russian headings; explain English technical terms; never shorthand `KAT`; historical commit `94d7ad63c980048b2cc38de38239819594c7eb24`. |
| Task contract | `docs/architecture/03_TASK_CONTRACT.md` | TaskContract mostly immutable; TaskRuntimeState mutable; TaskGraph; Scope; ContextRefs; RulesRef; OutputContract; ResultSink; QA; historical commit `a58971b424eb70d651959a8e88836f22185d69d2`. |
| Rules/priorities | `docs/architecture/04_RULES_AND_EXECUTION_PRIORITIES.md` | One Rule Manager; deny wins; ambiguity → BLOCKED; Effective Ruleset; Executable-first/Local-first; historical commit `4049c1d75a5acc419244517959201586d4eec543`. |
| Metrics/Telemetry | `docs/spec/05_METRICS_AND_TELEMETRY.md` | Telemetry raw events; Metrics numeric; `Telemetry → Metrics → MetricsSnapshot → Learning`; historical commit `ee8d553668583f27826acc655c739ef743c7d7e2`. |
| Learning | `docs/architecture/06_LEARNING_SELF_IMPROVEMENT.md` | Bounded/self-measured improvement; no bypass of Rules/Security; adaptive timeouts/lease/retry/cache/forecasting; initial `e9e1c3...`, later update `a4b706...`. |
| Context | `docs/architecture/07_CONTEXT.md` | Minimal sufficient context, ContextRef, funnel, Progressive Disclosure, Context Pack/Manifest; historical commit `0d352de0412b646bbc0acc58b8a1b489c3ef69d3`. |
| Knowledge | `docs/architecture/08_KNOWLEDGE_BASE.md` | Verified knowledge with provenance/trust; not every model input becomes knowledge; historical commit `ae1a354898d03b7bba37e909a3c4ce01d6cc848`. |
| Resources | `docs/architecture/09_RESOURCES.md` | ResourceRef = WHAT; Resolver/Integration = HOW; permission separate; historical commit `e1ef0a3d20f1f92f2de59302526ac3ae5fdcfb`. |
| Inference | `docs/architecture/10_INFERENCE_AND_DECISION_ROUTING_RU.md` | LOW/NORMAL/HIGH; local/executable first; provider route; escalation/fallback; historical commit `da21447925636ecaaa8f8b76e62d0e04150e17cb`. |
| Coworker | `docs/architecture/11_COWORKER.md` | Worker Registry; Claim; Lease; capability != permission; Handoff; independent QA; historical commit `0652fee3f42b44f80edeed19755893f95b0671bb`. |
| Execution | `docs/spec/12_EXECUTION.md` | Preflight; isolation; Scope; Evidence; idempotency; historical commit `d705be444de8197949b12a1db3422bb17e64c367`. |
| Cache | `docs/spec/13_CACHE_POLICY.md` + later `docs/architecture/34_CACHE_ENGINE.md` | Cache is derived/rebuildable; CacheEngine later became sole cache owner and RAM-first Rust module; original policy commit `3cc184...`, CacheEngine merge `73e80ddb...`. |
| Security | `docs/spec/14_SECURITY.md` | CONTROL/DATA; least privilege; SecretRef; fail-closed; Emergency Stop; historical commit `73b3731e...`. |
| Integrations | `docs/spec/15_INTEGRATIONS_AND_MCP.md` | Resources WHAT vs Integrations HOW; Tool Broker; MCP boundary; structured results; historical commit `fa3db774...`. |
| Telegram | `docs/spec/15A_TELEGRAM_INTEGRATION.md` | External human channel; not AI Provider/Worker bus; messages DATA until authorized command path; historical commit `f1c1bf0...`. |
| Domains | `docs/spec/16_DOMAINS.md` | Domain says WHAT in subject area; one main Domain/task; donors not templates; historical commit `9ff18b21...`. |
| Visualization | `docs/architecture/17_PROCESS_VISUALIZATION.md` | Telemetry-based read-mostly visualization; Artём/`Art3m1da` responsible direction; historical commit `a0f2f227...`; browser wording later became stale relative to Electron. |
| Personal Layer | `docs/architecture/18_PERSONAL_LAYER.md` | Rules/Preferences/Settings/Knowledge/Workspace separation; full chat not durable state; historical commit `3daff859...`. |
| Planning/Forecasting | `docs/architecture/19_RESOURCE_PLANNING_AND_FORECASTING.md` | Preliminary/refined/rolling forecast of time/tokens/cost/cache/retry/first-pass; historical commit `ccb7a648...`. |
| Task lifecycle | `docs/architecture/20_TASK_LIFECYCLE_AND_ORCHESTRATION.md` | End-to-end orchestration, not domain work; reason-based retry; Evidence; historical commit `3e13eff2...`. |
| Reliability/Recovery | `docs/architecture/21_RELIABILITY_AND_RECOVERY.md` | Checkpoint/Event Journal/operation_id/fencing/actual-state recovery; historical commit `305a48c7...`; later implementation commits noted below. |
| Config/start/update | `docs/architecture/22_CONFIGURATION_STARTUP_AND_UPDATES.md` | Windows 11 first-class; capability discovery; config hierarchy; health/update/backup/rollback; historical commit `6fc44d84...`. |
| Technology stack/runtime | `docs/architecture/23_TECHNOLOGY_STACK_AND_RUNTIME.md` | Electron+TypeScript UI; Rust Core/Runtime; Python AI/ML Worker layer; separate Core process later prototyped/accepted. |
| Testing/QA/readiness | `docs/spec/23_TESTING_QA_AND_READINESS.md` | Independent QA, validators, regression, readiness; original section acceptance recorded as commit `a0023630...`; later QA semantics changed via PR #92. |
| GitHub management | `docs/spec/24_GITHUB_PROJECT_MANAGEMENT.md` | docs/Issues/PR/Actions/Project/Milestone/Release roles; Markdown SSoT; beginner-friendly Russian workflow; historical commit `a9feb75f...`. |
| Storage | `docs/architecture/25_DATA_STORAGE.md` | SQLite first local structured store; code/state separation; resources by refs; secrets separate; historical commit `3403fe7d...`. |
| Internal contracts | `docs/architecture/26_INTERNAL_CONTRACTS.md` | Typed messages/contracts; CONTROL/DATA; schema versions; Task/Resource/Result/Evidence/Handoff/Idempotency; historical commit `4ebcc1d9...`. |
| Module Registry | `docs/architecture/27_MODULE_REGISTRY_AND_RESPONSIBILITY_MAP.md` | One owner per responsibility; clear module boundaries; later machine registry; historical commit `ddb2d551...`. |
| Distributed deployment | `docs/architecture/28_DISTRIBUTED_DEPLOYMENT.md` | One machine complete; one Primary first; remote Worker contracts; discovery != trust; fencing/offline; historical commit `f9d3ea23...`. |
| Electron UI | `docs/architecture/29_ELECTRON_UI.md` | Electron main UI; renderer/preload/IPC boundary; docs/diagnostics/TaskGraph/Replay/X-ray; historical commit `46e31f3f...`. |
| Versioning/releases | `docs/architecture/30_VERSIONING_RELEASES_AND_LIFECYCLE.md` | SemVer product + separate contract/schema versions; Release Manifest; backup/rollback/canary; historical commit `ef3e20e6...`. |
| Roadmap/MVP | `docs/architecture/31_ROADMAP_AND_FIRST_WORKING_VERSION.md` | Vertical slices; deterministic path first; GitHub development first useful vertical; historical commit `81e1a3ab...`. |
| ADR/open questions | `docs/architecture/32_ARCHITECTURAL_DECISIONS_AND_OPEN_QUESTIONS.md` | Decision/assumption/open/deferred registry; later updated with many accepted ADRs. |

Important current-state note: the repository now has both `docs/architecture/23_TECHNOLOGY_STACK_AND_RUNTIME.md` and `docs/spec/23_TESTING_QA_AND_READINESS.md`. This archive records paths as observed; it does not infer or authorize renumbering.

---

## 1.3 Cross-cutting accepted principles already represented in GitHub

- **Executable-first:** formalizable/repeatable/verifiable work should move toward executable code.
- **Local-first:** local deterministic code/algorithms/local AI before external paid routes when quality/security permit.
- **Reference-first:** pass references instead of copying large payloads where resolvers can fetch directly.
- **Evidence-first:** a Worker/model claim is not execution proof.
- **CONTROL/DATA boundary:** external/content data cannot promote itself into trusted control.
- Security and mandatory quality override cost/locality.
- Forecast-before-spend and forecast-vs-actual learning.
- Capability != permission.
- ResourceRef != permission.
- Cache != Knowledge != Evidence != SSoT.
- Full chat is not durable task state.
- Learning improves an already-correct system; it may not be required for correctness.
- One SSoT / one canonical responsibility owner.
- Modular monolith first; distributed complexity only when needed.

---

## 1.4 Later merged implementation/prototype work already in GitHub

Visible merged commits include:

- `2d21d143ce545802f9ae1fcd3f3ff09d2392767c` — machine contract format / JSON Schema / `schemas/v1`.
- `bfa167bdad11a7548bf83543165b3d535f8e3a1f` — machine Module Registry + dependency graph.
- `459244e5f79b25708cda5dbb378c55227e91292d` — Identity / Windows binding / Approval model.
- `a7b86e9e291ef19cdfd93cb2fbe9861d7d550889` — Event Journal / Checkpoint / Replay Recovery.
- `f65e3a9c11f0dc2542d2511dcca9cae91a439af5` — separate Rust Core Runtime + Electron IPC prototype.
- `08d3c10c1a744b5f6e64a733ec8d7336d681a09a` — Windows 11 DPAPI Secret Store / SecretRef.
- `ecc8c58ef4945a0e42faa563e779a3d073c87ace` — Scope Guard / path normalization / execution isolation.
- `f98bf0fc99de49e628e0ea9e711a3ea4e7d73e79` — deterministic v0.1 vertical engine + resilience tests.
- `cb3f97c3a746c85e2fdfb0a99387d412d5f88bbe` — end-to-end tracing / OpenTelemetry export.
- `8e7a2ccc1185a97dfef87fe329bb5bd8332decf2` — execution semantic snapshot / semantic isolation.
- `a73aee3a38044a951bf4611b2fec9b3efe9ceb7f` — workflow versioning / deterministic state migration.
- `ac1b55544cc8b2fd6879b28577193bdac68dc167` — reproducible evals/regression suite.
- `73e80ddb029cb27cfde117e00c5971064a76f277` — CacheEngine separate RAM-first Rust module.
- `2a63d0e4b20095e3a0983dcff7cb1066dfb02cfa` — QA Evidence REUSE / DELTA / FULL.

These commits are more authoritative than any earlier chat draft.


## 1.5 Important Issues already preserving conversation context

### Issue #1 — GitHub Project as control center

https://github.com/rassvetpublic-spec/KAT9I_OS/issues/1

Historical/current-at-snapshot intent:

- one main GitHub Project;
- Russian visible fields;
- Issues = work-state SSoT;
- Project = view/planning surface, not a second requirements source;
- the user learns GitHub through real project work;
- simplified target of exactly five main views:
  - `00 — Все задачи`
  - `01 — Готово к работе`
  - `02 — В работе`
  - `03 — Проверка`
  - `04 — Заблокировано`
- ruleset/milestones/automation/QA integration.
- At archive time this work was not fully complete.

### Issue #34 — Architecture Baseline / ADR-OQ reconciliation

https://github.com/rassvetpublic-spec/KAT9I_OS/issues/34

- Closed/completed.
- Preserved prior cross-audit findings that:
  - some “open questions” were already solved;
  - numbering had drifted;
  - accepted decisions must not silently remain marked OPEN;
  - canonical docs, README/navigation and GitHub state must be reconciled.

### Issue #43 — external benchmark

https://github.com/rassvetpublic-spec/KAT9I_OS/issues/43

- Closed/completed.
- Preserved requirement to compare KAT9I_OS with mature systems by capabilities and reproducible scenarios, not marketing.

### Issue #62 — historical Gate

https://github.com/rassvetpublic-spec/KAT9I_OS/issues/62

Historically used as G0→G4 gate/controller. Later became stale relative to newer GitHub/process decisions.

Do not reconstruct current process from #62 alone.

### Issue #87 — main Ruleset gaps

https://github.com/rassvetpublic-spec/KAT9I_OS/issues/87

At archive time it recorded:

- active `main-protection` ruleset;
- PR-only/deletion/non-fast-forward/review-thread protections observed;
- required Quality status check and strict up-to-date branch gate were not yet fully present;
- independent QA should not be assumed to be enforceable by standard GitHub ruleset alone.

### Issue #88 / PR #89 — Architecture Convergence Loop

- Issue: https://github.com/rassvetpublic-spec/KAT9I_OS/issues/88
- PR: https://github.com/rassvetpublic-spec/KAT9I_OS/pull/89

At archive time PR #89 was open.

Captured idea:

`simple laws → minimal baseline → maximal brainstorm → classify → attack complexity → Complexity Guillotine → return to simple laws → future compatibility by contracts`

Safety constraints captured in that work:

- no automatic SSoT edits;
- no automatic architecture acceptance;
- no automatic QA PASS/Gate PASS;
- no automatic Issue closing;
- no automatic merge.

Because the PR was open, this was **work-in-progress, not canonical main**.

### Issue #90 / PR #93 — Portable Promotion Protocol

- Issue: https://github.com/rassvetpublic-spec/KAT9I_OS/issues/90
- PR: https://github.com/rassvetpublic-spec/KAT9I_OS/pull/93

At archive time PR #93 was Draft/open.

Captured concepts:

- Promotion as portable abstraction, not GitHub-only Merge Queue core;
- one Promotion Queue;
- SAFE / NORMAL / STRICT / TEAM STRICT policy classes;
- Turbo as speculative preparation scheduler, not another queue/security level;
- Change Evidence / Integration Evidence / Authorization Evidence;
- deterministic ChangeSetDigest;
- ImpactAssessment;
- immutable PromotionTicket;
- `mtd` tied to the exact sealed ticket hash;
- one Promotion Lease per target;
- lease generation/fencing;
- stale-candidate check immediately before side effect;
- native GitHub Merge Queue only optional accelerator;
- personal GitHub account remains a required supported environment;
- missing capability causes safe degradation, not bypass;
- one PromotionStore SSoT.

This is **not canonical main in this archive snapshot**.

### Issue #91 / merged PR #92 — QA cost/evidence model

- Issue: https://github.com/rassvetpublic-spec/KAT9I_OS/issues/91
- PR: https://github.com/rassvetpublic-spec/KAT9I_OS/pull/92

Merged.

Replaced universal “new SHA/rebase/target movement → repeat FULL QA” with evidence applicability:

- same compatible ChangeSet can reuse Change Evidence;
- target/base movement primarily invalidates Integration Evidence, not automatically Change Evidence;
- local/material change can require DELTA;
- material/uncertain/conflicting change can require FULL/BLOCKED;
- repeated FULL should have machine-readable reason;
- independent QA requirement remains where policy requires it.

### Issue #94 — stale historical Gate #62

https://github.com/rassvetpublic-spec/KAT9I_OS/issues/94

Open at archive time.

Created specifically because #62 still contained:

- old 10-view Project design;
- obsolete “new commit invalidates QA” rule.

The intended historical lesson: a future Worker reading GitHub without this chat should not accidentally restore obsolete process from #62.

---

## 1.6 Important open PRs at archive time

These states are a historical snapshot only.

### PR #83

https://github.com/rassvetpublic-spec/KAT9I_OS/pull/83

Title observed:
`[G0][P0] chore(github): закрепить mtd, AGENTS и русские Issue Forms (#1)`

Contained/proposed:

- `AGENTS.md`;
- explicit no-merge-without `mtd` / `MTD` / `мтд`;
- Russian Issue Forms;
- expanded Russian PR template;
- GitHub workflow learning guide;
- triage helper;
- Project configuration script;
- exactly five Project views;
- project-field contract;
- fail-closed Project configuration behavior;
- Ruleset evidence.

At archive time it still required synchronization with newer QA Evidence semantics before merge.

### PR #89

https://github.com/rassvetpublic-spec/KAT9I_OS/pull/89

Architecture Convergence Loop. Open at archive time.

### PR #93

https://github.com/rassvetpublic-spec/KAT9I_OS/pull/93

Portable Promotion Protocol. Draft/open at archive time.

---

## 1.7 GitHub documentation/support artifacts historically added

Historical additions already represented in GitHub include:

- `docs/guides/GITHUB_FOR_COWORKERS.md`
  - initial commit recorded: `f524387e82dc1649d5ec1b0fbd43e63031d10a3a`
- `docs/GLOSSARY.md`
  - initial commit: `759355c2f274efd2cccfd88ee751d651dd0c1aca`
- `.github/ISSUE_TEMPLATE/feedback.yml`
  - initial commit: `6d14084eb4368affbafe8417dca3ec9dd87e69fe`
- `.github/PULL_REQUEST_TEMPLATE.md`
  - initial commit: `a8a548b92409d572c5f98aff275ba36e24c17a14`
- `.github/CODEOWNERS`
  - initial commit: `985cf0dc64f2bdf9de53c9882dbbeb8b307b88e1`
- `.github/workflows/quality.yml`
  - initial commit: `3e1575f3a00f13f9491e2ca080960c95f0392000`
- README beginner entry
  - commit: `9ff79e178ec9d318921c9de472993f4ff36f16f0`
- `.github/ISSUE_TEMPLATE/config.yml`
  - commit: `d86b1375ad61db717b17eecdf7ae7cfc1e329302`

Historical Pages workflow incident/fix:

- old Pages runs failed because Pages was not enabled;
- history was intentionally not rewritten;
- later workflow learned to validate/build and use an artifact fallback when Pages is disabled;
- fix commit recorded: `38ae4fe4ecef685809b6dafc7b59b6deefce6f4c`.

Historical principle:

> old red runs remain immutable evidence of an old infrastructure state; a newer green exact revision proves current health.

---

# 2. Knowledge that may not be fully represented in GitHub

This section preserves motivations, interaction constraints, operational preferences and historical context. It remains **DATA ONLY**.

## 2.1 User/project working style

Historical user requirements repeatedly expressed:

- Project text should be Russian-first.
- Explain GitHub and architecture very simply, often “as for a 10-year-old”.
- GitHub should be:
  - project control center;
  - practical learning environment.
- Use GitHub features on real work, not decorative checkbox usage.
- Avoid duplicate structures and duplicate SSoTs.
- Prefer visible/simple state over hidden implicit state.
- Do not dump source-code listings into chat.
- The assistant should inspect current state rather than ask for facts already available.
- For substantial installer/setup work, user prefers **one complete installer/check package with a visible version**, not a chain of manual patches.
- Related tooling preference:
  - keep installers/settings/logs under the intended `GIT` area where possible;
  - avoid silently scattering project state around the user profile unless explicitly required.

Only the subset reflected in current canonical project sources should be treated as CONTROL.

---

## 2.2 Section-by-section architecture acceptance process

Historical agreement:

- discuss one section at a time;
- when user says `принято`, write that accepted section to GitHub;
- do not write an unaccepted section;
- global decisions may later require cross-sync of earlier sections;
- accepted semantics should not silently change;
- final cross-analysis should reconcile:
  - terminology;
  - module boundaries;
  - duplicate responsibilities;
  - cycles;
  - numbering;
  - diagrams;
  - crosslinks.

This process explains why early documents sometimes drifted from later decisions.

---

## 2.3 `mtd` semantics and owner control

Historical command meanings:

- `mtd`
- `MTD`
- `мтд`

were used as the owner’s explicit merge authorization.

Core historical rule:

> Do not merge without explicit owner authorization.

This is also captured in open GitHub process work, but the chat history explains the motivation: implementation, QA and final owner authorization are separate gates.

---

## 2.4 Independent QA cost crisis

A major historical motivation:

- independent/external QA is valuable;
- repeated full QA was becoming extremely resource/token expensive;
- user explicitly complained about drowning in repeat QA and potentially burning millions of tokens;
- rebase/target movement/new SHA can be technical changes without semantic ChangeSet change;
- the system needed evidence applicability rather than automatic full re-review.

This motivated merged PR #92.

The economic reason is useful historical context even though the canonical rule is now in GitHub.

---

## 2.5 Universal product requirement

User explicitly rejected designs depending on GitHub Organization/Enterprise-only features.

Historical product principle:

> KAT9I_OS should work on ordinary personal accounts too.

Consequences discussed:

- use native platform capabilities when available;
- safe fallback when missing;
- native Merge Queue cannot be mandatory Core foundation;
- safety semantics must survive capability degradation;
- future GitLab/other adapters should fit the same core promotion model if that model becomes canonical.

---

## 2.6 Art3m1da responsibility clarification

Important correction:

- Артём / `Art3m1da` is responsible for the visualization direction at architecture/domain-responsibility level.
- This does **not** mean:
  - auto-assign every visualization Issue;
  - grant extra GitHub permissions;
  - make him owner of unrelated work.

An earlier mistaken Issue based on automatic assignment was closed as not planned.

---

## 2.7 Donor repository semantics

### Target project

https://github.com/rassvetpublic-spec/KAT9I_OS

### Primary/current donor for KAT9I engine ideas

https://github.com/NewDeep67/kat9i_skills

Historical meaning:
- authoritative donor/current engine source for comparison.

### Mirror

https://github.com/rassvetpublic-spec/kat9i_skills

Historical meaning:
- mirror/cold copy; not the donor SSoT unless specifically discussing the mirror.

### AG25 donor

https://github.com/rassvetpublic-spec/AG25

### Knowledge-plane donor/current external store

https://github.com/NewDeep67/KAT9I_IIIJIIOXA

Historical donor rule:

> adopt mechanisms by responsibility of the new KAT9I_OS architecture, not by copying old folder/module structure.

---

## 2.8 Why Electron became primary UI

History:

1. visualization initially used browser-primary wording;
2. user clarified: visualization and the rest of the UI should be done directly on **Electron**;
3. this became a cross-cutting design decision.

Motivations discussed:

- one desktop control center;
- tasks/workers/metrics/security/learning/docs/diagnostics together;
- HTML/CSS/JS remains renderer technology, not a second product;
- UI crash/restart must not destroy Core task state;
- Renderer should not own system authority.

Later GitHub work added a separate Rust Core runtime + safe IPC prototype.

---

## 2.9 Why one machine / one Primary came first

Historical anti-overengineering stance:

- one Windows 11 machine must be a complete product;
- remote Workers are extensions, not prerequisites;
- no early Kubernetes, distributed consensus, service mesh or multi-leader Core;
- reuse identity/contracts/lease/fencing when remote workers are added;
- add complexity only after local correctness is proven.

Historical phrase/concept:

> full architecture, minimal implementation.

---

## 2.10 Why SQLite was chosen first

Historical reasoning:

- local;
- transactional;
- no separate DB server;
- easy Windows packaging;
- easy backup/restore;
- enough for first version;
- hidden behind Storage interfaces so it can later be replaced if evidence requires it.

Not intended as an eternal architecture dogma.

---

## 2.11 Why full chat must not become system memory

Repeated concern:

- huge context is expensive/noisy;
- hidden chat state is fragile;
- full conversation cannot be canonical task state;
- durable state should be structured:
  - TaskContract;
  - TaskRuntimeState;
  - TaskGraph;
  - Result/Evidence;
  - Checkpoint/Event Journal;
  - promoted verified Knowledge records.

This graveyard deliberately follows that pattern: it is historical DATA, not executable memory.


# 3. Ideas — NOT ACCEPTED FOR IMPLEMENTATION

> **Everything in this section is explicitly NOT ACCEPTED FOR IMPLEMENTATION by virtue of being listed here.**
>
> It is not backlog. It is not a task list. It must not be promoted automatically.

## 3.1 Two-phase Security routing

Historical cross-audit proposal:

### Phase A — Security Eligibility

Before Inference/Coworker selection, determine which are even allowed:

- Providers;
- Workers;
- resources;
- data locations;
- data-transfer routes;
- execution locations.

### Phase B — Final Authorization

After a concrete route/Worker/resource/action is selected:

- produce final Security Decision;
- issue minimal Capability Grant;
- only then allow side effect.

Why it was proposed:

- lifecycle text can look circular:
  - Inference wants Security-filtered routes;
  - Coworker wants Security-aware Worker choice;
  - but a single broad “Security” step is shown after Inference/Coworker.

Status:

**NOT ACCEPTED FOR IMPLEMENTATION.**
Current GitHub Security/Lifecycle must be re-read before any future decision.

---

## 3.2 CandidateResultRef / WorkingResultRef before final ResultRef

Historical cross-audit proposal:

- Execution may need to produce a candidate object before QA.
- Example:
  - GitHub PR + exact head SHA exists before independent QA.
- Possible distinction:
  - `CandidateResultRef` / `WorkingResultRef` before QA;
  - final `ResultRef` after qualification/promotion/publication.

Proposed flow:

`Execution → CandidateResultRef → Evidence → QA → Promotion/Publication → ResultRef`

Why proposed:

- older lifecycle wording could imply QA needs a ResultRef that is only finalized after QA.

Status:

**NOT ACCEPTED FOR IMPLEMENTATION.**
Later Promotion contracts may solve this differently.

---

## 3.3 Dedicated Task State Registry

Historical idea:

- one machine-readable registry for all TaskRuntime states;
- no section maintains its own drifting full status list;
- detect undefined/incompatible transitions automatically.

Status:

**NOT ACCEPTED FOR IMPLEMENTATION unless separately canonized after this snapshot.**

---

## 3.4 Dedicated Metrics Registry

Historical idea:

one machine-readable metric registry containing:

- `metric_id`;
- type;
- units;
- dimensions;
- owner;
- retention/aggregation rules.

Reason:

- metrics spread across Forecasting, Recovery, Distributed, Electron, Releases, QA and Promotion.

Status:

**NOT ACCEPTED FOR IMPLEMENTATION unless current GitHub later says otherwise.**

---

## 3.5 Formal named Durable Step Contract

External comparison with Temporal / Restate / DBOS / LangGraph inspired an idea for a named durable step carrying:

- operation_id;
- input revision/hash;
- started/completed state;
- side-effect state;
- Evidence;
- checkpoint relation.

Important update:

Much of the behavior is now already represented in GitHub via:

- JournalEvent;
- Checkpoint;
- `operation_id`;
- `completed_operations`;
- idempotency;
- fencing;
- Evidence.

What remains speculative is whether a separate top-level `DurableStep` contract is useful.

Status:

**THE SEPARATE CONTRACT/OBJECT IS NOT ACCEPTED.**

---

## 3.6 TaskGraph stage as formal checkpoint boundary

Historical idea:

- checkpoint after a completed graph stage / independent execution set;
- after recovery, do not repeat successful sibling branches.

Status:

**NOT ACCEPTED FOR IMPLEMENTATION.**

---

## 3.7 Progressive Tool Disclosure

Historical idea:

Instead of sending every tool/schema/MCP description to a Worker:

1. send a compact capability index;
2. reveal detailed tool schema only when route selection actually considers it.

Reason:

- reduce context, tokens and tool noise;
- align with Context Funnel / Reference-first.

Status:

**NOT ACCEPTED FOR IMPLEMENTATION.**

---

## 3.8 External protocol patterns for future federation

Possible future research:

- ACP-like session/capability/streaming/permission patterns;
- A2A-like inter-system task/artifact exchange without shared memory.

Status:

**NOT ACCEPTED FOR IMPLEMENTATION.**
Federation remains deferred unless current GitHub says otherwise.

---

## 3.9 Plugin/package governance ideas

Inspired by mature plugin ecosystems:

- signed package;
- manifest;
- requested permissions;
- compatibility/version checks;
- capability negotiation;
- no implicit privilege.

Status:

**NOT ACCEPTED FOR IMPLEMENTATION.**
Marketplace/plugin ecosystem was historically deferred.

---

## 3.10 Aggregated “single status of main”

Historical suggestion:

- one human-readable aggregate gate showing whether current `main` is healthy across mandatory checks.

Status:

**NOT ACCEPTED HERE.**
Current Ruleset/Quality Gate work in GitHub must define any real implementation.

---

# 4. Rejected or superseded decisions

Historical DATA only. Superseded items must not be restored automatically.

## 4.1 Browser as primary UI → superseded by Electron

Earlier:

- local browser/web application as main visualization UI.

Later:

- Electron Desktop is the main user interface.
- web/HTML can remain renderer technology, documentation output or secondary/read-only UI.

Archive snapshot warning:

- `docs/architecture/17_PROCESS_VISUALIZATION.md` still contained browser-primary wording when checked.
- This is known drift, not authorization to edit.

---

## 4.2 “Any new SHA invalidates QA” → superseded

Old rule:

> a new revision after QA automatically invalidates previous QA and forces new full review.

Problem:

- unnecessary repeated expensive external QA;
- rebase/target movement can change SHA without changing semantic ChangeSet.

Replacement merged via PR #92:

- exact revision remains Provenance;
- evidence applicability is evaluated;
- QA REUSE / DELTA / FULL / BLOCKED;
- target/base movement primarily affects Integration Evidence;
- repeated FULL requires explicit reason.

Do not restore the universal old rule.

---

## 4.3 Ten Project views → simplified to five

Older design had many views:
Control Tower / G1 / Ready / Active Workers / QA / Blocked / Roadmap / Security / Evidence / Unclassified.

Later target in Issue #1:

- `00 — Все задачи`
- `01 — Готово к работе`
- `02 — В работе`
- `03 — Проверка`
- `04 — Заблокировано`

Issue #94 exists because old #62 still exposes the superseded view set.

---

## 4.4 Native GitHub Merge Queue as mandatory foundation → rejected direction

Research considered enterprise/native merge queue practices.

User requirement:

- KAT9I_OS must work on personal/non-enterprise accounts too.

Later open Promotion work therefore treats native platform queue as optional acceleration, not Core semantics.

Because PR #93 was still open, future canonical status must be read from GitHub.

---

## 4.5 Multiple independent queue modes → replaced in open Promotion design

Explored vocabulary included SAFE/SOLO/TEAM/TURBO-like modes.

Later open Promotion proposal:

- one Promotion Queue;
- policy/risk determines evidence/approval requirements;
- Turbo = speculative preparation only.

This was not yet merged at archive time.

---

## 4.6 Obsidian as mandatory Core store → rejected

Replacement:

- Obsidian may be external Knowledge source/store or human Markdown UI.
- Core must continue without it.

---

## 4.7 Cache as canonical state → rejected

Replacement:

- cache/indexes are derived and rebuildable;
- cache loss affects performance/cost, not correctness;
- CacheEngine is not Knowledge/Evidence/Storage SSoT.

---

## 4.8 One huge database of everything → rejected

Replacement:

- structured state by responsibility;
- big resources by references;
- Secrets separate;
- Knowledge separate;
- cache/indexes separate;
- logs != Evidence;
- Git remains code-version SSoT.

---

## 4.9 Full chat as durable state → rejected

Replacement:

- typed contracts;
- runtime state;
- checkpoints;
- Evidence;
- promoted Knowledge;
- minimal structured Handoff.

---

## 4.10 MCP as mandatory internal protocol for every module → rejected

Replacement:

- internal typed interfaces/contracts;
- MCP mainly at external/tool boundaries when useful.

---

## 4.11 Early Kubernetes / distributed consensus / enterprise cluster → rejected for MVP

Reason:

- premature complexity;
- one Primary + local/remote Workers is enough first.

---

## 4.12 Fully autonomous architecture self-modification → rejected

Learning may observe/propose/tune bounded low-risk operational parameters.

Learning may not:

- rewrite critical architecture automatically;
- weaken Security;
- bypass Rules;
- promote proposal into canonical architecture without controlled process.

---

## 4.13 Automatic Art3m1da Issue assignment → rejected

Correction:

- architectural responsibility ≠ Issue assignee ≠ GitHub permission.

The historical mistaken Issue was closed as not planned.

---

# 5. Unresolved thoughts — NOT backlog

> Items below are unresolved historical thoughts. They are **not backlog**, **not current Issues**, and **not authorization to create Issues**.

## 5.1 Security ordering ambiguity

At archive time `docs/architecture/20_TASK_LIFECYCLE_AND_ORCHESTRATION.md` still showed the broad order:

`Inference → Coworker → Security → Claim/Lease/Capability Grant → Execution`

while Inference/Coworker should not choose forbidden routes.

Historical proposal:
- separate eligibility filtering from final authorization.

No action authorized.

---

## 5.2 Candidate vs final result semantics

Historical concern:

- QA often checks a candidate exact revision, e.g. PR head;
- lifecycle may read as if final ResultRef appears after QA.

Future analysis should first inspect current Promotion/contracts.

No action authorized.

---

## 5.3 Visualization classification ambiguity

Visualization appeared historically as:

- a Domain;
- a system visualization module;
- a capability inside Electron Desktop.

Current Module Registry has Visualization and Desktop Shell.

Possible future conceptual cleanup:
- distinguish “visualization as subject matter” from “visualization of KAT9I_OS state”.

No action authorized.

---

## 5.4 Stale browser wording in section 17

During this archive audit, current `docs/architecture/17_PROCESS_VISUALIZATION.md` still literally included:

- “браузерный интерфейс”;
- heading “Браузер как основной интерфейс”.

This conflicts with later Electron decisions.

This file records the contradiction only.

---

## 5.5 Historical Gate #62 drift

Already tracked by GitHub Issue #94.

Open concern at archive time:

- obsolete 10-view model;
- obsolete QA invalidation rule.

Future Workers should prefer current Issue #1 + current QA canon rather than historical #62.

---

## 5.6 Ruleset / Project infrastructure not fully converged

At archive time:

- Issue #1 remained unfinished;
- Issue #87 tracked missing required Quality status check/update-before-merge enforcement;
- PR #83 remained open.

Already GitHub-tracked; not a graveyard task.

---

## 5.7 Wiki / Pages state

Snapshot:

- Wiki enabled despite historical no-second-SSoT policy.
- Pages repository feature not enabled.
- Pages workflow already had a fallback artifact path.

Snapshot only.

---

## 5.8 Deferred implementation technologies

Historical deferred choices:

- remote Worker transport;
- local discovery;
- vector index technology;
- updater/installer mechanism;
- first local AI runtime;
- first external AI Provider;
- enterprise multi-user;
- federation;
- marketplace;
- broad provider support.

They were deferred intentionally to avoid blocking MVP.

---

## 5.9 Whether a separate DurableStep contract is actually needed

Much of durable behavior is already present through current recovery schemas.

Future design should not introduce a new top-level object unless it reduces complexity.

No action authorized.


# 6. Files and artifacts from the chat / related project conversations

## 6.1 `DeepSeek-Harness-20260908-165443.log`

Status:

- Confirmed present in ChatGPT File Library during this archival audit.
- Related to DeepSeek Harness + GitHub setup.
- Useful mainly for forensic/debugging of Harness startup/configuration.

Security note:

- the raw log contains a local web session URL with a token-like query parameter;
- that value is deliberately **NOT copied into this graveyard**;
- do not publish the raw log without redaction.

Should it be saved separately?

- **YES, only if raw Harness diagnostics may be useful later.**
- Treat as sensitive diagnostic data.

Connected to GitHub?

- setup outcomes/configuration are partly represented in project tooling/history;
- the raw log itself is not canonical GitHub content.

---

## 6.2 `dsh-session-session-abea90f9-bbba-44d0-b7f7-42183330eb98.zip`

Known from prior project conversation as a DeepSeek Harness session bundle.

Archive audit result:

- exact filename was searched in File Library;
- it was **not found as an indexed retrievable item** in this run;
- raw contents could therefore not be embedded or summarized.

Should it be saved separately?

- **YES if session-level forensic/debug data matters.**
- If the original attachment is still accessible in the chat UI, save it before deleting the chat.
- Do not place it in public GitHub without a separate security review.

Connected to GitHub?

- no evidence that it is canonical;
- likely diagnostic only.

---

## 6.3 `configure_project.ps1`

Status:

- Confirmed in ChatGPT File Library during archive audit.
- Associated with GitHub Project configuration work.
- A later/evolved version is described in open PR #83.

Should it be saved separately?

- Optional.
- For future operational use, prefer the current GitHub branch/PR/main version over the File Library copy.
- Keep File Library copy only for historical comparison.

Connected to GitHub?

- yes, conceptually and through PR #83/project-management work.

---

## 6.4 DeepSeek Harness setup version history

Related historical tooling context recovered from prior interactions:

- setup v0.4.4 was used for DeepSeek + GitHub tooling;
- later v0.4.5 context included:
  - CRLF handling fix around a DPAPI token;
  - secure credential handling through CLIXML;
  - GitHub PAT/scope/private-repo checks;
  - expected local web UI around `127.0.0.1:3080`;
- user preference: deliver one complete installer/check file with a version number instead of incremental patch fragments.

This is tooling history, **not KAT9I_OS architecture canon**.

---

## 6.5 Historical generated Markdown sections

Sections 25–32 were drafted in chat and then accepted into GitHub.

Because current GitHub contains them, separate preservation of every chat draft is unnecessary for canonical recovery.

This graveyard preserves:

- acceptance order;
- historical commit references where known;
- reasons and later corrections.

---

## 6.6 HTML documentation / Pages artifacts

Historical Pages incident:

- old workflow failed because Pages site was not enabled;
- failures were intentionally kept as immutable history;
- workflow was changed so “Pages disabled” does not create a false project failure;
- later green runs proved newer revisions.

Historical fix commit recorded in chat:

`38ae4fe4ecef685809b6dafc7b59b6deefce6f4c`

No need to preserve old Actions binaries unless forensic CI analysis is desired.

---

## 6.7 Other File Library items discovered but not imported as KAT9I_OS facts

File Library search also returned adjacent/unrelated files such as:

- `11_SECURITY_PRIVACY_GITHUB.md`
- `OBSIDIAN.md`
- `ENVIRONMENT.md`
- SUNO knowledge exports
- engineering PDFs/data
- other project dumps

They were **not automatically promoted into this archive as KAT9I_OS facts**.

---

# 7. External sources

Links are historical references. Re-check current versions before reuse.

## 7.1 Project / donor repositories

### KAT9I_OS

https://github.com/rassvetpublic-spec/KAT9I_OS

### AG25

https://github.com/rassvetpublic-spec/AG25

Used as architecture/code/idea donor.

### Current KAT9I donor

https://github.com/NewDeep67/kat9i_skills

Historically treated as the authoritative donor/current engine source.

### Public mirror of kat9i_skills

https://github.com/rassvetpublic-spec/kat9i_skills

Historically treated as mirror/cold copy rather than donor SSoT.

### Knowledge plane / donor

https://github.com/NewDeep67/KAT9I_IIIJIIOXA

### Related GitHub-learning reference project

https://github.com/rassvetpublic-spec/local-listener-android

Its GitHub Project/onboarding organization was used as a practical reference when designing KAT9I_OS project-management UX.

---

## 7.2 External architecture / agent / workflow projects examined

### Goose

https://github.com/block/goose

Historical takeaway:

- highly relevant desktop-agent architecture donor;
- Electron/TypeScript UI with Rust-centric core patterns;
- keep non-trivial system logic out of Renderer.

### OpenHands

https://docs.openhands.dev/openhands/usage/architecture/runtime

Historical takeaway:

- strong sandbox/runtime boundary;
- UI separate from execution runtime.

### LangGraph

https://docs.langchain.com/oss/python/langgraph/persistence

Historical takeaway:

- checkpoint/persistence/resume concepts;
- useful for graph recovery reasoning.

### Temporal

https://docs.temporal.io/

Historical takeaway:

- durable workflow execution;
- replay/side-effect discipline.

### Restate

https://docs.restate.dev/

Historical takeaway:

- durable/journaled operations and recovery patterns.

### DBOS

https://docs.dbos.dev/

Historical takeaway:

- durable execution / exactly-once-oriented transaction patterns.

### Microsoft Agent Framework / agent resources

https://microsoft.github.io/agent-resources/

Historical takeaway:

- typed workflows/checkpoints/context providers;
- progressive tool concepts.

### Letta

https://docs.letta.com/

Historical takeaway:

- explicit memory/state models and context compaction.

### OpenAI Agents SDK

Historical reference used:

https://openai.github.io/openai-agents-js/guides/handoffs/

Historical takeaway:

- handoff/guardrail/authorization-boundary ideas;
- model handoff must not imply permissions.

### CrewAI

https://docs.crewai.com/

Historical takeaway:

- deterministic Flow vs agentic work separation.

### Dify

https://docs.dify.ai/

Historical takeaway:

- plugin/package manifest and permission ideas;
- not recommended as KAT9I_OS core.

### A2A

https://github.com/a2aproject/A2A/blob/main/docs/specification.md

Historical takeaway:

- possible future federation/task/artifact protocol donor;
- not an internal KAT9I_OS module bus.

### Electron security guidance

https://www.electronjs.org/docs/latest/tutorial/security

Historical takeaway:

- context isolation;
- narrow preload bridge;
- avoid broad Node privileges in Renderer;
- validate IPC.

### Semantic Versioning

https://semver.org/

Used as versioning reference.

---

## 7.3 Historical external-comparison conclusion

Do **not** define KAT9I_OS as:

- “LangGraph + UI”
- “CrewAI + SQLite”
- “another agent framework”

Instead:

- KAT9I_OS owns governance, contracts, state, security, evidence, execution boundaries and orchestration.
- external frameworks/libraries may be used:
  - inside a Worker;
  - inside a Domain;
  - as adapter/integration;
  - as reference implementation.

Most useful donor patterns by capability:

- Goose → Electron ↔ Core separation.
- OpenHands → sandbox/runtime boundary.
- LangGraph → checkpointed graph execution.
- Temporal/Restate/DBOS → durable side-effect/recovery principles.
- Microsoft Agent Framework → checkpoint/context/tool-disclosure ideas.
- Letta → memory model ideas.
- Dify → plugin governance.
- A2A/ACP-like protocols → possible future interoperability/federation.

Again: historical comparison, not implementation authority.

---

# 8. Brief chronology

## 8.1 Project framing

- KAT9I_OS developed from a broader AI-managed/agent-orchestration concept.
- Donor projects `kat9i_skills`, AG25 and KAT9I_IIIJIIOXA were used for ideas and working mechanisms.
- GitHub was chosen as both source control and project-learning/control surface.
- Russian-first simple documentation became explicit policy.

## 8.2 Foundational architecture

Core ideas emerged and were accepted:

- TaskContract.
- Rules/Rule Manager.
- Metrics/Telemetry.
- Learning.
- Context.
- Knowledge.
- Resources.
- Inference.
- Coworker.
- Execution.
- Cache.
- Security.
- Integrations.
- Domains.
- Telegram boundary.
- Personal Layer.
- Visualization.
- Planning/Forecasting.

Cross-cutting laws solidified:

- Executable-first.
- Local-first.
- Reference-first.
- Evidence-first.
- CONTROL/DATA.
- one SSoT.
- capability != permission.

## 8.3 Recovery and lifecycle

- task lifecycle was formalized;
- checkpoint/recovery/lease/fencing/idempotency concepts were added;
- unknown state must become BLOCKED rather than guessed;
- failure/recovery metrics and adaptive timeout ideas were added.

## 8.4 Configuration/start/update

- Windows 11 first-class target;
- environment discovery;
- capability discovery != permission;
- update/backup/migration/health/rollback;
- SAFE/OFFLINE/MAINTENANCE modes.

## 8.5 GitHub control plane / learning experience

User requested GitHub be used “to the full” for real project work and personal learning.

Architecture separated:

- docs;
- Issues;
- PR;
- Actions;
- Project;
- Milestones;
- Releases;
- Discussions;
- Pages.

Beginner Russian guides/forms/templates/workflows were added.

Historical Pages failures were preserved, not rewritten.

## 8.6 Section 23 acceptance

Testing / independent QA / readiness was accepted.

At that stage QA was more tightly tied to exact revision than the later evidence-applicability model.

## 8.7 Sections 25–32

- Storage accepted.
- Internal contracts accepted.
- Module Registry/responsibility map accepted.
- Distributed deployment accepted.
- user explicitly clarified Electron as the main UI.
- Electron UI section accepted.
- versioning/releases accepted.
- roadmap/MVP accepted.
- ADR/open-question registry accepted.

## 8.8 Mandatory cross-analysis request

User explicitly required later:

- cross-analysis of all sections;
- search/analysis of similar projects on the internet.

This was performed.

## 8.9 Cross-audit

Historical findings included:

- numbering drift;
- OQs already solved but still marked open;
- browser-primary wording vs Electron;
- duplicated responsibility-map concepts;
- glossary semantic drift;
- Security ordering ambiguity;
- candidate/final result lifecycle ambiguity;
- need for stronger machine-readable contracts/registries.

Several findings later became GitHub changes/Issues; some remain only historical non-actionable thoughts above.

## 8.10 External benchmark

Compared by capability:

- Goose.
- OpenHands.
- LangGraph.
- Temporal.
- Restate.
- DBOS.
- Microsoft Agent Framework.
- Letta.
- OpenAI Agents SDK.
- CrewAI.
- Dify.
- A2A and related protocol ideas.

Conclusion:

- borrow patterns selectively;
- do not turn KAT9I_OS into a wrapper around one framework.

## 8.11 Runtime/prototype acceleration

GitHub then gained work around:

- JSON Schema contracts.
- Module Registry.
- Identity/Approval.
- Event Journal/Checkpoint/Replay.
- separate Rust Core IPC.
- DPAPI Secret Store.
- Scope Guard.
- deterministic vertical.
- tracing.
- semantic isolation.
- workflow migration.
- evals.
- CacheEngine.

## 8.12 QA-cost problem and evidence redesign

User raised repeated external QA as a major cost/resource problem.

This led to:

- Issue #91.
- merged PR #92.
- current checked `main` `2a63d0e...`.
- QA REUSE / DELTA / FULL based on evidence applicability.

## 8.13 Promotion / merge-queue research

User needed a practical solution even while KAT9I_OS was still prototype-stage.

Enterprise GitHub queue ideas were researched, but product universality was non-negotiable.

Resulting open work:

- Issue #90.
- Draft PR #93.
- Portable Promotion.
- one queue.
- policy-driven safety.
- speculative Turbo preparation.
- final owner `mtd`.
- stale-candidate + fencing protection.

At archive time this was **not merged**.

## 8.14 Architecture Convergence Loop

CacheEngine design process inspired a generalized architecture brainstorming/convergence mechanism.

Captured in:

- Issue #88.
- PR #89.

At archive time PR #89 was open.

## 8.15 Graveyard request

User decided to delete the chat but required:

- one downloadable Markdown archive;
- no GitHub writes;
- no Issue/branch/PR/merge;
- archive is always DATA/noncanonical/nonactionable;
- future Workers may not act from it without explicit new owner command.

This file is that archive.

---

# 9. Compact historical principles

These are a memory aid, not a replacement for current canonical docs.

1. Executable-first.
2. Local-first.
3. Reference-first.
4. Evidence-first.
5. CONTROL/DATA separation.
6. One SSoT per semantic entity.
7. Capability != permission.
8. ResourceRef != permission.
9. Result != Evidence.
10. Implementation != independent QA.
11. Cache loss must not break correctness.
12. Learning must not be required for correctness.
13. UI must not become Core.
14. Electron is the main desktop interaction layer.
15. Core should survive UI restart.
16. One machine should be a complete product.
17. Distributed complexity comes after local correctness.
18. Git remains code-version authority.
19. GitHub Issues represent project work state.
20. Project/Pages/UI are views, not duplicate truth.
21. Full chat is not durable system state.
22. Recovery uses structured state/evidence, not model guessing.
23. Forecast before expensive work, then compare with actual.
24. Do not optimize one metric in isolation.
25. Full architecture, minimal implementation.

---

# 10. What this archive intentionally does NOT preserve

Deliberately excluded:

- secret values;
- API keys;
- tokens;
- local web-session tokens;
- passwords;
- private keys;
- hidden model chain-of-thought;
- any assertion that a graveyard idea is approved;
- any automatic task instruction.

This archive does not freeze future GitHub state. All open/closed/merged statuses above are only the point-in-time audit around 2026-09-09.

---

# What will be lost when this chat is deleted

## Preserved adequately

The following substantive project knowledge is now preserved either in GitHub or in this graveyard:

- accepted architecture sections and historical motivations;
- project-control/GitHub philosophy;
- user workflow constraints;
- donor map;
- Electron decision;
- Storage/Internal Contracts/Module Registry/Distributed/UI/Release/Roadmap/ADR history;
- external benchmark conclusions;
- superseded browser and QA models;
- unresolved two-phase Security / candidate-result thoughts;
- repeated-QA cost motivation;
- portable promotion discussion;
- Architecture Convergence idea;
- important Issue/PR/commit links;
- DeepSeek Harness log existence and security warning;
- relevant installer/setup preferences.

## Not fully preservable in this Markdown

### 1. Raw `dsh-session-session-abea90f9-bbba-44d0-b7f7-42183330eb98.zip`

The session ZIP was referenced historically but could not be retrieved from File Library during this archival audit.

Therefore its byte-level/session-level diagnostic contents are **not preserved here**.

If the attachment is still available in the chat UI and those diagnostics matter, save it separately before deleting the chat.

### 2. Raw attachment bytes in general

This Markdown preserves meaning, names and disposition of artifacts; it does not embed binary attachments or full sensitive diagnostic logs.

### 3. Historical setup screenshots

The resulting decisions/context are preserved, but not every screenshot pixel from old UI walkthroughs.

Because at least one referenced raw artifact (`dsh-session-...zip`) could not be preserved or verified, the strict user-specified condition for a SAFE marker is **not met**.

**DO NOT USE `SAFE TO DELETE CHAT AFTER GRAVEYARD IMPORT` YET if raw session diagnostics matter.**

If the owner explicitly decides the missing raw ZIP/screenshots are disposable, then the substantive KAT9I_OS design/context appears sufficiently preserved between this graveyard and GitHub.
