# KAT9I OS — Architecture Context

> Initial architecture snapshot distilled from the design discussion that started with the modular-monolith proposal.
> This document intentionally excludes unrelated earlier chat context.
> Status: architecture draft / design context, not an implementation specification.

## 1. Core direction: modular monolith

The proposed direction is to converge KAT9I and AG25 into a **modular monolith** rather than continue growing cross-repository bridges.

The goal is not a "single pile of code". The goal is:

- one repository;
- one release;
- one CI graph;
- one end-to-end lifecycle;
- one task model;
- one policy model;
- strict internal module boundaries;
- external data/knowledge kept outside the product repository.

The main expected gains:

- fewer cross-repository contracts and compatibility problems;
- easier end-to-end testing;
- easier Windows bootstrap and local deployment;
- simpler debugging and telemetry;
- atomic refactoring across policy + execution;
- less duplicated state and transport logic;
- faster development of worker orchestration;
- easier enforcement of rules directly in execution.

A proposed top-level decomposition:

```text
KAT9I/
├── core/
├── context/
├── inference/
├── coworker/
├── execution/
├── security/
├── integrations/
├── domains/
├── personal/
├── resources/
├── telemetry/
└── tests/
```

The architectural question split is:

```text
DOMAIN      → What needs to be done?
CORE        → Which rules/policies/contracts apply?
CONTEXT     → What does the model need to know?
INFERENCE   → Which intelligence/provider should be used?
COWORKER    → Who should do the work?
EXECUTION   → How is the work physically executed?
INTEGRATION → How do we reach external systems?
PERSONAL    → How should the system behave for this user?
RESOURCES   → Where are source context and result artifacts located?
```

---

## 2. Core

`core/` is the generic control plane.

Suggested contents:

```text
core/
├── tasks/
├── contracts/
├── rules/
├── skills/
├── routing/
├── policy/
└── learning/
```

Responsibilities:

- generic task contracts;
- skill registry and skill routing;
- Rule Manager;
- Effective Ruleset;
- policy conflict resolution;
- generic task/domain routing;
- governed learning/proposals;
- stable internal contracts.

Hard rule:

> Domain-specific semantics must not leak into the generic core.

Examples:
- Core may know that a rule applies to a task.
- Core should not know what a chorus, BPM, rhyme, pressure sensor, or PR review means.

---

## 3. Execution

`execution/` contains the low-level mechanics that AG25 currently largely owns.

Suggested structure:

```text
execution/
├── workers/
├── runtime/
├── processes/
├── worktrees/
├── leases/
├── evidence/
├── scope_guard/
├── timeouts/
└── cleanup/
```

Responsibilities:

- run processes;
- launch/supervise workers;
- manage worktrees and branches;
- enforce timeout;
- maintain leases;
- collect execution evidence;
- scope guard;
- cleanup;
- process lifecycle.

Key boundary:

```text
Coworker = WHO gets the task
Execution = HOW the task is physically run
```

---

## 4. Coworker: distributed agent work

`coworker/` is a first-class platform component, not a domain.

Purpose:

> Coordinate distributed work between local agents, local machines, remote Katya, cloud workers, and potentially humans.

Suggested structure:

```text
coworker/
├── coordinator/
├── worker_registry/
├── discovery/
├── capabilities/
├── scheduler/
├── claims/
├── leases/
├── delegation/
├── messaging/
├── handoff/
├── presence/
├── local/
├── remote/
└── federation/
```

### Worker Registry

A worker should be describable as:

```text
Worker
├── id
├── location
├── runtime
├── skills
├── capabilities
├── connectors
├── availability
├── current_task
├── trust_level
└── last_seen
```

Worker types may include:

```text
LOCAL
REMOTE
CLOUD
HUMAN
```

Remote Katya should not use a special privileged architecture. It should be another worker/coordinator endpoint with explicit capabilities and scope.

### Capability grants

Remote/local workers should receive a bounded grant, for example:

