# -*- coding: utf-8 -*-
"""
Движок воспроизводимых Evals и регрессионного анализа для агентного поведения (Issue #51, Gate G5).

Архитектурные принципы:
1. Разделение QA и Evals:
   - QA проверяет конкретное единичное изменение (PR/коммит).
   - Evals систематически измеряет качество поведения на воспроизводимом наборе сценариев во времени.
2. 4 уровня проверок:
   - Детерминированные: точный PASS/FAIL (соблюдение инвариантов);
   - Структурные: соответствие контрактам и схемам;
   - Поведенческие: проверка отсутствия запрещённых действий (forbidden_actions);
   - Качественные: скоринг по формализованным критериям (без использования той же модели в роли судьи).
3. Анализ регрессий (Regression Report):
   - Сравнение текущего прогона с базовой линией (baseline);
   - Фиксация регрессий (когда сценарий ранее проходил, но в новой версии упал);
   - Запрет признания модели "лучшей" без доказанного отсутствия регрессий.
4. Базовый тестовый набор сценариев для вертикали разработки GitHub:
   - Анализ Issue;
   - Соблюдение Scope;
   - Запрет прямого push в main;
   - Корректное создание PR;
   - Запрет Self-QA (исполнитель не может одобрить собственный PR);
   - Обработка неполного/враждебного текста как DATA, а не CONTROL.
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMAS_V1_DIR = REPO_ROOT / "schemas" / "v1"


class Kat9iEvalRunner:
    """Движок воспроизводимого выполнения оценочных сценариев (EvalRunner)."""

    def __init__(self):
        schema_path = SCHEMAS_V1_DIR / "EvalSuite.json"
        with open(schema_path, "r", encoding="utf-8") as f:
            self.suite_schema = json.load(f)
        self.validator = Draft202012Validator(self.suite_schema)

    def validate_suite(self, suite: Dict[str, Any]):
        """Проверяет корректность набора сценариев по схеме EvalSuite.json."""
        self.validator.validate(suite)

    def execute_eval_case(
        self,
        case: Dict[str, Any],
        agent_executor: Callable[[Dict[str, Any]], Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Выполняет один оценочный сценарий с детерминированной и поведенческой проверкой:
        1. Передает input в функцию агента.
        2. Проверяет отсутствие forbidden_actions.
        3. Проверяет соблюдение expected_invariants.
        """
        case_id = case["case_id"]
        result = agent_executor(case["input"])

        actions_performed = result.get("actions", [])
        violations = []

        # 1. Проверка запрещенных действий (Behavioral Guard)
        for forbidden in case.get("forbidden_actions", []):
            if forbidden in actions_performed:
                violations.append(f"Forbidden action '{forbidden}' was performed by agent")

        # 2. Проверка инвариантов
        invariants_checked = {}
        for inv in case.get("expected_invariants", []):
            passed = result.get(inv, False) or (inv in result.get("invariants_met", []))
            invariants_checked[inv] = bool(passed)
            if not passed:
                violations.append(f"Expected invariant '{inv}' was not satisfied")

        case_passed = len(violations) == 0

        return {
            "case_id": case_id,
            "name": case["name"],
            "status": "PASS" if case_passed else "FAIL",
            "score": 1.0 if case_passed else 0.0,
            "violations": violations,
            "invariants_checked": invariants_checked,
            "agent_output": result.get("output", {})
        }

    def run_suite(
        self,
        suite: Dict[str, Any],
        agent_executor: Callable[[Dict[str, Any]], Dict[str, Any]],
        environment_meta: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Выполняет полный набор сценариев и формирует отчет."""
        self.validate_suite(suite)

        case_results = []
        total_cases = len(suite["cases"])
        passed_cases = 0

        for c in suite["cases"]:
            res = self.execute_eval_case(c, agent_executor)
            case_results.append(res)
            if res["status"] == "PASS":
                passed_cases += 1

        pass_rate = (passed_cases / total_cases) * 100 if total_cases > 0 else 0.0

        return {
            "suite_id": suite["suite_id"],
            "version": suite["version"],
            "domain": suite["domain"],
            "total_cases": total_cases,
            "passed_cases": passed_cases,
            "failed_cases": total_cases - passed_cases,
            "pass_rate_percent": round(pass_rate, 2),
            "environment_meta": environment_meta or {},
            "case_results": case_results,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    @staticmethod
    def compare_with_baseline(
        current_report: Dict[str, Any],
        baseline_report: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Формирует сравнительный регрессионный отчет (Regression Report).
        Выявляет:
        - Регрессии (ранее проходило, теперь падает);
        - Улучшения (ранее падало, теперь проходит);
        - Стабильные сценарии.
        """
        b_results = {c["case_id"]: c["status"] for c in baseline_report["case_results"]}
        c_results = {c["case_id"]: c["status"] for c in current_report["case_results"]}

        regressions = []
        improvements = []
        unchanged_pass = []
        unchanged_fail = []

        for cid, current_status in c_results.items():
            baseline_status = b_results.get(cid, "UNKNOWN")
            if baseline_status == "PASS" and current_status == "FAIL":
                regressions.append(cid)
            elif baseline_status == "FAIL" and current_status == "PASS":
                improvements.append(cid)
            elif baseline_status == "PASS" and current_status == "PASS":
                unchanged_pass.append(cid)
            elif baseline_status == "FAIL" and current_status == "FAIL":
                unchanged_fail.append(cid)

        verdict = "REGRESSION_DETECTED" if regressions else ("IMPROVED" if improvements else "STABLE")

        return {
            "verdict": verdict,
            "current_pass_rate": current_report["pass_rate_percent"],
            "baseline_pass_rate": baseline_report["pass_rate_percent"],
            "delta_pass_rate": round(current_report["pass_rate_percent"] - baseline_report["pass_rate_percent"], 2),
            "regressions_count": len(regressions),
            "regressions": regressions,
            "improvements_count": len(improvements),
            "improvements": improvements,
            "unchanged_pass_count": len(unchanged_pass),
            "unchanged_fail_count": len(unchanged_fail),
            "has_regressions": len(regressions) > 0
        }
