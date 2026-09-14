# QUEUE-GUARD Protocol

## Поток

ROADMAP
↓
READY
↓
QUEUE
↓
WORKER
↓
QA (AGY)
↓
MTD
↓
DONE

## Перед передачей WORKER

Обязательно:
- Issue существует;
- понятна цель;
- есть критерий готовности;
- назначен исполнитель;
- нет незакрытого блокера.

## Базовое правило

Один Worker = один активный ChangeSet.
Параллельные изменения одной области запрещены.

## Merge authority

`QUEUE-GUARD` является обязательной точкой допуска к merge. Наличие зелёного CI, положительного текста в PR body, старого QA PASS или технической возможности нажать GitHub Merge само по себе не даёт merge authority.

Прямой merge, который обходит действующий QUEUE-GUARD/evidence lifecycle, считается governance violation.

## Exact candidate snapshot

Перед переходом ChangeSet в merge-ready состояние Controller фиксирует как минимум:

- `candidate_head` — полный exact SHA текущего PR HEAD;
- `expected_base` — полный exact SHA целевой base branch;
- required CI/check/status evidence именно для `candidate_head`;
- независимый Antigravity QA evidence именно для `candidate_head`;
- состояние review threads: unresolved blocking threads = 0;
- действующий Evidence Epoch по `QA_PROTOCOL.md`.

Текстовые SHA внутри comments/reviews не заменяют системные GitHub metadata.

## Race check

После сбора qualifying evidence и непосредственно перед merge Controller повторно читает live PR metadata и base.

Merge запрещён, если изменилось хотя бы одно из следующего:

- PR HEAD;
- expected base SHA;
- review/gate/policy evidence, которое квалифицирует ChangeSet;
- появился новый unresolved blocking review thread.

HEAD/base drift возвращает ChangeSet в соответствующее состояние повторной проверки. Старый merge-ready snapshot нельзя переносить на новую пару HEAD/base.

## Governed merge

Разрешённый merge должен быть привязан к expected candidate HEAD и выполняться только после успешной проверки всей цепочки:

`Issue → exact HEAD → exact base → CI → AGY QA → QA-ACCEPT/Evidence Epoch → zero blocking threads → live race recheck → governed merge`.

Если транспорт merge поддерживает expected-head compare-and-swap, он обязателен. Проверка expected base выполняется перед side effect; изменение base после snapshot запрещает использование старого допуска.

После merge выполняется post-merge verification целевой ветки. Только после этого карточка может перейти в DONE и рабочая ветка может быть удалена по MTD.

## Donor provenance

При переносе механизмов из donor-репозиториев действует `docs/context/DONOR_PROMOTION_PROTOCOL.md`: donor-код не получает authority автоматически, а любой более слабый donor-control не может понизить KAT9I governance.