```text
WorkerGrant
├── repository
├── allowed_paths
├── read/write capabilities
├── PR creation
├── merge permission
├── timeout
└── expiration
```

A worker receives only:

- task scope;
- required context;
- Effective Ruleset / rules reference;
- temporary capabilities;
- output contract.

### Distributed layout example

```text
                   KAT Coordinator
                         │
          ┌──────────────┼───────────────┐
          ▼              ▼               ▼
     Local PC       Remote Katya      Server
          │              │               │
      ┌───┴───┐      ┌───┴───┐       ┌───┴───┐
    Worker A Worker B Agent C Agent D Worker E
```

The current AG25 Mesh concepts map naturally here:

```text
AG25 orchestration  → coworker/
AG25 worker runtime → execution/
AG25 security       → security/
AG25 GitHub logic   → integrations/github/
AG25 Suno logic     → domains/suno/
```

AG25 does not need to be "deleted"; its useful components are absorbed into the correct modules.

---

## 5. Domains

`domains/` contains applied task stacks.

A domain answers:

> What kind of work are we doing, and what domain-specific workflow/skills/validators apply?

Proposed examples:

```text
domains/
├── software_delivery/
├── repository_optimization/
├── suno/
├── research/
├── documents/
├── engineering/
└── automation/
```

Domains should call platform capabilities through contracts, not reach into execution internals.

---

## 6. Software Delivery domain

`software_delivery/` covers Issue/PR/QA/release work.

Suggested structure:

```text
domains/software_delivery/
├── contracts/
├── workflows/
├── stacks/
├── skills/
├── validators/
├── policies/
└── tests/
```

Example stacks:

### issue_to_pr

```text
Issue
→ Analyze
→ Plan
→ Claim
→ Implement
→ Test
→ PR
```

### pr_to_merge

```text
PR
→ Diff Analysis
→ Policy Check
→ QA
→ CI
→ Review
→ Merge
```

### qa

```text
Target
→ Exact Head Binding
→ Static Checks
→ Tests
→ Behavioral Checks
→ Evidence
→ PASS / FAIL
```

### bug_repair

```text
Failure
→ Reproduce
→ Root Cause
→ Fix
→ Regression Test
→ QA
→ PR
```

### roadmap

```text
Issues
→ Dependency Graph
→ Duplicate Detection
→ Priority
→ Batch Formation
→ Execution Order
```

Important governance rule:

```text
ImplementationWorker != QAWorker
```

Independent QA should be a workflow invariant, not merely text guidance.

---

## 7. Repository Optimization domain

This should be separate from normal issue implementation.

Purpose:

> Analyze a repository as a system and produce an evidence-backed optimization backlog.

Suggested structure:

```text
domains/repository_optimization/
├── analyzers/
├── skills/
├── workflows/
├── metrics/
├── recommendations/
└── tests/
```

Pipeline:

```text
Repository
   ↓
Inventory
   ↓
Architecture Map
   ↓
Dependency Analysis
   ↓
Duplication Analysis
   ↓
Dead Code
   ↓
Complexity
   ↓
Tests / CI
   ↓
Documentation
   ↓
Security
   ↓
Performance
   ↓
Improvement Backlog
```

Potential output:

```text
RepositoryOptimizationReport
├── findings
├── severity
├── evidence
├── suggested_fix
├── estimated_effort
├── dependencies
└── proposed_issues
```

Then:

```text
Repository Optimization
        ↓
proposed Issues
        ↓
Software Delivery
        ↓
Coworker
        ↓
implementation workers
```

---

## 8. Suno domain

Suno is explicitly separated as a **domain module** while remaining inside the monolith.

Reason:

> Suno is an application of the agent platform, not infrastructure of the agent platform.

Generic execution should not know about:

- Verse;
- Chorus;
- BPM;
- key;
- vocals;
- rhyme;
- dramaturgy;
- arrangement;
- Style/Lyrics/Negative;
- Suno-specific validation.

