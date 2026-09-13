# T0 — полный Requirements Registry KAT9I_OS

## Назначение

T0 материализует inventory/traceability для следующей ABC/XYZ-классификации. Реестр не заменяет канонические SSoT и не принимает архитектурные решения.

- Inventory `baseline_revision`: `d28547da5286eb7f275a74449d88d398018de8e4` — revision, на которой сформирован и проверен Requirement inventory; последующее движение integration base само по себе не меняет ChangeSet.
- Current accepted integration main: `3388713fa0b5b7c47acbeebee53a1b889d0aed62` — post-G0 remediation/read-back PASS после PR #144; новых нормативных Requirement относительно inventory baseline не добавлено.
- Corrective implementation provenance: `2e7795fe3dbb47ad54ba6d4325be22d1131557b7`.
- Graveyard SSoT corrective provenance: `0252f888f8a0a32ddf1644fde284bda4a10aa9cc`.
- Final review correction provenance: `1fdac14d209daf1e7847a52cf0786e97439f1661` — закрывает 5 оставшихся traceability review findings после G0.
- Integrated G0 control-plane baseline: `d28547da5286eb7f275a74449d88d398018de8e4` (PR #133); последующие G0 repair-коммиты относятся к control-plane и не расширяют нормативный Requirement inventory T0.
- Requirements: **51**.
- Findings/gaps: **19**.
- ABC: `UNASSESSED` для всех Requirement.
- XYZ: `UNASSESSED` для всех Requirement.

## Инварианты T0

- один Requirement имеет ровно один `canonical_ssot`;
- дополнительные документы хранятся в `supporting_refs`;
- один Requirement имеет ровно одного `canonical_owner`;
- Requirement status отделён от `coverage_status`;
- любой non-COVERED Requirement связан с gap того же вида;
- каждый документ из `CANONICAL_SSoT` source inventory связан хотя бы с одним Requirement;
- логический owner не означает физическую materialization модуля;
- Graveyard остаётся DATA-only;
- T0 не назначает ABC/XYZ.

## Coverage snapshot

- `CONTRACT_GAP`: 18
- `CONTRADICTION`: 1
- `COVERED`: 30
- `TRACEABILITY_GAP`: 1
- `OWNER_GAP`: 1

## Зарегистрированные findings

- `OWNER_GAP`: 1
- `CONTRACT_GAP`: 16
- `CONTRADICTION`: 1
- `TRACEABILITY_GAP`: 1

Ключевые findings остаются DATA для последующего convergence: неверная Execution→§27.14 traceability-ссылка, противоречие §32.45 с принятым ADR-034, а также отсутствующие физические схемы устойчивых контрактов.

## OQ-010

OQ-010 уже закрыт в inventory baseline как **ACCEPTED / ADR-047** после merge PR #123 (`c2b15c87b7310c1b26e79d2088a2be3137ba13d5`). Реестр фиксирует этот канонический статус; pending-кандидатом он больше не считается.

## Исправления после review

- `QA_PROTOCOL.md` включён в canonical inventory и связан с отдельным Requirement control-plane QA-протокола;
- `machine_contract_refs` теперь содержат только literal разрешимые schema refs, wildcard запрещён regression-тестом;
- OQ-010 использует профильный §22 как canonical SSoT, §23/ADR-047 остаются supporting provenance;
- языковая политика фиксирует `OWNER_GAP` вместо создания несуществующего canonical owner;
- добавлена явная Requirement-связь для §20 Task Lifecycle;
- `canonical_ssot` нормализован до одной разрешимой ссылки, дополнительные ссылки вынесены в `supporting_refs`;
- составные canonical owners устранены;
- `REQ-TASKGRAPH-001` сохраняет принятый Requirement status, а отсутствие схемы отражается только через `CONTRACT_GAP`;
- coverage↔gap-kind проверяется детерминированно;
- полнота canonical source→Requirement linkage проверяется тестом;
- Graveyard DATA-only: `schemas/README.md#5` является canonical SSoT, а `graveyard/README.md` оставлен только supporting provenance.

## DoD T0

T0 готов к независимому QA только если JSON Schema валидна, все ссылки/IDs/dependencies разрешаются, все перечисленные инварианты проходят локальные тесты и полный Quality Gate на exact HEAD.
