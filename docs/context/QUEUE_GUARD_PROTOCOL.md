# Протокол QUEUE-GUARD

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
OWNER `mtd`
↓
SYNTHETIC INTEGRATION
↓
FINAL GATES
↓
MERGE
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

## Полномочие на merge

`QUEUE-GUARD` является обязательной точкой допуска к merge. Зелёный CI, положительный текст в PR, старый QA PASS или техническая возможность нажать GitHub Merge сами по себе не дают полномочия на merge.

Прямой merge в обход действующего `QUEUE-GUARD`, Evidence lifecycle или Owner Gate считается нарушением governance.

## Проверка ChangeSet до Owner Gate

До запроса у владельца команды `mtd` Controller фиксирует и проверяет как минимум:

- `candidate_head` — полный SHA текущего PR HEAD;
- `expected_base` — полный SHA текущей целевой ветки;
- обязательные CI/check/status результаты для `candidate_head`;
- независимый Antigravity QA для проверенного ChangeSet;
- отсутствие нерешённых блокирующих review threads;
- действующий `EVIDENCE_EPOCH` по `QA_PROTOCOL.md`;
- отсутствие drift между собранным Evidence и текущим PR.

Текстовый SHA в comment/review не заменяет системные GitHub metadata.

Изменение PR HEAD инвалидирует доказательства, привязанные к прежнему HEAD, если их применимость к новому ChangeSet не доказана по действующему QA-протоколу. Изменение base не даёт права автоматически использовать старое Integration Evidence.

## Owner Gate `mtd`

Явная команда владельца `mtd` является разрешением перейти к финальной интеграционной фазе. Она не означает немедленный merge и не заменяет финальные проверки.

До `mtd` запрещено выдавать synthetic integration candidate за финально допущенный к merge объект.

## Synthetic integration candidate

После `mtd` Controller строит или получает synthetic integration candidate из точной пары:

- текущий проверенный PR HEAD;
- текущий SHA целевой base branch.

Финальный CI и интеграционные проверки выполняются на этом synthetic candidate согласно канону проекта. Именно результат интеграции с текущим target, а не один PR HEAD, является финальным техническим кандидатом на merge.

Если PR HEAD или base SHA изменились после построения synthetic candidate, этот candidate становится устаревшим и должен быть пересоздан. Старые финальные результаты нельзя переносить на новую пару HEAD/base без нового доказательства применимости.

## Финальная проверка перед side effect

Непосредственно перед merge Controller повторно читает live PR metadata и target branch и подтверждает:

- PR HEAD совпадает с HEAD, из которого построен synthetic candidate;
- base SHA совпадает с base, из которого построен synthetic candidate;
- финальные обязательные проверки synthetic candidate успешны;
- QA/Policy/Gate Evidence остаётся применимым и действующим;
- нерешённых блокирующих review threads нет;
- Owner Gate `mtd` относится к текущему ChangeSet и не был инвалидирован изменением области работ.

Любой drift возвращает ChangeSet в соответствующую фазу повторной проверки.

## Управляемый merge

Разрешённая последовательность:

`Issue → exact PR HEAD → pre-merge CI → AGY QA → Evidence → zero blocking threads → Owner mtd → exact current base + checked ChangeSet → synthetic integration candidate → final CI/gates → live race recheck → governed merge → post-merge verification`.

Если merge transport поддерживает compare-and-swap по expected HEAD, он обязателен. Expected base проверяется перед side effect. Прямой merge, минующий эту последовательность, запрещён.

После merge выполняется post-merge verification целевой ветки. Только после успешной проверки карточка может перейти в DONE, а рабочая ветка — быть удалена по MTD.

## Происхождение donor-решений

При переносе механизмов из внешних репозиториев действует `docs/context/DONOR_PROMOTION_PROTOCOL.md`: donor-код не получает полномочия автоматически, а более слабый donor-control не может понизить действующий KAT9I governance.