Suggested structure:

```text
domains/suno/
├── contracts/
├── pipeline/
├── skills/
├── rules/
├── validators/
├── formatters/
├── knowledge/
├── presets/
├── evaluation/
└── tests/
```

Example skills:

```text
dramaturg
lyric-editor
rhyme-editor
structure-editor
vocal-director
style-engineer
suno-prompt-engineer
final-reviewer
```

The dramaturg module belongs here because concepts such as exposition, conflict, culmination, hero, and dramatic function are song-domain semantics.

Example Suno pipeline:

```text
INPUT
  ↓
IDEA ANALYSIS
  ↓
DRAMATURGY
  ↓
LYRICS EDIT
  ↓
STRUCTURE
  ↓
VOCAL DESIGN
  ↓
STYLE DESIGN
  ↓
SUNO FORMAT
  ↓
VALIDATION
  ↓
FINAL
```

Important ownership split:

```text
Suno owns skill content and domain workflow.
KAT9I Core owns registry, routing, governance, policy and generic contracts.
Execution owns physical execution.
```

The same KAT9I platform can later host other domains without contaminating the execution engine with music logic.

---

## 9. Other example domains

### Research

```text
Question
→ Discovery
→ Sources
→ Verification
→ Comparison
→ Synthesis
→ Report
```

### Documents

```text
Input files
→ Extraction
→ Validation
→ Translation
→ Formatting
→ PDF/DOCX
```

### Engineering

```text
Requirements
→ Standards
→ Candidate search
→ Compliance check
→ Configuration
→ Technical description
→ Documentation
```

### Automation

```text
Trigger
→ Condition
→ Task
→ Worker
→ Result
→ Notification
```

---

## 10. Personal layer

A separate personal layer is required.

Proposed structure:

```text
personal/
├── profile/
├── rules/
├── preferences/
├── settings/
├── knowledge/
└── workspaces/
```

Four concepts must remain separate:

| Layer | Purpose |
|---|---|
| Knowledge | Facts/history/decisions |
| Rules | MUST / MUST NOT constraints |
| Preferences | Soft preferences |
| Settings | Runtime/environment configuration |

Examples:

### Knowledge

```text
Canonical KAT repository is X.
A certain song has BPM/key Y.
A project uses Windows.
```

### Rule

```text
Never use a mirror as runtime source-of-truth.
A specific project forbids male vocals.
Secrets must not leave local environment.
```

### Preference

```text
Prefer concise reports.
Prefer tables.
Prefer Russian output.
```

### Setting

```text
platform = windows
shell = pwsh
max_local_workers = 3
default_provider = ...
```

Hard rules can block work. Preferences must not.

---

## 11. Personal knowledge base

The personal knowledge mechanism belongs to the product, but the physical knowledge data should remain external.

Inside KAT9I:

```text
personal/knowledge/
├── schema/
├── providers/
├── index/
└── policies/
```

External Personal Data Plane may contain:

```text
KAT9I_IIIJIIOXA
Obsidian
ChatGPT memory
Google Drive
local notes
project documentation
research databases
```

The Engine should access them through providers/connectors.

Do not merge all private/personal data into the product Git repository.

---

## 12. Personal workspaces/projects

Projects are not domains.

Examples:

```text
Suno        = domain
AG25        = project/repository
Genre_test  = project
KAT9I_OS    = project/system
```

Suggested structure:

```text
personal/workspaces/
├── kat9i/
├── ag25/
├── genre_test/
└── sqwin/
```

A workspace may define:

```text
ProjectContext
├── repositories
├── local_paths
├── project_rules
├── knowledge_sources
├── active_issues
├── runtime
└── preferred_workflows
```

This allows one KAT instance to work across many projects.

---

## 13. Context Engine

Token/context optimization should be a platform layer.

Suggested structure:

```text
context/
├── references/
├── resolver/
├── scopes/
├── manifests/
├── retrieval/
├── token_budget/
├── compression/
├── summaries/
├── context_cache/
├── context_packs/
└── materializer/
```

