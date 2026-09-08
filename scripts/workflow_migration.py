# -*- coding: utf-8 -*-
"""
Управление версионированием Workflow и детерминированной миграцией состояния длительных задач (Issue #52, Gate G5).

Архитектурные свойства:
1. Каждая длительная задача привязана к точному `workflow_id` и `workflow_version` (SemVer).
2. Классификация изменений между версиями Workflow:
   - FULLY_COMPATIBLE: минорные/патч обновления без изменения структуры шагов. Состояние продолжается без трансформаций.
   - REQUIRES_STATE_MIGRATION: совместимое изменение структуры состояния (добавление дефолтных полей, реструктуризация переменных).
     Применяется версионированная идемпотентная функция миграции (`StateMigration`).
   - BREAKING_INCOMPATIBLE: мажорное несовместимое изменение графа (удаление текущего шага, смена семантики переходов).
     Продолжение категорически запрещено (Fail-Closed); задача переводится в `BLOCKED` с аудитом.
3. Идемпотентность миграций:
   - Повторный запуск мигратора на уже мигрированном состоянии возвращает статус `SKIPPED_IDEMPOTENT` без искажения данных.
4. Обязательный аудит и Evidence:
   - Каждая применённая миграция формирует машинную запись по схеме `StateMigration.json`.
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMAS_V1_DIR = REPO_ROOT / "schemas" / "v1"


class WorkflowIncompatibleError(RuntimeError):
    """Несовместимое изменение версии Workflow, блокирующее автоматическое продолжение задачи."""
    pass


class WorkflowMigrationEngine:
    """Детерминированный движок проверки совместимости версий и миграции состояния Workflow."""

    def __init__(self):
        schema_path = SCHEMAS_V1_DIR / "StateMigration.json"
        with open(schema_path, "r", encoding="utf-8") as f:
            self.migration_schema = json.load(f)
        self.validator = Draft202012Validator(self.migration_schema)

        # Реестр зарегистрированных миграторов состояния: (workflow_id, from_ver, to_ver) -> handler
        self._migrators: Dict[Tuple[str, str, str], Callable[[Dict[str, Any]], Tuple[Dict[str, Any], List[str]]]] = {}

    def register_migrator(
        self,
        workflow_id: str,
        source_version: str,
        target_version: str,
        handler: Callable[[Dict[str, Any]], Tuple[Dict[str, Any], List[str]]]
    ):
        """Регистрирует детерминированную функцию миграции между двумя версиями."""
        self._migrators[(workflow_id, source_version, target_version)] = handler

    def classify_compatibility(
        self,
        workflow_id: str,
        source_version: str,
        target_version: str
    ) -> str:
        """
        Классифицирует совместимость между исходной и целевой версией Workflow.
        Основано на SemVer и наличии зарегистрированного пути миграции.
        """
        if source_version == target_version:
            return "FULLY_COMPATIBLE"

        # Разбиваем на major, minor, patch
        try:
            s_maj, s_min, s_patch = [int(x) for x in source_version.split(".")[:3]]
            t_maj, t_min, t_patch = [int(x) for x in target_version.split(".")[:3]]
        except Exception:
            return "BREAKING_INCOMPATIBLE"

        # Мажорное изменение без явного мигратора всегда несовместимо
        if t_maj > s_maj and (workflow_id, source_version, target_version) not in self._migrators:
            return "BREAKING_INCOMPATIBLE"

        # Если есть явный зарегистрированный мигратор
        if (workflow_id, source_version, target_version) in self._migrators:
            return "REQUIRES_STATE_MIGRATION"

        # Если major совпадает, а target >= source
        if t_maj == s_maj:
            if (t_min, t_patch) >= (s_min, s_patch):
                return "FULLY_COMPATIBLE"
            else:
                # Даунгрейд версии Workflow не допускается без мигратора
                return "BREAKING_INCOMPATIBLE"

        return "BREAKING_INCOMPATIBLE"

    def migrate_task_state(
        self,
        task_id: str,
        workflow_id: str,
        current_state: Dict[str, Any],
        target_version: str,
        evidence_ref: str = "artifacts/migrations/evidence.json"
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Выполняет проверку совместимости и детерминированную миграцию состояния.
        Возвращает (новое_состояние, запись_StateMigration).
        """
        source_version = current_state.get("workflow_version", "1.0.0")

        # Проверка идемпотентности: состояние уже на целевой версии
        if source_version == target_version:
            migration_record = {
                "migration_id": f"mig-{uuid.uuid4().hex[:12]}",
                "task_id": task_id,
                "workflow_id": workflow_id,
                "source_version": source_version,
                "target_version": target_version,
                "compatibility_class": "FULLY_COMPATIBLE",
                "migration_status": "SKIPPED_IDEMPOTENT",
                "applied_operations": [],
                "evidence_ref": evidence_ref,
                "migrated_at": datetime.now(timezone.utc).isoformat()
            }
            self.validator.validate(migration_record)
            return current_state, migration_record

        compat_class = self.classify_compatibility(workflow_id, source_version, target_version)

        # Несовместимое изменение: Fail-Closed блокировка
        if compat_class == "BREAKING_INCOMPATIBLE":
            migration_record = {
                "migration_id": f"mig-{uuid.uuid4().hex[:12]}",
                "task_id": task_id,
                "workflow_id": workflow_id,
                "source_version": source_version,
                "target_version": target_version,
                "compatibility_class": "BREAKING_INCOMPATIBLE",
                "migration_status": "BLOCKED_INCOMPATIBLE",
                "applied_operations": [],
                "evidence_ref": evidence_ref,
                "migrated_at": datetime.now(timezone.utc).isoformat()
            }
            self.validator.validate(migration_record)
            raise WorkflowIncompatibleError(
                f"Workflow migration rejected: incompatible change from {source_version} to {target_version} "
                f"for workflow '{workflow_id}' in task '{task_id}' without valid migration path"
            )

        # Полностью совместимое изменение: обновление метки версии
        if compat_class == "FULLY_COMPATIBLE":
            new_state = dict(current_state)
            new_state["workflow_version"] = target_version
            migration_record = {
                "migration_id": f"mig-{uuid.uuid4().hex[:12]}",
                "task_id": task_id,
                "workflow_id": workflow_id,
                "source_version": source_version,
                "target_version": target_version,
                "compatibility_class": "FULLY_COMPATIBLE",
                "migration_status": "APPLIED",
                "applied_operations": ["UPGRADE_VERSION_TAG"],
                "evidence_ref": evidence_ref,
                "migrated_at": datetime.now(timezone.utc).isoformat()
            }
            self.validator.validate(migration_record)
            return new_state, migration_record

        # Требуется трансформация состояния через зарегистрированный мигратор
        key = (workflow_id, source_version, target_version)
        migrator = self._migrators.get(key)
        if not migrator:
            raise WorkflowIncompatibleError(f"Missing registered state migrator for {key}")

        transformed_state, ops = migrator(current_state)
        transformed_state["workflow_version"] = target_version

        migration_record = {
            "migration_id": f"mig-{uuid.uuid4().hex[:12]}",
            "task_id": task_id,
            "workflow_id": workflow_id,
            "source_version": source_version,
            "target_version": target_version,
            "compatibility_class": "REQUIRES_STATE_MIGRATION",
            "migration_status": "APPLIED",
            "applied_operations": ops,
            "evidence_ref": evidence_ref,
            "migrated_at": datetime.now(timezone.utc).isoformat()
        }
        self.validator.validate(migration_record)
        return transformed_state, migration_record
