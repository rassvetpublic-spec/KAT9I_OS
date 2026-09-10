# -*- coding: utf-8 -*-
"""Детерминированные проверки T0 Requirements Registry (Issue #129)."""

import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = REPO_ROOT / "requirements_registry.json"
SCHEMA_PATH = REPO_ROOT / "schemas" / "v1" / "RequirementsRegistry.json"


class TestRequirementsRegistry(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with REGISTRY_PATH.open("r", encoding="utf-8") as stream:
            cls.registry = json.load(stream)
        with SCHEMA_PATH.open("r", encoding="utf-8") as stream:
            cls.schema = json.load(stream)

    def test_schema_and_registry_are_valid(self):
        Draft202012Validator.check_schema(self.schema)
        Draft202012Validator(self.schema).validate(self.registry)

    def test_requirement_ids_are_unique_and_dependencies_resolve(self):
        ids = [item["requirement_id"] for item in self.registry["requirements"]]
        self.assertEqual(len(ids), len(set(ids)), "Requirement ID должны быть уникальны")
        known = set(ids)
        for item in self.registry["requirements"]:
            unknown = set(item["dependencies"]) - known
            self.assertFalse(unknown, f"{item['requirement_id']}: неизвестные зависимости {sorted(unknown)}")

    def test_t0_does_not_assign_abc_or_xyz(self):
        for item in self.registry["requirements"]:
            self.assertEqual(item["abc"], "UNASSESSED")
            self.assertEqual(item["xyz"], "UNASSESSED")

    def test_each_gap_is_unique_and_references_known_requirements(self):
        gap_ids = [item["gap_id"] for item in self.registry["gaps"]]
        self.assertEqual(len(gap_ids), len(set(gap_ids)), "Gap ID должны быть уникальны")
        known = {item["requirement_id"] for item in self.registry["requirements"]}
        for gap in self.registry["gaps"]:
            self.assertTrue(gap["requirement_refs"], f"{gap['gap_id']} обязан ссылаться на Requirement")
            unknown = set(gap["requirement_refs"]) - known
            self.assertFalse(unknown, f"{gap['gap_id']}: неизвестные Requirement refs {sorted(unknown)}")

    def test_non_covered_requirements_have_registered_gap(self):
        gap_refs = {
            req
            for gap in self.registry["gaps"]
            for req in gap["requirement_refs"]
        }
        for item in self.registry["requirements"]:
            if item["coverage_status"] != "COVERED":
                self.assertIn(
                    item["requirement_id"],
                    gap_refs,
                    f"{item['requirement_id']} имеет {item['coverage_status']} без записи в gaps",
                )

    def test_inventory_covers_all_current_t0_source_families(self):
        expected = set()
        for pattern in (
            "docs/tz/*.md",
            "docs/architecture/*.md",
            "docs/spec/*.md",
            "schemas/v1/*.json",
        ):
            expected.update(
                path.relative_to(REPO_ROOT).as_posix()
                for path in REPO_ROOT.glob(pattern)
                if path.is_file()
            )
        for relative in (
            "schemas/README.md",
            "modules_registry.json",
            "AGENTS.md",
            "docs/GITHUB_WORKFLOW.md",
            "QA_PROTOCOL.md",
            "config/architecture_convergence_policy.json",
            ".github/workflows/quality.yml",
            ".github/workflows/project-queue-sync.yml",
        ):
            path = REPO_ROOT / relative
            if path.exists():
                expected.add(relative)

        covered = set()
        for source in self.registry["source_inventory"]:
            pattern = source["path"]
            matches = [path for path in REPO_ROOT.glob(pattern) if path.is_file()]
            self.assertTrue(matches, f"source_inventory pattern не разрешается ни в один файл: {pattern}")
            covered.update(path.relative_to(REPO_ROOT).as_posix() for path in matches)

        missing = expected - covered
        self.assertFalse(missing, f"T0 source_inventory не покрывает: {sorted(missing)}")

    def test_known_t0_findings_are_not_silently_hidden(self):
        gaps = {gap["gap_id"]: gap for gap in self.registry["gaps"]}
        self.assertEqual(gaps["GAP-T0-001"]["kind"], "TRACEABILITY_GAP")
        self.assertEqual(gaps["GAP-T0-002"]["kind"], "CONTRADICTION")
        self.assertIn("REQ-OQ010-001", {r["requirement_id"] for r in self.registry["requirements"]})

    def test_registry_is_traceability_not_second_ssot(self):
        for item in self.registry["requirements"]:
            self.assertTrue(item["canonical_ssot"].strip())
            self.assertTrue(item["canonical_owner"].strip())
        self.assertEqual(
            self.registry["generated_from"],
            "docs/spec/25_TZ_REQUIREMENTS_PRIORITIZATION_PIPELINE.md#25.5",
        )


class TestRequirementsRegistryCorrectiveInvariants(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with REGISTRY_PATH.open("r", encoding="utf-8") as stream:
            cls.registry = json.load(stream)

    @staticmethod
    def _repo_path(ref):
        return ref.split("#", 1)[0].strip()

    def test_canonical_ssot_is_single_resolvable_repo_ref(self):
        for item in self.registry["requirements"]:
            ref = item["canonical_ssot"]
            self.assertNotIn(";", ref, f"{item['requirement_id']}: canonical_ssot содержит список")
            path = REPO_ROOT / self._repo_path(ref)
            self.assertTrue(path.is_file(), f"{item['requirement_id']}: canonical_ssot не разрешается: {ref}")
            for supporting in item.get("supporting_refs", []):
                support_path = REPO_ROOT / self._repo_path(supporting)
                self.assertTrue(support_path.exists(), f"{item['requirement_id']}: supporting_ref не разрешается: {supporting}")

    def test_machine_contract_refs_are_literal_resolvable_repo_files(self):
        for item in self.registry["requirements"]:
            for ref in item["machine_contract_refs"]:
                self.assertNotIn("*", ref, f"{item['requirement_id']}: wildcard contract ref: {ref}")
                path = REPO_ROOT / self._repo_path(ref)
                self.assertTrue(path.is_file(), f"{item['requirement_id']}: machine_contract_ref не разрешяется: {ref}")

    def test_each_requirement_has_one_canonical_owner(self):
        for item in self.registry["requirements"]:
            owner = item["canonical_owner"]
            self.assertNotIn("/", owner, f"{item['requirement_id']}: составной canonical_owner: {owner}")

    def test_owner_gap_does_not_invent_canonical_owner(self):
        for item in self.registry["requirements"]:
            if item["coverage_status"] == "OWNER_GAP":
                self.assertEqual(item["canonical_owner"], "UNRESOLVED")

    def test_noncovered_requirement_has_gap_of_same_kind(self):
        by_kind = {}
        for gap in self.registry["gaps"]:
            by_kind.setdefault(gap["kind"], set()).update(gap["requirement_refs"])
        for item in self.registry["requirements"]:
            kind = item["coverage_status"]
            if kind != "COVERED":
                self.assertIn(item["requirement_id"], by_kind.get(kind, set()), f"{item['requirement_id']}: {kind} без gap того же вида")

    def test_each_canonical_inventory_document_is_linked_to_requirement(self):
        linked = set()
        for item in self.registry["requirements"]:
            linked.add(self._repo_path(item["canonical_ssot"]))
            linked.update(self._repo_path(ref) for ref in item.get("supporting_refs", []))
        missing = []
        for source in self.registry["source_inventory"]:
            if source["role"] != "CANONICAL_SSoT":
                continue
            for path in REPO_ROOT.glob(source["path"]):
                if path.is_file():
                    rel = path.relative_to(REPO_ROOT).as_posix()
                    if rel not in linked:
                        missing.append(rel)
        self.assertFalse(missing, f"CANONICAL_SSoT без Requirement linkage: {sorted(missing)}")


if __name__ == "__main__":
    unittest.main()