Initial concept:

```text
Task
 ↓
Context Compiler
 ↓
Minimal Context Pack
 ↓
Model
```

But the preferred design evolves into **reference-first context**, where KAT does not carry large context bodies unless necessary.

---

## 14. Reference-first architecture

The central design principle:

> KAT9I should orchestrate references, permissions, tasks and result locations instead of transporting large model context payloads.

Bad path:

```text
KAT
→ download repository
→ put large repository into prompt
→ send to provider
→ receive huge response
→ resend it to another worker
```

Preferred path:

```text
KAT
→ TaskContract
→ ContextRefs
→ provider reads sources through its own connectors
→ performs work
→ writes result directly to shared sink
→ KAT receives ResultRef
```

This turns KAT from a **data bus** into a **control bus**.

---

## 15. Resource Fabric

Introduce a first-class `resources/` component.

Suggested structure:

```text
resources/
├── registry/
├── refs/
├── resolvers/
├── sinks/
├── permissions/
├── provenance/
└── cache/
```

It manages resource identities such as:

```text
github://...
gdrive://...
knowledge://...
file://...
mcp://...
artifact://...
```

### ResourceRef / ContextRef

Concept:

```text
ContextRef
├── type
├── provider
├── uri
├── version/revision
├── scope
├── access
├── trust
├── freshness
└── resolver_hint
```

Example:

```text
type: github
repository: NewDeep67/kat9i_skills
revision: <commit>
scope:
  - Issue #...
  - kat9i/rules/**
  - tests/**
access: read
```

### URL is identity; Connector is transport

Important abstraction:

```text
ResourceRef = WHAT
Connector   = HOW TO GET IT
```

The same GitHub resource may be resolved by:

```text
ChatGPT GitHub connector
native GitHub API
MCP GitHub server
local Git checkout
```

The domain should not need to know which one.

---

## 16. Context Manifest

A task should normally carry references, not full source material.

```text
TaskContract
├── objective
├── context_manifest
│   ├── github_ref
│   ├── issue_ref
│   ├── drive_ref
│   └── knowledge_ref
├── rules_ref
├── output_contract
└── result_sink
```

Reference-first resolution algorithm:

```text
RESOURCE REFERENCE
    ↓
Can provider resolve source itself?
    │
   YES → pass reference
    │
    NO
    ↓
Can a connector be attached?
    │
   YES → use connector
    │
    NO
    ↓
KAT materializes minimal context
```

Rule:

> Materialize context only when reference resolution is unavailable.

---

## 17. ResultRef and ResultSink

Results should follow the same reference-first design.

Instead of returning a huge report/diff through KAT, a provider writes directly to a sink:

```text
ResultSink
├── GitHub PR
├── GitHub Issue/comment
├── GitHub artifact
├── Google Drive document
├── file/artifact store
└── Knowledge entry
```

KAT receives:

```text
ResultRef
├── type
├── uri/id
├── revision/head
├── evidence
└── provenance
```

Example development flow:

```text
KAT
 ↓
task source = GitHub Issue
context = GitHub repository reference
result sink = GitHub PR

Provider/worker
 ↓
reads repo using connector
 ↓
creates PR

KAT
 ↓
receives PR ResultRef
```

QA should then receive the PR reference, not a re-transmitted diff:

```text
Worker A → PR #X
KAT → QA Task(target = PR #X)
QA Worker → reads PR through GitHub connector
```

This naturally supports independent QA and minimizes outgoing payloads.

---

## 18. RulesRef

Effective Ruleset can also be reference-backed.

Instead of passing a large resolved rules body every time:

```text
RulesRef
├── uri
├── revision
├── digest
└── required
```

The worker/provider resolves the snapshot itself and records the digest used.

This preserves provenance:

> Which exact rule snapshot governed the task?

---

## 19. Inference / Provider layer

