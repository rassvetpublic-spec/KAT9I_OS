# KAT9I_OS Donor Promotion Protocol

## Назначение

Этот протокол определяет, как KAT9I_OS принимает идеи, контракты и реализацию из внешних donor-репозиториев без создания второго SSoT и без ослабления текущего канона.

GitHub-канон KAT9I_OS всегда имеет приоритет над donor-кодом, donor-документацией и donor-release state.

## Обязательный pin

Любая donor-сессия начинается с фиксации:

- `repository`;
- exact donor commit SHA;
- source path;
- Git blob SHA, если доступен;
- exact KAT9I_OS baseline SHA;
- Issue, которая разрешает promotion.

Floating refs (`main`, `latest`, branch name без exact SHA) не являются достаточным доказательством происхождения.

## Классификация

Каждый признанный ценным donor-артефакт обязан получить ровно один статус:

- `PROMOTE_AS_CODE` — реализация переносится и становится KAT9I-кодом только после semantic diff, адаптации и собственных тестов;
- `PROMOTE_AS_CONTEXT` — переносится инвариант/контракт, а donor-код остаётся только provenance/evidence;
- `PRESERVE_AS_DONOR_REFERENCE` — ценность сохранена точным source/blob pin, но текущий канон уже эквивалентен или сильнее;
- `DEFER` — ценность подтверждена, но активация отложена до выполнения указанного gate;
- `REJECT_ANTIPATTERN` — сохраняется как отрицательное знание и запрещённый способ реализации.

Нельзя завершать promotion, если существует хотя бы один ценный элемент без классификации. Machine summary обязана содержать `unclassified_count = 0`.

## Semantic diff прежде копирования

Порядок принятия:

1. Сначала сравнить поведение и инварианты donor с текущим KAT9I canon.
2. Если KAT9I уже реализует эквивалентный или более сильный механизм, donor-код не дублируется.
3. Если donor добавляет полезный отсутствующий инвариант, сначала он формулируется в KAT9I contract/SSoT.
4. Код переносится только если существует подтверждённый implementation gap и не возникает параллельной authority-системы.
5. Любой порт получает собственные KAT9I tests/evidence; donor CI не считается доказательством KAT9I correctness.

## Запрет downgrade

Donor никогда не может отменять или ослаблять более сильные KAT9I controls. В частности, promotion не может обходить:

- `EVIDENCE_EPOCH`;
- anti-replay;
- Controller attestation;
- exact live HEAD checks;
- stale-evidence invalidation;
- independent Antigravity QA;
- Owner/MTD gate;
- QUEUE-GUARD.

Если donor-механизм конфликтует с ними, сохраняется только совместимый инвариант, а конфликтующая реализация классифицируется `REJECT_ANTIPATTERN` или `DEFER`.

## Merge authority

Donor promotion проходит обычный ChangeSet lifecycle. Перед MTD обязательны:

- linked Issue;
- exact candidate HEAD;
- exact expected base SHA;
- required CI/checks на candidate HEAD;
- независимый QA Evidence на candidate HEAD;
- zero unresolved blocking review threads;
- повторное чтение live PR metadata после сбора Evidence;
- отсутствие HEAD/base/evidence drift;
- governed merge с expected candidate HEAD; прямой merge в обход QUEUE-GUARD запрещён.

Изменение candidate HEAD или expected base после квалифицирующего snapshot инвалидирует merge-ready evidence до повторной проверки.

## Preservation manifest

Для каждой donor-сессии создаётся machine-readable manifest. Он является индексом решений и provenance, но не подменяет canonical architecture files.

Минимальные поля каждого элемента:

- stable id;
- source path(s);
- exact source/blob identity;
- ценность;
- classification;
- KAT9I destination или defer/reject reason;
- verification/evidence.

Критерий полноты: `inventory_count == classified_count` и `unclassified_count == 0`.

## Красный donor

Красный CI donor-репозитория не запрещает исследование или сохранение идей, но запрещает слепое объявление его runtime-модулей готовым KAT9I production code. Такой код допускается только через отдельный порт, собственные тесты и KAT9I QA.
