# -*- coding: utf-8 -*-
"""
Тесты версионирования Workflow и детерминированной миграции состояния (Issue #52, Gate G5).

Проверяет:
1. Валидность схемы StateMigration.json по стандарту Draft 2020-12.
2. Сценарий 1: Пауза задачи -> Совместимое обновление Workflow (minor/patch) ->
   автоматическое продолжение без изменения данных (APPLIED / FULLY_COMPATIBLE).
3. Сценарий 2: Пауза задачи -> Обновление структуры схемы состояния с мигратором ->
   успешная детерминированная трансформация данных (APPLIED / REQUIRES_STATE_MIGRATION).
4. Сценарий 3: Идемпотентность миграции ->
   повторное применение миграции к уже обновленному состоянию возвращает SKIPPED_IDEMPOTENT без искажения полей.
5. Сценарий 4: Пауза задачи -> Несовместимое мажорное обновление Workflow без пути миграции ->
   блокировка выполнения (WorkflowIncompatibleError / Fail-Closed, BLOCKED_INCOMPATIBLE).
6. Проверка генерации Evidence и аудиторских записей.
"""

import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from scripts.workflow_migration import WorkflowMigrationEngine, WorkflowIncompatibleError

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMAS_V1_DIR = REPO_ROOT / "schemas" / "v1"


class TestWorkflowVersioningMigration(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.engine = WorkflowMigrationEngine()
        schema_path = SCHEMAS_V1_DIR / "StateMigration.json"
        cls.assertTrue(cls, schema_path.exists(), "StateMigration.json отсутствует")
        with open(schema_path, "r", encoding="utf-8") as f:
            cls.schema = json.load(f)
        cls.validator = Draft202012Validator(cls.schema)

    def test_schema_validity(self):
        """Проверяет соответствие схемы StateMigration.json стандарту Draft 2020-12."""
        Draft202012Validator.check_schema(self.schema)
        self.assertFalse(self.schema.get("additionalProperties", True))
        self.assertEqual(self.schema.get("version"), "1.0.0")

    def test_compatible_minor_upgrade_allows_resume(self):
        """
        Сценарий 1: Задача на паузе с Workflow 1.0.0.
        Workflow обновлен до 1.1.0 (совместимое добавление функционала).
        Продолжение разрешено без изменения пользовательских переменных.
        """
        initial_state = {
            "task_id": "task-wf-001",
            "workflow_id": "wf-code-review",
            "workflow_version": "1.0.0",
            "current_step": "step-lint",
            "variables": {"target_dir": "src/"}
        }

        new_state, record = self.engine.migrate_task_state(
            task_id="task-wf-001",
            workflow_id="wf-code-review",
            current_state=initial_state,
            target_version="1.1.0"
        )

        self.validator.validate(record)
        self.assertEqual(record["compatibility_class"], "FULLY_COMPATIBLE")
        self.assertEqual(record["migration_status"], "APPLIED")
        self.assertEqual(new_state["workflow_version"], "1.1.0")
        self.assertEqual(new_state["variables"]["target_dir"], "src/")

    def test_state_migration_with_registered_transformer(self):
        """
        Сценарий 2: Workflow 1.0.0 -> 2.0.0 требует реструктуризации переменных:
        `variables.target_dir` преобразуется в список `variables.target_paths`.
        """
        engine = WorkflowMigrationEngine()

        def v1_to_v2_migrator(state: dict):
            new_s = dict(state)
            new_vars = dict(state.get("variables", {}))
            old_dir = new_vars.pop("target_dir", None)
            if old_dir:
                new_vars["target_paths"] = [old_dir]
            new_vars["strict_mode"] = True
            new_s["variables"] = new_vars
            return new_s, ["CONVERT_TARGET_DIR_TO_LIST", "SET_STRICT_MODE_DEFAULT"]

        engine.register_migrator("wf-code-review", "1.0.0", "2.0.0", v1_to_v2_migrator)

        initial_state = {
            "task_id": "task-wf-002",
            "workflow_id": "wf-code-review",
            "workflow_version": "1.0.0",
            "current_step": "step-analyze",
            "variables": {"target_dir": "lib/"}
        }

        new_state, record = engine.migrate_task_state(
            task_id="task-wf-002",
            workflow_id="wf-code-review",
            current_state=initial_state,
            target_version="2.0.0"
        )

        self.validator.validate(record)
        self.assertEqual(record["compatibility_class"], "REQUIRES_STATE_MIGRATION")
        self.assertEqual(record["migration_status"], "APPLIED")
        self.assertEqual(record["applied_operations"], ["CONVERT_TARGET_DIR_TO_LIST", "SET_STRICT_MODE_DEFAULT"])
        self.assertEqual(new_state["workflow_version"], "2.0.0")
        self.assertEqual(new_state["variables"]["target_paths"], ["lib/"])
        self.assertTrue(new_state["variables"]["strict_mode"])

    def test_migration_idempotency_safe_rerun(self):
        """
        Сценарий 3: Идемпотентность. Повторный запуск мигратора на уже обновленном состоянии
        не выполняет повторных трансформаций и возвращает SKIPPED_IDEMPOTENT.
        """
        already_migrated_state = {
            "task_id": "task-wf-003",
            "workflow_id": "wf-code-review",
            "workflow_version": "2.0.0",
            "current_step": "step-analyze",
            "variables": {"target_paths": ["core/"]}
        }

        new_state, record = self.engine.migrate_task_state(
            task_id="task-wf-003",
            workflow_id="wf-code-review",
            current_state=already_migrated_state,
            target_version="2.0.0"
        )

        self.validator.validate(record)
        self.assertEqual(record["migration_status"], "SKIPPED_IDEMPOTENT")
        self.assertEqual(record["applied_operations"], [])
        self.assertEqual(new_state["variables"]["target_paths"], ["core/"])

    def test_incompatible_major_upgrade_blocks_resume_fail_closed(self):
        """
        Сценарий 4: Workflow 1.0.0 -> 3.0.0 без зарегистрированного мигратора.
        Политика Fail-Closed: автоматическое возобновление блокируется с ошибкой WorkflowIncompatibleError.
        """
        initial_state = {
            "task_id": "task-wf-incompatible",
            "workflow_id": "wf-critical-deploy",
            "workflow_version": "1.0.0",
            "current_step": "step-deploy"
        }

        with self.assertRaises(WorkflowIncompatibleError) as ctx:
            self.engine.migrate_task_state(
                task_id="task-wf-incompatible",
                workflow_id="wf-critical-deploy",
                current_state=initial_state,
                target_version="3.0.0"
            )

        self.assertIn("incompatible change from 1.0.0 to 3.0.0", str(ctx.exception))
        self.assertIn("without valid migration path", str(ctx.exception))