Model selection should be a dedicated platform component, separate from Coworker.

Suggested structure:

```text
inference/
├── router/
├── model_registry/
├── provider_registry/
├── capability_matrix/
├── budget/
├── escalation/
└── providers/
    ├── local/
    ├── api/
    ├── seat/
    └── remote_kat/
```

Key distinction:

```text
Coworker = who executes?
Inference/Provider Router = which intelligence/runtime/provider route?
```

---

## 20. Intelligence tiers

Keep a simple abstract quality classification:

```text
LOW
NORMAL
HIGH
```

Examples:

### LOW
- classification;
- tagging;
- extraction;
- simple summaries;
- commit messages;
- duplicate detection;
- format checks;
- chunk ranking.

### NORMAL
- ordinary issue implementation;
- ordinary PR review;
- tests;
- bounded refactoring;
- Suno prompt engineering;
- research synthesis;
- documentation;
- common QA.

### HIGH
- architecture;
- complex debugging/root-cause;
- security;
- difficult rule conflicts;
- cross-repository design;
- critical QA;
- ambiguous high-risk decisions.

HIGH should be an escalation path, not the default for every stage.

---

## 21. Stage-level model selection

A task must not be tied to one intelligence tier.

Example:

```text
Issue ingestion        → LOCAL/LOW
Context retrieval      → deterministic/local
Planning               → NORMAL
Architecture decision  → HIGH if required
Implementation         → NORMAL
Formatting             → LOW
QA                     → NORMAL
Critical ambiguity     → HIGH
```

Core principle:

> HIGH/NORMAL/LOW is a property of a task stage, not of the whole task or a permanent property of an agent.

Escalation model:

```text
LOCAL/LOW
  ↓ if insufficient
NORMAL
  ↓ if insufficient / critical ambiguity
HIGH
```

Security/policy defines the minimum floor and cannot be downgraded by a cheaper classifier.

---

## 22. Provider economic classes

Provider selection must distinguish intelligence from economics.

Proposed economic/runtime classes:

```text
LOCAL_FREE
SUBSCRIPTION_INCLUDED
METERED_API
PREMIUM_API
```

A provider may be:

```text
intelligence = HIGH
economic_class = SUBSCRIPTION_INCLUDED
```

or:

```text
intelligence = NORMAL
economic_class = LOCAL_FREE
```

This matters because a web subscription or licensed seat may not require per-token API optimization in the same way a metered API does.

---

## 23. Subscription-seat providers

A provider can be an already-paid interactive environment:

```text
providers/seat/
├── chatgpt/
├── antigravity/
└── other/
```

Conceptual provider type:

```text
SUBSCRIPTION_SEAT
```

Examples:

- ChatGPT web/Work environment;
- Antigravity;
- another AI web environment;
- a licensed coding agent environment.

Important constraint:

> A web subscription is not the same thing as an API.

KAT must not assume it can automate a web product via arbitrary HTTP calls.

Use a supported adapter for that seat/environment.

A seat endpoint can advertise:

```text
WorkerEndpoint
├── provider_type
├── intelligence
├── connectors
├── write_capabilities
├── usage_state
├── availability
└── restrictions
```

---

## 24. Connector-aware provider routing

If the provider already has the required connector, KAT should prefer sending a reference instead of materializing context.

Example:

```text
TASK source = Google Drive

Worker A:
HIGH
Drive connector = YES

Worker B:
HIGH+
Drive connector = NO
```

Worker A may be the better route because it has **data affinity**.

Routing should consider:

```text
RouteScore =
    capability_match
  + intelligence_fit
  + source_affinity
  + connector_availability
  + privacy_fit
  + result_sink_support
  + subscription_availability
  - metered_cost
  - transfer_cost
  - latency
```

`transfer_cost` becomes a first-class routing concern.

---

## 25. ProviderRoute

The earlier "Model Router" concept should evolve into a broader provider/execution-intelligence router.

Concept:

