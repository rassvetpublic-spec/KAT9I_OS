# -*- coding: utf-8 -*-
"""
Тесты снимка семантического окружения (SemanticSnapshot) и правил Recovery / Resume (Issue #42, Gate G5).

Проверяет:
1. Валидность схемы SemanticSnapshot.json по Draft 2020-12.
2. Создание валидного снимка (Reference-first, хранение версий и хэшей без дублирования больших данных).
3. Штатный сценарий: окружение не изменилось -> RESUME_ALLOWED (Preflight успешен).
4. Критический сценарий 1: незаметная смена версии модели при одинаковом псевдониме (alias drift) ->
   обнаружение BREAKING_DRIFT, блокировка возобновления (SemanticDriftError / Fail-Closed).
5. Критический сценарий 2: изменение RulesRef (системных правил) во время паузы задачи ->
   обнаружение BREAKING_DRIFT, блокировка возобновления.
6. Критический сценарий 3: дрейф сигнатуры или удаление зарегистрированного инструмента ->
   обнаружение BREAKING_DRIFT, блокировка возобновления.
7. Неразрушающий дрейф (патч навыка) -> RESUME_WITH_AUDIT (продолжение с аудитом без падения).
8. Связь снимка с Evidence: возможность извлечь snapshot_id и точный контекст окружения выполнения.
"""

import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from scripts.semantic_isolation import SemanticIsolationGuard, SemanticDriftError

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMAS_V1_DIR = REPO_ROOT / "schemas" / "v1"


