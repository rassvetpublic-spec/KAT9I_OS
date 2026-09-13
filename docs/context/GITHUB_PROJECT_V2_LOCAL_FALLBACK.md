# GitHub Project v2 — локальный operator fallback

## Назначение

Этот fallback используется, если ChatGPT/GitHub connector видит Issues/PR, но не предоставляет Project v2 read/write actions.

Он не меняет SSoT и не даёт дополнительных прав merge.

## Проверенная схема доступа

На локальном ПК владельца GitHub CLI (`gh`) может работать с Projects v2 через обычную авторизацию пользователя.

Требуемый принцип:

- авторизация хранится локально в credential store;
- токен не копируется в чат, Issue, PR, лог или репозиторий;
- должны присутствовать права на repository и project operations;
- при отсутствии write Project scope разрешён только audit/read-only режим.

Проверенный Project KAT9I_OS:

- owner: `rassvetpublic-spec`;
- project number: `2`;
- Project node ID: `PVT_kwHODnXDgM4Bi0YJ`.

## Audit-first

Перед любой mutation локальный Operator сначала сохраняет read-only snapshot:

- Project metadata;
- items;
- fields/options;
- при необходимости views/layout через GraphQL.

Снимок используется только как Evidence текущего состояния; динамические counts карточек/полей не являются вечным каноном.

## Fallback layers

1. `gh project` для Project metadata, items и fields.
2. `gh api graphql` для возможностей Project v2, которых нет в удобных CLI subcommands, например views/layout.
3. При недоступности GraphQL — audit-only; нельзя притворяться, что repair выполнен.

## Mutations

- сначала полный semantic preflight;
- затем bounded mutation только ожидаемых объектов;
- неизвестные/дублирующиеся fields/views/options → fail-closed;
- после каждой серии mutations обязателен read-back;
- repair не создаёт QA PASS, Gate PASS или merge authority.

## Связь с автоматизацией

Repo-side production automation остаётся предпочтительным воспроизводимым механизмом. Локальный fallback нужен как operator path для доступа к Project v2 и диагностики, когда connector/UI не экспонирует нужные действия.