```text
ProviderRoute
├── worker
├── model_class
├── provider
├── economic_class
├── context_transport
├── connectors
├── tool_transport
├── result_sink
└── fallback
```

Possible route examples:

```text
HIGH
ChatGPT subscription
GitHub connector
result → GitHub PR
```

```text
NORMAL
Local AI
local filesystem
result → local artifact
```

```text
HIGH
Metered API
KAT-materialized context
result → KAT
```

The last route can be more expensive even with similar intelligence because of context transfer.

---

## 26. Local AI provider layer

Local models belong under:

```text
inference/providers/local/
```

Possible backend adapters:

```text
Ollama
llama.cpp
LM Studio
vLLM
custom local API
```

Core should only see a stable inference contract.

Local AI is useful for:

- private/local-only content;
- logs;
- repository inventory;
- classification;
- indexing;
- deduplication;
- secret detection;
- chunk ranking;
- context compression;
- repetitive low-cost analysis.

A strong pattern:

```text
large local data
   ↓
deterministic parser
   ↓
local AI filtering/summary
   ↓
small set of ContextRefs / summary
   ↓
remote HIGH provider
```

---

## 27. Token/context economy

The priority order should not simply be "use cheaper model".

Recommended order:

```text
1. Avoid LLM where deterministic tools work.
2. Avoid moving context at all; pass references.
3. Minimize/limit context if materialization is required.
4. Minimize exposed tools and skills.
5. Use local inference where appropriate.
6. Use cheaper cloud/API tier when quality/risk allow.
```

Examples of work that should not require LLM:

- scope guard;
- hash comparison;
- schema validation;
- file change detection;
- AST/dependency extraction where tooling exists;
- deterministic diff checks.

Principle:

> Tool first, tokens second.

---

## 28. Skill and tool progressive disclosure

Workers should not receive the full skill/tool catalog.

Task path:

```text
Task
 ↓
Domain Router
 ↓
Skill Router
 ↓
relevant skills only
 ↓
Tool Broker
 ↓
relevant tools only
 ↓
Context Compiler
 ↓
Worker
```

This reduces:

- prompt size;
- tool-schema size;
- confusion;
- accidental tool usage.

---

## 29. Tool Broker

Add a generic tool routing/broker component.

One capability may be reachable through:

```text
native API
MCP
CLI
local library
```

Domain asks for the capability, not the transport.

Example:

```text
Domain:
  github.issue.read

        ↓

Tool Broker

 ┌──────┼──────┐
 ▼      ▼      ▼
Native MCP    CLI
```

Policy chooses the allowed route.

---

## 30. MCP placement

MCP should live in integrations, not in Core/Coworker business logic.

Suggested structure:

```text
integrations/mcp/
├── client/
├── server/
├── registry/
└── gateway/
```

Roles:

### MCP client
KAT consumes external MCP servers.

### MCP server
KAT exposes selected capabilities to external environments.

### Registry
Tracks approved servers/capabilities/trust/auth/version.

### Gateway
Applies:

```text
request
 ↓
authentication
 ↓
permissions
 ↓
schema validation
 ↓
policy
 ↓
tool invocation
 ↓
sanitized result
```

Internal monolith modules should normally use typed/internal calls.

MCP is most useful when crossing:

```text
process boundary
machine boundary
product boundary
```

Do not turn every internal KAT module call into MCP; that would recreate distributed-system overhead inside the monolith.

---

## 31. MCP as resolver/transport, not source-of-truth

MCP fits naturally into Resource Fabric:

```text
ContextRef
 ↓
Resolver Registry
 ├── Native connector
 ├── MCP
 ├── GitHub API
 ├── Google Drive API
 └── Local FS
```

Similarly, Coworker tasks may later be transported over MCP, but the KAT-native task contract should remain the stable internal SSoT.

Pattern:

```text
KAT CoworkerTask
        │
        ├── local adapter
        ├── GitHub adapter
        ├── remote adapter
        └── MCP adapter
```

