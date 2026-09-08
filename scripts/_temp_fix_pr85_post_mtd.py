from pathlib import Path


def replace_once(path, old, new):
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected exactly 1 match, got {count}")
    p.write_text(text.replace(old, new), encoding="utf-8")

# 1) Security-aware spill policy in CacheEngine.
replace_once(
    "docs/architecture/34_CACHE_ENGINE.md",
    """Политика первой версии:\n\n1. дешёвые для повторного построения холодные записи удаляются;\n2. дорогие для повторного построения холодные записи собираются в batch;\n3. batch записывается одной крупной последовательной операцией в immutable spill segment;\n4. RAM освобождается;\n5. при последующем запросе нужный объект лениво возвращается в RAM.\n\nSSD используется как резерв ёмкости, а не как обязательное постоянное хранилище.\n""",
    """Политика первой версии:\n\n1. `NO_CACHE` вообще не принимается в CacheEngine;\n2. дешёвые для повторного построения холодные записи удаляются;\n3. дорогая запись сначала проходит `SpillPolicy` и Security-проверку места хранения, срока жизни, Scope и обязательного шифрования;\n4. `CACHE_SESSION_ONLY` в v1 не записывается на диск: при нехватке RAM такая запись остаётся в допустимой памяти либо удаляется и пересчитывается;\n5. `CACHE_LIMITED` допускается к spill только если политика явно разрешает локальный диск и все требования к шифрованию, расположению и retention выполнены; если требуемая защита не реализована или недоступна, запись не spill'ится;\n6. разрешённые дорогие холодные записи собираются в batch;\n7. batch записывается одной крупной последовательной операцией в immutable spill segment;\n8. RAM освобождается;\n9. при последующем запросе нужный объект лениво возвращается в RAM.\n\nSSD используется как резерв ёмкости, а не как обязательное постоянное хранилище. Memory pressure никогда не ослабляет Cache Policy или Security: безопаснее удалить пересоздаваемую запись, чем сохранить её в запрещённом месте.\n""",
)

replace_once(
    "docs/architecture/34_CACHE_ENGINE.md",
    """- policy: class/priority hints;\n- security: scope;\n- integrity: checksum;\n""",
    """- policy: cache_class (`CACHE_ALLOWED`, `CACHE_LIMITED`, `CACHE_SESSION_ONLY`), class/priority hints, spill_allowed, retention/session binding;\n- security: scope, storage/location restrictions, encryption_required;\n- integrity: checksum;\n""",
)

replace_once(
    "docs/architecture/34_CACHE_ENGINE.md",
    "Результат проверки повторного использования использует единый словарь состояний: `FULL`, `PARTIAL`, `MISS`, `STALE`, `FORBIDDEN`. Эти состояния описывают решение Cache Policy и не зависят от того, находится payload в RAM, spill segment или будущем backend.",
    "Результат проверки повторного использования использует единый словарь состояний: `FULL_HIT`, `PARTIAL_HIT`, `MISS`, `STALE`, `FORBIDDEN`. Эти состояния описывают решение Cache Policy и не зависят от того, находится payload в RAM, spill segment или будущем backend.",
)

replace_once(
    "docs/architecture/34_CACHE_ENGINE.md",
    """- batch spill;\n- immutable segments;\n- checksum;\n""",
    """- batch spill только после Cache Policy / Security gate;\n- immutable segments;\n- checksum;\n""",
)

replace_once(
    "docs/architecture/34_CACHE_ENGINE.md",
    """- весь cache storage повреждён → удалить и построить заново;\n- незавершённый temporary segment → удалить при старте.\n""",
    """- весь cache storage повреждён → удалить и построить заново;\n- незавершённый temporary segment → удалить при старте;\n- завершение задачи/сессии → гарантированно очистить все `CACHE_SESSION_ONLY` записи и связанные временные области.\n""",
)

# 2) Canonical responsibility map uses the existing serialized cache-result vocabulary.
replace_once(
    "docs/architecture/27_MODULE_REGISTRY_AND_RESPONSIBILITY_MAP.md",
    "Состояния `FULL`, `PARTIAL`, `MISS`, `STALE`, `FORBIDDEN` являются единым словарём результата Cache Policy. Они не означают конкретный backend хранения.",
    "Состояния `FULL_HIT`, `PARTIAL_HIT`, `MISS`, `STALE`, `FORBIDDEN` являются единым словарём результата Cache Policy. Они не означают конкретный backend хранения.",
)
replace_once(
    "docs/architecture/27_MODULE_REGISTRY_AND_RESPONSIBILITY_MAP.md",
    "Каноническое владение: Cache Policy, runtime Cache Registry, CacheKey/CacheEntry/PayloadRef и состояния FULL/PARTIAL/MISS/STALE/FORBIDDEN.",
    "Каноническое владение: Cache Policy, runtime Cache Registry, CacheKey/CacheEntry/PayloadRef и состояния FULL_HIT/PARTIAL_HIT/MISS/STALE/FORBIDDEN.",
)

# 3) Cache Policy explicitly owns placement rules and aligns module boundary.
replace_once(
    "docs/spec/13_CACHE_POLICY.md",
    """- `NO_CACHE` — сохранение запрещено.\n\nЗапрет кэширования имеет приоритет над разрешением.\n""",
    """- `NO_CACHE` — сохранение запрещено.\n\nЗапрет кэширования имеет приоритет над разрешением.\n\n## Размещение и spill\n\nКласс кэширования определяет не только возможность повторного использования, но и допустимое физическое размещение записи. Memory pressure не может ослаблять эти ограничения.\n\n- `NO_CACHE` не принимается в CacheEngine;\n- `CACHE_SESSION_ONLY` в первой реализации хранится только в допустимой оперативной памяти и полностью удаляется при завершении задачи/сессии;\n- `CACHE_LIMITED` может попасть на диск только при явном разрешении политики и выполнении всех требований по Scope, месту хранения, TTL/retention и шифрованию;\n- `CACHE_ALLOWED` может использовать RAM и разрешённый spill, если Security не задаёт более строгих ограничений.\n\nЕсли запись нельзя безопасно spill'ить, CacheEngine удаляет её и при необходимости пересчитывает позже. Производительность не имеет приоритета над Security.\n""",
)

replace_once(
    "docs/spec/13_CACHE_POLICY.md",
    "- Resources отвечает за физическое хранение, source revision, resolver cache и локальные копии;",
    "- Resources владеет ResourceRef, source revision и правилами разрешения источника; физическим размещением runtime cache и spill владеет CacheEngine;",
)

# 4) Compatible schema expansion gets a SemVer minor bump.
replace_once(
    "schemas/v1/ModuleRegistry.json",
    '  "version": "1.0.0",',
    '  "version": "1.1.0",',
)
