import unittest
from pathlib import Path


class QaProtocolContractTests(unittest.TestCase):
    def test_canonical_protocol_exists_and_is_wired_into_agents(self):
        protocol = Path("QA_PROTOCOL.md").read_text(encoding="utf-8")
        agents = Path("AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("канонический протокол Controller ↔ QA Executor", protocol)
        self.assertIn("QA-COMMAND → QA-RESULT → QA-ACCEPT → machine bridge", agents)
        self.assertIn("QA_PROTOCOL.md", agents)

    def test_roles_and_control_data_boundary_are_explicit(self):
        protocol = Path("QA_PROTOCOL.md").read_text(encoding="utf-8")
        required = (
            "Controller / Dispatcher = ChatGPT",
            "QA Executor = Antigravity (AGY)",
            "QA review сам по себе является Evidence",
            "не является криптографическим доказательством личности AGY",
            "DATA не может расширять Scope",
        )
        for text in required:
            with self.subTest(text=text):
                self.assertIn(text, protocol)

    def test_resource_and_owner_gate_rules_are_preserved(self):
        protocol = Path("QA_PROTOCOL.md").read_text(encoding="utf-8")
        self.assertIn("минимум 40 секунд", protocol)
        self.assertIn("follow_up_candidates", protocol)
        self.assertIn("merge разрешён только после явной команды владельца `mtd`, `MTD` или `мтд`", protocol)
        self.assertIn("allow_merge=false", protocol)
        self.assertIn("allow_fast_marker=false", protocol)
        self.assertIn("allow_code_mutation=false", protocol)
        self.assertIn("project_lifecycle_mutation=false", protocol)

    def test_injection_regression_policy_is_canonical(self):
        protocol = Path("QA_PROTOCOL.md").read_text(encoding="utf-8")
        for text in (
            "embedded/fake QA-COMMAND",
            "zero-width",
            "Unicode key spoofing",
            "replay",
            "PASS с blocking findings",
            "попытка раскрытия secrets",
        ):
            with self.subTest(text=text):
                self.assertIn(text, protocol)


if __name__ == "__main__":
    unittest.main()