MCP is a transport/adapter, not the core task model.

---

## 32. Security order

Economy must come after hard security/policy constraints.

Routing order:

```text
1. Security classification
2. Hard Rules
3. Required capabilities
4. Minimum quality floor
5. Data locality/privacy
6. Available providers/models
7. Connector/source affinity
8. Cost optimization
9. Latency optimization
10. Final route
```

Never:

```text
choose cheapest
→ then see if it is safe
```

A local/cheap classifier may propose a route, but cannot lower a policy-enforced minimum.

---

## 33. Telemetry and cost evidence

Add telemetry for both quality and economic routing.

Example:

```text
InferenceEvidence
├── task_id
├── stage
├── provider
├── model
├── intelligence_tier
├── economic_class
├── input_tokens
├── output_tokens
├── cached_tokens
├── transfer_size
├── latency
├── estimated_cost
├── retries
├── escalations
└── result_quality
```

This allows future learning such as:

- which tasks truly require HIGH;
- which work can move to local;
- which connectors reduce transfer;
- which providers are overloaded;
- which routes fail more often.

---

## 34. Task budgets

A task may carry a budget:

```text
TaskBudget
├── max_cloud_tokens
├── max_high_calls
├── max_cost
├── max_duration
└── local_preferred
```

For subscription providers, token cost pressure may be low, but usage/rate/availability constraints still matter.

---

## 35. End-to-end conceptual architecture

```text
                         USER
                          │
              ┌───────────▼───────────┐
              │     PERSONAL LAYER    │
              │ Rules/Prefs/Settings  │
              └───────────┬───────────┘
                          │
                          ▼
                       CORE
                          │
                          ▼
                       DOMAIN
                          │
                          ▼
                   RESOURCE FABRIC
             "Where is the context/result?"
                          │
        ┌─────────────────┼─────────────────┐
        ▼                 ▼                 ▼
     GitHub             Drive          Knowledge
        │                 │                 │
        └─────────────────┬─────────────────┘
                          │ refs
                          ▼
                  CONTEXT ENGINE
             select references / scope
                          │
                          ▼
                  PROVIDER ROUTER
                          │
          ┌───────────────┼────────────────┐
          ▼               ▼                ▼
  Subscription Seat    Local AI      Metered API
          │
          ▼
       COWORKER
  choose worker / endpoint
          │
          ▼
       EXECUTION
          │
          ▼
      TOOL BROKER
   Native / MCP / CLI
          │
          ▼
       ResultSink
  PR / Issue / Drive / Artifact
          │
          ▼
       ResultRef
          │
          ▼
         KAT
```

---

## 36. Proposed repository shape

