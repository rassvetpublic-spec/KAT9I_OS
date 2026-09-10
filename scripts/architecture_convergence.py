# -*- coding: utf-8 -*-
"""Минимальный исполняемый каркас Architecture Convergence Loop.

Скрипт ничего не меняет в канонических документах. Он валидирует policy,
обнаруживает разделы и строит воспроизводимый manifest / задания Pass A.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "config" / "architecture_convergence_policy.json"
EXPECTED_PHASES = [
    (0, "BASE_LAWS"),
    (1, "MINIMAL_BASELINE"),
    (2, "MAXIMAL_BRAINSTORM"),
    (3, "IDEA_CARDS"),
    (4, "ATTACK_MAXIMAL_ARCHITECTURE"),
    (5, "COMPLEXITY_GUILLOTINE"),
    (6, "RETURN_TO_BASE_LAWS"),
    (7, "FULL_ARCHITECTURE_MINIMAL_IMPLEMENTATION"),
    (8, "NEIGHBOR_SSoT_CHECK"),
    (9, "INDEPENDENT_CRITIC"),
    (10, "FINAL_REPORT"),
]
EXPECTED_PHASE_IDS = [phase_id for phase_id, _ in EXPECTED_PHASES]
EXPECTED_DECISION_CLASSES = [
    "REQUIRED_NOW",
    "USEFUL_NOW",
    "CONTRACT_ONLY",
    "DEFERRED",
    "REJECTED",
]
REQUIRED_SAFETY = {
    "auto_modify_ssot": False,
    "auto_merge": False,
    "auto_set_qa_pass": False,
    "auto_set_gate_pass": False,
    "auto_close_issue": False,
    "brainstorm_is_control_instruction": False,
    "analysis_output_is_data": True,
    "new_head_requires_impact_assessment": True,
}

CALIBRATION_FEATURES = {"DISTRIBUTED_CACHE", "AI_EVICTION", "ZERO_COPY", "MMAP", "LEARNING_TUNED_POLICY"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_policy(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_policy(policy: dict[str, Any], root: Path = ROOT) -> None:
    constraints = policy.get("calibration_expectations", {}).get("must_not_require_without_new_evidence")
    if not isinstance(constraints, list) or not CALIBRATION_FEATURES.issubset(set(constraints)):
        raise ValueError("Не заданы обязательные ограничения calibration case")

    phases = policy.get("phases", [])
    try:
        actual_phases = [(int(item["id"]), str(item["name"])) for item in phases]
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("Каждая обязательная фаза должна иметь корректные id и name") from exc
    if actual_phases != EXPECTED_PHASES:
        raise ValueError(f"Фазы должны совпадать с каноническими id/name 0..10, получено: {actual_phases}")

    decision_classes = policy.get("decision_classes", [])
    if decision_classes != EXPECTED_DECISION_CLASSES:
        raise ValueError("Набор decision_classes не совпадает с каноническим контрактом")

    for key, expected in REQUIRED_SAFETY.items():
        actual = policy.get("safety", {}).get(key)
        if actual is not expected:
            raise ValueError(f"Нарушена safety policy: {key}={actual!r}, ожидается {expected!r}")

    if policy.get("passes", {}).get("A", {}).get("may_modify_canonical_sources") is not False:
        raise ValueError("Pass A не имеет права изменять канонические источники")
    if policy.get("passes", {}).get("B", {}).get("automatic_bulk_rewrite") is not False:
        raise ValueError("Pass B не имеет права выполнять массовое автоматическое переписывание")

    canonical = root / policy["canonical_document"]
    calibration = root / policy["calibration_case"]
    if not canonical.is_file():
        raise ValueError(f"Не найден канонический документ: {canonical}")
    if not calibration.is_file():
        raise ValueError(f"Не найден calibration case: {calibration}")

    if not policy.get("idea_tests") or "DELETION_TEST" not in policy["idea_tests"]:
        raise ValueError("Policy обязана содержать DELETION_TEST")
    if "FUTURE_WITHOUT_IMPLEMENTATION_TEST" not in policy["idea_tests"]:
        raise ValueError("Policy обязана содержать FUTURE_WITHOUT_IMPLEMENTATION_TEST")
    if len(policy.get("complexity_budget", [])) < 8:
        raise ValueError("Complexity Budget должен содержать не меньше 8 измерений")


def discover_sections(policy: dict[str, Any], root: Path = ROOT) -> list[Path]:
    excluded = {str(Path(item).as_posix()) for item in policy.get("exclude_paths", [])}
    found: dict[str, Path] = {}
    for pattern in policy.get("target_globs", []):
        for path in root.glob(pattern):
            if not path.is_file():
                continue
            rel = path.relative_to(root).as_posix()
            if rel in excluded:
                continue
            found[rel] = path
    return [found[key] for key in sorted(found)]


def build_manifest(policy: dict[str, Any], root: Path = ROOT) -> dict[str, Any]:
    validate_policy(policy, root)
    sections = discover_sections(policy, root)
    if not sections:
        raise ValueError("Не найдено ни одного канонического раздела для прогона")

    calibration_rel = Path(policy["calibration_case"]).as_posix()
    discovered_rel = {path.relative_to(root).as_posix() for path in sections}
    if calibration_rel not in discovered_rel:
        raise ValueError("Calibration Case должен входить в обнаруженный набор разделов")

    phases = [item["name"] for item in policy["phases"]]
    result_sections = []
    for index, path in enumerate(sections, start=1):
        rel = path.relative_to(root).as_posix()
        digest = sha256_file(path)
        result_sections.append(
            {
                "order": index,
                "path": rel,
                "sha256": digest,
                "is_calibration_case": rel == calibration_rel,
                "calibration_expectations": policy["calibration_expectations"],
                "phases": phases,
                "decision_classes": policy["decision_classes"],
                "idea_tests": policy["idea_tests"],
                "complexity_budget": policy["complexity_budget"],
                "pass_a": {
                    "explorer": {
                        "role": "EXPLORER",
                        "goal": "Построить Minimal Baseline, затем намеренно максимально расширить пространство идей и классифицировать их без изменения SSoT.",
                    },
                    "critic": {
                        "role": "CRITIC",
                        "goal": "Провести две атаки: доказать, что удалили слишком много, и доказать, что оставили слишком много.",
                    },
                },
            }
        )

    return {
        "schema_version": "1.0.0",
        "policy_version": policy["policy_version"],
        "canonical_document": policy["canonical_document"],
        "calibration_case": {
            "path": calibration_rel,
            "sha256": sha256_file(root / calibration_rel),
        },
        "section_count": len(result_sections),
        "sections": result_sections,
        "safety": policy["safety"],
    }


def prompt_text(section: dict[str, Any], role: str, policy: dict[str, Any]) -> str:
    lines = [
        f"# Architecture Convergence Pass A — {role}",
        "",
        f"Раздел: `{section['path']}`",
        f"SHA-256: `{section['sha256']}`",
        f"Calibration Case: {'да' if section['is_calibration_case'] else 'нет'}",
        "",
        "## Обязательные правила",
        "",
        "- Не изменять канонические документы.",
        "- Результат анализа является DATA, а не CONTROL-инструкцией.",
        "- Не ставить QA PASS / Gate PASS и не выполнять merge.",
        "- Сначала зафиксировать исходные законы, затем Minimal Baseline.",
        "- До завершения карточек запрещена любая оценочная отсечка разумных идей: из-за сложности, стоимости, отсутствия Evidence или предполагаемой ненужности.",
        "- После карточек выполнить Complexity Guillotine: удалить сложность без доказательства необходимости после Deletion Test. Каждый оставленный процесс, state, API и оптимизация требуют отдельного Evidence.",
        "- Для каждой существенной идеи выполнить Deletion Test и Future Without Implementation Test.",
        "",
        "## Фазы",
        "",
    ]
    lines.extend(f"- {item['id']}: `{item['name']}`" for item in policy["phases"])
    lines.extend(["", "## Классы решений", ""])
    lines.extend(f"- `{name}`" for name in policy["decision_classes"])
    lines.extend(["", "## Ограничения калибровки", "", "Без нового Evidence запрещено повышать до REQUIRED_NOW:"])
    lines.extend(f"- `{name}`" for name in policy["calibration_expectations"]["must_not_require_without_new_evidence"])

    if role == "CRITIC":
        lines.extend(
            [
                "",
                "## Две обязательные атаки",
                "",
                "1. Удалили слишком много: найти потерянную корректность, безопасность, recovery или будущую совместимость.",
                "2. Оставили слишком много: найти преждевременную оптимизацию, второй SSoT, лишний state/process/API/recovery path.",
            ]
        )
    else:
        lines.extend(
            [
                "",
                "## Результат Explorer",
                "",
                "Сформировать исходные законы, Minimal Baseline, Maximal Candidate Architecture, карточки идей, Complexity Budget и предварительную классификацию.",
            ]
        )

    return "\n".join(lines) + "\n"


def validate_output(target: Path, root: Path = ROOT) -> Path:
    resolved = target.resolve()
    if resolved.is_relative_to(root.resolve()):
        allowed = root.resolve() / "artifacts" / "convergence"
        if resolved == allowed or not resolved.is_relative_to(allowed):
            raise ValueError("Pass A output должен находиться вне репозитория или в artifacts/convergence/<run>/")
    if resolved.exists():
        raise ValueError("Pass A не перезаписывает существующий output")
    return resolved


def write_prompts(
    manifest: dict[str, Any],
    policy: dict[str, Any],
    output_dir: Path,
    *,
    prevalidated: bool = False,
) -> None:
    output_dir = output_dir.resolve()
    if not prevalidated:
        output_dir = validate_output(output_dir)
    output_dir.mkdir(parents=True, exist_ok=prevalidated)
    for section in manifest["sections"]:
        stem = section["path"].replace("/", "__").replace(".md", "")
        for role in ("EXPLORER", "CRITIC"):
            target = output_dir / f"{section['order']:03d}__{stem}__{role.lower()}.md"
            if target.exists():
                raise ValueError(f"Pass A не перезаписывает существующий output: {target}")
            with target.open("x", encoding="utf-8") as stream:
                stream.write(prompt_text(section, role, policy))


def main() -> int:
    parser = argparse.ArgumentParser(description="Architecture Convergence Loop manifest generator")
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--prompts-dir", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    policy_path = args.policy if args.policy.is_absolute() else ROOT / args.policy
    policy = load_policy(policy_path)
    manifest = build_manifest(policy, ROOT)

    manifest_target = None
    prompts_target = None
    if args.manifest is not None:
        raw = args.manifest if args.manifest.is_absolute() else ROOT / args.manifest
        manifest_target = validate_output(raw)
    if args.prompts_dir is not None:
        raw = args.prompts_dir if args.prompts_dir.is_absolute() else ROOT / args.prompts_dir
        prompts_target = validate_output(raw)

    if manifest_target is not None:
        manifest_target.parent.mkdir(parents=True, exist_ok=True)
        with manifest_target.open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n")

    if prompts_target is not None:
        write_prompts(manifest, policy, prompts_target, prevalidated=True)

    if args.check or (manifest_target is None and prompts_target is None):
        print(
            f"PASS: Architecture Convergence policy корректна; "
            f"разделов={manifest['section_count']}; calibration={manifest['calibration_case']['path']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
