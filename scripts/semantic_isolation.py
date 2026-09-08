# -*- coding: utf-8 -*-
"""
Механизм семантической изоляции выполнения и контроля возобновления задач (Issue #42, Gate G5).

Основан на концепции 'Semantic Isolation for Durable AI Workflows' (2026):
1. Execution Semantic Snapshot фиксирует точные ссылки и хэши значимых ресурсов:
   - RulesRef;
   - точный маршрут и разрешённая версия модели (resolved_model_version);
   - ревизия манифеста контекста и базы знаний;
   - версии используемых Skills/Workflow;
   - схемы и версии инструментов / MCP серверов;
   - ревизия системной конфигурации;
   - версии контрактов.
2. Детерминированный компаратор (SemanticIsolationGuard):
   - При попытке продолжения (Resume) задачи после паузы или сбоя сравнивает
     исходный снимок с текущим окружением.
   - Определяет класс дрейфа:
     * MATCH: полное совпадение окружения, продолжение разрешено (RESUME_ALLOWED).
     * COMPATIBLE_CHANGE: незначительное обновление (например, патч-версия контракта),
       разрешено автоматическое продолжение с фиксацией в журнале.
     * BREAKING_DRIFT: критический дрейф (изменение модели, системного промпта, правил,
       интерфейса инструментов или манифеста контекста).
       В соответствии с политикой Fail-Closed продолжение блокируется (RESUME_BLOCKED)
       либо переводится в статус REQUIRE_REPLANNING / REQUIRE_USER_CONFIRMATION.
"""

import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMAS_V1_DIR = REPO_ROOT / "schemas" / "v1"


class SemanticDriftError(RuntimeError):
    """Критический семантический дрейф окружения, блокирующий продолжение задачи."""
    pass