```text
KAT9I/
│
├── core/
│   ├── tasks/
│   ├── contracts/
│   ├── rules/
│   ├── skills/
│   ├── routing/
│   ├── policy/
│   └── learning/
│
├── context/
│   ├── references/
│   ├── resolver/
│   ├── scopes/
│   ├── manifests/
│   ├── retrieval/
│   ├── compression/
│   ├── summaries/
│   ├── context_cache/
│   ├── context_packs/
│   └── materializer/
│
├── resources/
│   ├── registry/
│   ├── refs/
│   ├── resolvers/
│   ├── sinks/
│   ├── permissions/
│   ├── provenance/
│   └── cache/
│
├── inference/
│   ├── router/
│   ├── model_registry/
│   ├── provider_registry/
│   ├── capability_matrix/
│   ├── budget/
│   ├── escalation/
│   └── providers/
│       ├── local/
│       ├── api/
│       ├── seat/
│       │   ├── chatgpt/
│       │   ├── antigravity/
│       │   └── other/
│       └── remote_kat/
│
├── coworker/
│   ├── coordinator/
│   ├── worker_registry/
│   ├── discovery/
│   ├── capabilities/
│   ├── scheduler/
│   ├── claims/
│   ├── leases/
│   ├── delegation/
│   ├── messaging/
│   ├── handoff/
│   ├── presence/
│   ├── local/
│   ├── remote/
│   └── federation/
│
├── execution/
│   ├── workers/
│   ├── runtime/
│   ├── processes/
│   ├── worktrees/
│   ├── leases/
│   ├── evidence/
│   ├── scope_guard/
│   ├── timeouts/
│   └── cleanup/
│
├── security/
│   ├── identity/
│   ├── permissions/
│   ├── sensitive_data/
│   ├── scope_guard/
│   └── containment/
│
├── integrations/
│   ├── github/
│   ├── git/
│   ├── filesystem/
│   ├── google_drive/
│   ├── antigravity/
│   ├── codex/
│   ├── agy/
│   ├── mcp/
│   │   ├── client/
│   │   ├── server/
│   │   ├── registry/
│   │   └── gateway/
│   └── tool_broker/
│
├── domains/
│   ├── software_delivery/
│   │   ├── issue_to_pr/
│   │   ├── pr_review/
│   │   ├── qa/
│   │   ├── release/
│   │   └── roadmap/
│   ├── repository_optimization/
│   ├── suno/
│   ├── research/
│   ├── documents/
│   ├── engineering/
│   └── automation/
│
├── personal/
│   ├── profile/
│   ├── rules/
│   ├── preferences/
│   ├── settings/
│   ├── knowledge/
│   └── workspaces/
│
├── telemetry/
│   ├── execution/
│   ├── inference/
│   ├── cost/
│   └── quality/
│
└── tests/
    ├── unit/
    ├── integration/
    └── e2e/
```

---

## 37. Main architectural invariants

1. **Modular monolith, not an unstructured monolith.**
2. **One repository/release/CI, strict internal boundaries.**
3. **KAT is control plane, not bulk data transport.**
4. **Reference-first context and result exchange.**
5. **Materialize context only as fallback.**
6. **ResourceRef says what; Connector says how.**
7. **Domain owns domain semantics.**
8. **Core owns generic task/rule/skill/policy semantics.**
9. **Coworker chooses who; Execution runs how.**
10. **Provider Router chooses intelligence/provider route.**
11. **LOW/NORMAL/HIGH apply per stage, not per whole task.**
12. **Subscription seats are valid provider routes distinct from metered APIs.**
13. **Local AI is a first-class provider.**
14. **MCP is an integration/transport boundary, not internal architecture SSoT.**
15. **Tools/skills/context use progressive disclosure.**
16. **Deterministic tools should replace LLM calls where possible.**
17. **Security/rules define hard floors before economy.**
18. **Independent QA is enforceable workflow policy.**
19. **Personal Knowledge, Rules, Preferences and Settings are separate concepts.**
20. **Physical personal knowledge remains outside the product Git repository.**
21. **Results should be written to shared sinks and returned as ResultRef.**
22. **Telemetry measures quality, execution and economic routing.**
23. **AG25 functionality is redistributed into correct internal modules rather than duplicated.**
24. **Suno is a domain application, not execution infrastructure.**

---

## 38. Current design status

This file captures the architecture discussion only.

Not yet decided/implemented:

- exact programming language/package boundaries;
- concrete TaskContract schema;
- concrete ResourceRef / ContextRef / ResultRef schema;
- concrete ProviderRoute scoring formula;
- exact subscription-seat adapter mechanism per provider;
- exact MCP exposure surface;
- storage backend for personal rules/preferences/settings;
- migration plan from canonical KAT9I + AG25;
- compatibility strategy during migration;
- first minimal executable vertical slice;
- exact GitHub governance/branch-protection policy for KAT9I_OS.

The recommended next design step is to turn this architecture context into:

1. architecture decision records (ADRs);
2. a minimal repository skeleton;
3. canonical contracts;
4. a migration plan;
5. one real vertical slice such as:
   `GitHub Issue → ContextRefs → ProviderRoute → Coworker → Worker → PR ResultRef → independent QA`.