class TestSemanticIsolationRecovery(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.guard = SemanticIsolationGuard()
        schema_path = SCHEMAS_V1_DIR / "SemanticSnapshot.json"
        cls.assertTrue(cls, schema_path.exists(), "SemanticSnapshot.json отсутствует")
        with open(schema_path, "r", encoding="utf-8") as f:
            cls.schema = json.load(f)

    def _create_baseline_env(self) -> dict:
        """Вспомогательный конструктор эталонного семантического окружения."""
        return {
            "rules_ref": "canonical-v1.4-rules",
            "model_route": {
                "provider": "anthropic",
                "model_alias": "HIGH",
                "resolved_model_version": "claude-3-7-sonnet-20250219-v1.0",
                "temperature": 0.0,
                "prompt_template_revision": "sha256-prompt-template-v1"
            },
            "context_manifest_ref": "manifest-ctx-sha256-abc1234",
            "skill_revisions": {
                "git_operator": "rev-1.2.0",
                "code_auditor": "rev-2.0.1"
            },
            "tool_definitions": {
                "fs_read": "sha256-tool-schema-01",
                "git_commit": "sha256-tool-schema-02"
            },
            "config_revision": "cfg-rev-prod-2026",
            "contract_versions": {
                "TaskContract": "1.0.0",
                "TaskResult": "1.0.0",
                "Evidence": "1.0.0"
            }
        }

    def test_schema_validity(self):
        """Проверяет синтаксис SemanticSnapshot.json по Draft 2020-12."""
        Draft202012Validator.check_schema(self.schema)
        self.assertFalse(self.schema.get("additionalProperties", True))
        self.assertEqual(self.schema.get("version"), "1.0.0")

    def test_snapshot_creation_and_validation(self):
        """Проверяет создание корректного семантического снимка."""
        env = self._create_baseline_env()
        snapshot = self.guard.create_snapshot(
            task_id="task-sem-001",
            rules_ref=env["rules_ref"],
            provider=env["model_route"]["provider"],
            model_alias=env["model_route"]["model_alias"],
            resolved_model_version=env["model_route"]["resolved_model_version"],
            context_manifest_ref=env["context_manifest_ref"],
            skill_revisions=env["skill_revisions"],
            tool_definitions=env["tool_definitions"],
            config_revision=env["config_revision"],
            contract_versions=env["contract_versions"],
            prompt_template_revision=env["model_route"]["prompt_template_revision"]
        )
        self.assertTrue(snapshot["snapshot_id"].startswith("sem-"))
        self.assertEqual(snapshot["task_id"], "task-sem-001")

    def test_identical_environment_allows_resume(self):
        """Штатный сценарий: окружение после паузы идентично baseline -> RESUME_ALLOWED."""
        env = self._create_baseline_env()
        snapshot = self.guard.create_snapshot(
            task_id="task-resume-ok",
            rules_ref=env["rules_ref"],
            provider=env["model_route"]["provider"],
            model_alias=env["model_route"]["model_alias"],
            resolved_model_version=env["model_route"]["resolved_model_version"],
            context_manifest_ref=env["context_manifest_ref"],
            skill_revisions=env["skill_revisions"],
            tool_definitions=env["tool_definitions"],
            config_revision=env["config_revision"],
            contract_versions=env["contract_versions"],
            prompt_template_revision=env["model_route"]["prompt_template_revision"]
        )

        report = self.guard.verify_resume_preflight(snapshot, env)
        self.assertEqual(report["decision"], "RESUME_ALLOWED")
        self.assertEqual(report["policy_action"], "CONTINUE")
        self.assertFalse(report["has_breaking_drift"])

    def test_model_version_drift_blocks_resume(self):
        """
        Критический сценарий:
        Псевдоним HIGH остался тем же, но поставщик/версия модели изменилась
        (например, тихое обновление провайдера на новую ревизию).
        Возобновление обязано быть заблокировано (Fail-Closed).
        """
        env = self._create_baseline_env()
        snapshot = self.guard.create_snapshot(
            task_id="task-drift-model",
            rules_ref=env["rules_ref"],
            provider=env["model_route"]["provider"],
            model_alias=env["model_route"]["model_alias"],
            resolved_model_version=env["model_route"]["resolved_model_version"],
            context_manifest_ref=env["context_manifest_ref"],
            skill_revisions=env["skill_revisions"],
            tool_definitions=env["tool_definitions"],
            config_revision=env["config_revision"],
            contract_versions=env["contract_versions"],
            prompt_template_revision=env["model_route"]["prompt_template_revision"]
        )

        # Симулируем тихое изменение модели в окружении
        drifted_env = dict(env)
        drifted_env["model_route"] = dict(env["model_route"])
        drifted_env["model_route"]["resolved_model_version"] = "claude-3-7-sonnet-20250601-silent-v2.0"

        with self.assertRaises(SemanticDriftError) as ctx:
            self.guard.verify_resume_preflight(snapshot, drifted_env)

        self.assertIn("breaking semantic drift detected", str(ctx.exception))
        self.assertIn("model provider or exact version has drifted", str(ctx.exception))

    def test_rules_ref_drift_blocks_resume(self):
        """
        Критический сценарий:
        Во время паузы задачи системные правила (RulesRef) обновились.
        Задача не может продолжаться без явного репланирования.
        """
        env = self._create_baseline_env()
        snapshot = self.guard.create_snapshot(
            task_id="task-drift-rules",
            rules_ref=env["rules_ref"],
            provider=env["model_route"]["provider"],
            model_alias=env["model_route"]["model_alias"],
            resolved_model_version=env["model_route"]["resolved_model_version"],
            context_manifest_ref=env["context_manifest_ref"],
            skill_revisions=env["skill_revisions"],
            tool_definitions=env["tool_definitions"],
            config_revision=env["config_revision"],
            contract_versions=env["contract_versions"]
        )

        drifted_env = dict(env)
        drifted_env["rules_ref"] = "canonical-v1.5-rules-new-policy"

        with self.assertRaises(SemanticDriftError) as ctx:
            self.guard.verify_resume_preflight(snapshot, drifted_env)

        self.assertIn("Rules reference has changed", str(ctx.exception))

    def test_tool_schema_drift_blocks_resume(self):
        """
        Критический сценарий:
        Сигнатура или схема инструмента изменилась.
        Возобновление блокируется (Fail-Closed).
        """
        env = self._create_baseline_env()
        snapshot = self.guard.create_snapshot(
            task_id="task-drift-tools",
            rules_ref=env["rules_ref"],
            provider=env["model_route"]["provider"],
            model_alias=env["model_route"]["model_alias"],
            resolved_model_version=env["model_route"]["resolved_model_version"],
            context_manifest_ref=env["context_manifest_ref"],
            skill_revisions=env["skill_revisions"],
            tool_definitions=env["tool_definitions"],
            config_revision=env["config_revision"],
            contract_versions=env["contract_versions"]
        )

        drifted_env = dict(env)
        drifted_env["tool_definitions"] = dict(env["tool_definitions"])
        drifted_env["tool_definitions"]["fs_read"] = "sha256-mutated-schema-999"

        with self.assertRaises(SemanticDriftError) as ctx:
            self.guard.verify_resume_preflight(snapshot, drifted_env)

        self.assertIn("Tool 'fs_read' schema/version has drifted", str(ctx.exception))

    def test_compatible_skill_change_allows_resume_with_audit(self):
        """
        Неразрушающий сценарий:
        Обновился внутренний вспомогательный навык (Skill), но модели, правила и инструменты неизменны.
        Preflight разрешает продолжение со статусом RESUME_WITH_AUDIT.
        """
        env = self._create_baseline_env()
        snapshot = self.guard.create_snapshot(
            task_id="task-compat-skill",
            rules_ref=env["rules_ref"],
            provider=env["model_route"]["provider"],
            model_alias=env["model_route"]["model_alias"],
            resolved_model_version=env["model_route"]["resolved_model_version"],
            context_manifest_ref=env["context_manifest_ref"],
            skill_revisions=env["skill_revisions"],
            tool_definitions=env["tool_definitions"],
            config_revision=env["config_revision"],
            contract_versions=env["contract_versions"],
            prompt_template_revision=env["model_route"]["prompt_template_revision"]
        )

        modified_env = dict(env)
        modified_env["skill_revisions"] = dict(env["skill_revisions"])
        modified_env["skill_revisions"]["git_operator"] = "rev-1.2.1-patch"

        report = self.guard.compare_environments(snapshot, modified_env)
        self.assertEqual(report["decision"], "RESUME_WITH_AUDIT")
        self.assertEqual(report["policy_action"], "CONTINUE_WITH_LOGGED_CHANGES")
        self.assertFalse(report["has_breaking_drift"])
        self.assertEqual(report["differences_count"], 1)