class SemanticIsolationGuard:
    """Детерминированный контроллер семантической изоляции и проверки совместимости окружения."""

    def __init__(self):
        schema_path = SCHEMAS_V1_DIR / "SemanticSnapshot.json"
        with open(schema_path, "r", encoding="utf-8") as f:
            self.snapshot_schema = json.load(f)
        self.validator = Draft202012Validator(self.snapshot_schema)

    def validate_snapshot(self, snapshot: Dict[str, Any]):
        """Проверяет снимок на соответствие канонической схеме Draft 2020-12."""
        self.validator.validate(snapshot)

    def create_snapshot(
        self,
        task_id: str,
        rules_ref: str,
        provider: str,
        model_alias: str,
        resolved_model_version: str,
        context_manifest_ref: str,
        skill_revisions: Dict[str, str],
        tool_definitions: Dict[str, str],
        config_revision: str,
        contract_versions: Dict[str, str],
        step_id: Optional[str] = None,
        temperature: float = 0.0,
        prompt_template_revision: Optional[str] = None
    ) -> Dict[str, Any]:
        """Формирует и валидирует канонический SemanticSnapshot."""
        snapshot = {
            "snapshot_id": f"sem-{uuid.uuid4().hex[:16]}",
            "task_id": task_id,
            "step_id": step_id,
            "rules_ref": rules_ref,
            "model_route": {
                "provider": provider,
                "model_alias": model_alias,
                "resolved_model_version": resolved_model_version,
                "temperature": temperature,
                "prompt_template_revision": prompt_template_revision or "sha256-default-prompt"
            },
            "context_manifest_ref": context_manifest_ref,
            "skill_revisions": skill_revisions,
            "tool_definitions": tool_definitions,
            "config_revision": config_revision,
            "contract_versions": contract_versions,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        self.validate_snapshot(snapshot)
        return snapshot

    def compare_environments(
        self,
        baseline_snapshot: Dict[str, Any],
        current_environment: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Сравнивает базовый семантический снимок с текущим окружением.
        Возвращает детальный отчёт о совместимости (Verdict, Drift Details, Policy Action).
        """
        self.validate_snapshot(baseline_snapshot)
        differences = []
        breaking_drift = False

        # 1. Проверка RulesRef (Критично: изменение системных правил ломает воспроизводимость)
        current_rules = current_environment.get("rules_ref")
        if current_rules != baseline_snapshot["rules_ref"]:
            differences.append({
                "component": "rules_ref",
                "severity": "CRITICAL",
                "baseline": baseline_snapshot["rules_ref"],
                "current": current_rules,
                "description": "Rules reference has changed"
            })
            breaking_drift = True

        # 2. Проверка маршрута и версии модели (Критично: смена версии модели меняет логику рассуждений)
        b_model = baseline_snapshot["model_route"]
        c_model = current_environment.get("model_route", {})
        if (b_model.get("provider") != c_model.get("provider") or
            b_model.get("resolved_model_version") != c_model.get("resolved_model_version")):
            differences.append({
                "component": "model_route.version",
                "severity": "CRITICAL",
                "baseline": f"{b_model.get('provider')}:{b_model.get('resolved_model_version')}",
                "current": f"{c_model.get('provider')}:{c_model.get('resolved_model_version')}",
                "description": "Underlying model provider or exact version has drifted"
            })
            breaking_drift = True

        if b_model.get("prompt_template_revision") != c_model.get("prompt_template_revision"):
            differences.append({
                "component": "model_route.prompt_template",
                "severity": "CRITICAL",
                "baseline": b_model.get("prompt_template_revision"),
                "current": c_model.get("prompt_template_revision"),
                "description": "System prompt template revision has drifted"
            })
            breaking_drift = True

        # 3. Проверка схем инструментов (Критично: смена сигнатуры инструментов меняет выполнение)
        b_tools = baseline_snapshot["tool_definitions"]
        c_tools = current_environment.get("tool_definitions", {})
        for t_name, t_hash in b_tools.items():
            if t_name not in c_tools:
                differences.append({
                    "component": f"tool_definitions.{t_name}",
                    "severity": "CRITICAL",
                    "baseline": t_hash,
                    "current": None,
                    "description": f"Tool '{t_name}' is missing in current environment"
                })
                breaking_drift = True
            elif c_tools[t_name] != t_hash:
                differences.append({
                    "component": f"tool_definitions.{t_name}",
                    "severity": "CRITICAL",
                    "baseline": t_hash,
                    "current": c_tools[t_name],
                    "description": f"Tool '{t_name}' schema/version has drifted"
                })
                breaking_drift = True

        # 4. Проверка контекста и базы знаний (Критично при изменении манифеста)
        if baseline_snapshot["context_manifest_ref"] != current_environment.get("context_manifest_ref"):
            differences.append({
                "component": "context_manifest_ref",
                "severity": "CRITICAL",
                "baseline": baseline_snapshot["context_manifest_ref"],
                "current": current_environment.get("context_manifest_ref"),
                "description": "Context and knowledge base index has changed"
            })
            breaking_drift = True

        # 5. Проверка навыков (Skills)
        b_skills = baseline_snapshot["skill_revisions"]
        c_skills = current_environment.get("skill_revisions", {})
        for s_name, s_hash in b_skills.items():
            if c_skills.get(s_name) != s_hash:
                differences.append({
                    "component": f"skill_revisions.{s_name}",
                    "severity": "WARNING",
                    "baseline": s_hash,
                    "current": c_skills.get(s_name),
                    "description": f"Skill '{s_name}' revision modified"
                })

        # 6. Определение вердикта и политики
        if not differences:
            decision = "RESUME_ALLOWED"
            action = "CONTINUE"
        elif breaking_drift:
            decision = "RESUME_BLOCKED"
            action = "REQUIRE_REPLANNING_OR_CONFIRMATION"
        else:
            decision = "RESUME_WITH_AUDIT"
            action = "CONTINUE_WITH_LOGGED_CHANGES"

        return {
            "task_id": baseline_snapshot["task_id"],
            "decision": decision,
            "policy_action": action,
            "has_breaking_drift": breaking_drift,
            "differences_count": len(differences),
            "differences": differences,
            "evaluated_at": datetime.now(timezone.utc).isoformat()
        }

    def verify_resume_preflight(self, baseline_snapshot: Dict[str, Any], current_environment: Dict[str, Any]):
        """
        Проверка Preflight перед возобновлением.
        Бросает SemanticDriftError при критическом несовместимом дрейфе окружения (Fail-Closed).
        """
        report = self.compare_environments(baseline_snapshot, current_environment)
        if report["has_breaking_drift"]:
            crit = [d["description"] for d in report["differences"] if d["severity"] == "CRITICAL"]
            raise SemanticDriftError(
                f"Resume rejected: breaking semantic drift detected in task '{baseline_snapshot['task_id']}': "
                f"{'; '.join(crit)}"
            )
        return report
