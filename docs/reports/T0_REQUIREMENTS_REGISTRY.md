# T0 — полный Requirements Registry KAT9I_OS

## Назначение

T0 материализует inventory/traceability для следующей ABC/XYZ-классификации. Реестр не заменяет канонические SSoT и не принимает архитектурные решения.

- Baseline current main: `c2b15c87b7310c1b26e79d2088a2be3137ba13d5`.
- Requirements: **50**.
- Findings/gaps: **18**.
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

## Зарегистрированные findings

- `CONTRACT_GAP`: 16
- `CONTRADICTION`: 1
- `TRACEABILITY_GAP`: 1

Ключевые findings остаются DATA для последующего convergence: неверная Execution→§27.14 traceability-ссылка, противоречие §32.45 с принятым ADR-034, а также отсутствующие физические схемы устойчивых контрактов.

## OQ-010

OQ-010 уже закрыт в current main как **ACCEPTED / ADR-047** после merge PR #123 (`c2b15c87b7310c1b26e79d2088a2be3137ba13d5`). Реестр фиксирует этот канонический статус; pending-кандидатом он больше не считается.

## Исправления после review

- добавлена явная Requirement-связь для §20 Task Lifecycle;
- `canonical_ssot` нормализован до одной разрешимой ссылки, дополнительные ссылки вынесены в `supporting_refs`;
- составные canonical owners устранены;
- `REQ-TASKGRAPH-001` сохраняет принятый Requirement status, а отсутствие схемы отражается только через `CONTRACT_GAP`;
- coverage↔gap-kind проверяется детерминированно;
- полнота canonical source→Requirement linkage проверяется тестом.

## DoD T0

T0 готов к независимому QA только если JSON Schema валидна, все ссылки/IDs/dependencies разрешаются, все перечисленные инварианты проходят локальные тесты и полный Quality Gate на exact HEAD.
