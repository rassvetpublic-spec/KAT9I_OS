# -*- coding: utf-8 -*-

import json
import tempfile
import unittest
from pathlib import Path

from scripts.architecture_convergence import (
    EXPECTED_DECISION_CLASSES,
    EXPECTED_PHASE_IDS,
    EXPECTED_PHASES,
    ROOT,
    build_manifest,
    load_policy,
    validate_policy,
    write_prompts,
    validate_output,
    prompt_text,
)


POLICY_PATH = ROOT / "config" / "architecture_convergence_policy.json"
DOC_PATH = ROOT / "docs" / "architecture" / "35_ARCHITECTURE_CONVERGENCE_LOOP.md"


class ArchitectureConvergenceTests(unittest.TestCase):
    def setUp(self):
        self.policy = load_policy(POLICY_PATH)

    def test_policy_is_valid_and_complete(self):
        validate_policy(self.policy, ROOT)
        self.assertEqual(EXPECTED_PHASE_IDS, [item["id"] for item in self.policy["phases"]])
        self.assertEqual(EXPECTED_PHASES, [(item["id"], item["name"]) for item in self.policy["phases"]])
        self.assertEqual(EXPECTED_DECISION_CLASSES, self.policy["decision_classes"])
        self.assertIn("DELETION_TEST", self.policy["idea_tests"])
        self.assertIn("FUTURE_WITHOUT_IMPLEMENTATION_TEST", self.policy["idea_tests"])
        self.assertGreaterEqual(len(self.policy["complexity_budget"]), 8)

    def test_phase_name_change_is_fail_closed(self):
        self.policy["phases"][2]["name"] = "RENAMED_BRAINSTORM"
        with self.assertRaises(ValueError):
            validate_policy(self.policy, ROOT)

    def test_safety_is_fail_closed_for_control_actions(self):
        safety = self.policy["safety"]
        self.assertFalse(safety["auto_modify_ssot"])
        self.assertFalse(safety["auto_merge"])
        self.assertFalse(safety["auto_set_qa_pass"])
        self.assertFalse(safety["auto_set_gate_pass"])
        self.assertFalse(safety["auto_close_issue"])
        self.assertTrue(safety["analysis_output_is_data"])
        self.assertTrue(safety["new_head_requires_impact_assessment"])

    def test_outputs_cannot_overwrite_canon_or_control(self):
        for relative in ("docs/architecture/35_ARCHITECTURE_CONVERGENCE_LOOP.md", "docs/architecture", ".github/new.yml", "scripts/new.py", "index.html"):
            with self.subTest(path=relative), self.assertRaises(ValueError):
                validate_output(ROOT / relative)

    def test_existing_external_output_is_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "old.md"
            target.write_text("original", encoding="utf-8")
            with self.assertRaises(ValueError):
                validate_output(target)
            self.assertEqual("original", target.read_text(encoding="utf-8"))

    def test_manifest_and_prompts_can_share_new_run_directory(self):
        manifest = build_manifest(self.policy, ROOT)
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run"
            manifest_target = validate_output(run_dir / "manifest.json")
            prompts_target = validate_output(run_dir)

            manifest_target.parent.mkdir(parents=True, exist_ok=True)
            manifest_target.write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            write_prompts(manifest, self.policy, prompts_target, prevalidated=True)

            self.assertTrue(manifest_target.is_file())
            generated = sorted(run_dir.glob("*__explorer.md")) + sorted(run_dir.glob("*__critic.md"))
            self.assertEqual(manifest["section_count"] * 2, len(generated))

    def test_missing_calibration_is_rejected(self):
        del self.policy["calibration_expectations"]
        with self.assertRaises(ValueError):
            build_manifest(self.policy, ROOT)

    def test_both_roles_receive_calibration_and_deletion_rules(self):
        manifest = build_manifest(self.policy, ROOT)
        section = next(s for s in manifest["sections"] if s["is_calibration_case"])
        self.assertEqual(self.policy["calibration_expectations"], section["calibration_expectations"])
        for role in ("EXPLORER", "CRITIC"):
            prompt = prompt_text(section, role, self.policy)
            for feature in self.policy["calibration_expectations"]["must_not_require_without_new_evidence"]:
                self.assertIn(feature, prompt)
            self.assertIn("любая оценочная отсечка", prompt)
            self.assertIn("удалить сложность без доказательства", prompt)

    def test_manifest_is_deterministic(self):
        first = build_manifest(self.policy, ROOT)
        second = build_manifest(self.policy, ROOT)
        self.assertEqual(first, second)
        encoded = json.dumps(first, ensure_ascii=False, sort_keys=True)
        self.assertNotIn("timestamp", encoded.lower())
        self.assertNotIn("uuid", encoded.lower())

    def test_cache_engine_is_calibration_case(self):
        manifest = build_manifest(self.policy, ROOT)
        calibration = manifest["calibration_case"]
        self.assertEqual("docs/architecture/34_CACHE_ENGINE.md", calibration["path"])
        section = next(item for item in manifest["sections"] if item["path"] == calibration["path"])
        self.assertTrue(section["is_calibration_case"])
        expected = self.policy["calibration_expectations"]["must_not_require_without_new_evidence"]
        self.assertIn("DISTRIBUTED_CACHE", expected)
        self.assertIn("ZERO_COPY", expected)
        self.assertIn("AI_EVICTION", expected)

    def test_all_sections_get_explorer_and_critic(self):
        manifest = build_manifest(self.policy, ROOT)
        self.assertGreater(manifest["section_count"], 5)
        for section in manifest["sections"]:
            self.assertEqual(11, len(section["phases"]))
            self.assertEqual("EXPLORER", section["pass_a"]["explorer"]["role"])
            self.assertEqual("CRITIC", section["pass_a"]["critic"]["role"])

    def test_prompt_generation_does_not_touch_sources(self):
        before = {item["path"]: item["sha256"] for item in build_manifest(self.policy, ROOT)["sections"]}
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "prompts"
            manifest = build_manifest(self.policy, ROOT)
            write_prompts(manifest, self.policy, output)
            generated = sorted(output.glob("*.md"))
            self.assertEqual(manifest["section_count"] * 2, len(generated))
            text = generated[0].read_text(encoding="utf-8")
            self.assertIn("Не изменять канонические документы", text)
        after = {item["path"]: item["sha256"] for item in build_manifest(self.policy, ROOT)["sections"]}
        self.assertEqual(before, after)

    def test_human_document_and_policy_share_core_principles(self):
        text = DOC_PATH.read_text(encoding="utf-8")
        self.assertIn("Полная архитектура — минимальная реализация", text)
        self.assertIn("Complexity Guillotine", text)
        self.assertIn("Deletion Test", text)
        self.assertIn("Future Without Implementation Test", text)
        self.assertIn("docs/architecture/34_CACHE_ENGINE.md", text)
        for decision in EXPECTED_DECISION_CLASSES:
            self.assertIn(decision, text)


if __name__ == "__main__":
    unittest.main()
