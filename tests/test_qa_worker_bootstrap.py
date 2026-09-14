import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "qa_worker_listener", ROOT / "scripts" / "qa_worker_listener.py"
)
qa = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(qa)


class FakeGitHub:
    def __init__(self, comments):
        self.comments = comments

    def paged(self, path, limit_pages=20):
        if path.endswith("/comments"):
            return list(self.comments)
        return []


class QaWorkerBootstrapTests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads((ROOT / "config" / "qa_worker.json").read_text(encoding="utf-8"))

    def _command(self, comment_id=1, *, exact_head="a" * 40, allow_merge="false", malformed=False):
        fields = [
            "KAT9I-CONTROL/1 | QA-COMMAND",
            f"command_id=qa-test-{comment_id}",
            "target_pr=7",
            "controller=ChatGPT",
            "executor=AGY",
            "role=QA_EXECUTOR",
            f"exact_head={exact_head}",
            "qa_mode=FULL",
            "result_sink=PR_REVIEW",
            "allow_issue_create=false",
            f"allow_merge={allow_merge}",
            "allow_fast_marker=false",
            "allow_code_mutation=false",
            "project_lifecycle_mutation=false",
            "EVIDENCE_EPOCH",
            "epoch_version=1",
            f"snapshot_head={exact_head}",
            "review_digest=" + "1" * 64,
            "gate_digest=" + "2" * 64,
            "policy_digest=" + "3" * 64,
            "evidence_digest=" + "4" * 64,
        ]
        if malformed:
            fields = [line for line in fields if not line.startswith("gate_digest=")]
        return {
            "id": comment_id,
            "author_association": "OWNER",
            "user": {"login": "rassvetpublic-spec"},
            "body": "\n".join(fields),
            "html_url": f"https://example.invalid/{comment_id}",
        }

    def test_worker_qa_is_single_bounded_entrypoint(self):
        entry = (ROOT / "WORKER_QA.md").read_text(encoding="utf-8")
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("Единственная корневая точка входа", entry)
        self.assertIn("Issue #171 — только история требования", entry)
        self.assertIn("0 LLM tokens", entry)
        self.assertIn("Project.Приоритет → FIFO authoritative QA-COMMAND", entry)
        self.assertIn("WORKER QA", agents)
        self.assertIn("WORKER_QA.md", agents)

    def test_budget_is_bounded_and_polling_is_ten_seconds(self):
        budget = self.config["token_budget"]
        self.assertEqual(self.config["poll_seconds"], 10)
        self.assertEqual(budget["idle_poll_llm_tokens"], 0)
        self.assertEqual(budget["soft_input_tokens"], 24000)
        self.assertEqual(budget["max_input_tokens"], 32000)
        self.assertEqual(budget["max_output_tokens"], 4000)
        self.assertEqual(budget["hard_total_model_tokens"], 40000)
        self.assertLess(budget["soft_input_tokens"], budget["max_input_tokens"])
        self.assertLess(budget["max_input_tokens"], budget["hard_total_model_tokens"])
        self.assertLessEqual(budget["max_escalations"], 1)

    def test_latest_malformed_command_blocks_fallback(self):
        older = self._command(1)
        latest = self._command(2, malformed=True)
        result = qa.latest_authoritative_command(FakeGitHub([older, latest]), 7, self.config)
        self.assertIsNone(result)

    def test_latest_forbidden_capability_blocks_fallback(self):
        older = self._command(1)
        latest = self._command(2, allow_merge="true")
        result = qa.latest_authoritative_command(FakeGitHub([older, latest]), 7, self.config)
        self.assertIsNone(result)

    def test_valid_latest_command_is_selected(self):
        older = self._command(1)
        latest = self._command(2)
        result = qa.latest_authoritative_command(FakeGitHub([older, latest]), 7, self.config)
        self.assertIsNotNone(result)
        comment, fields = result
        self.assertEqual(comment["id"], 2)
        self.assertEqual(fields["command_id"], "qa-test-2")
        self.assertEqual(fields["exact_head"], "a" * 40)

    def test_context_summaries_point_to_canon(self):
        for rel in (
            "docs/context/QA_ENVELOPE_STANDARD.md",
            "docs/context/QUEUE_GUARD_PROTOCOL.md",
            "docs/context/WORKER_PROTOCOL.md",
        ):
            text = (ROOT / rel).read_text(encoding="utf-8")
            self.assertIn("QA_PROTOCOL.md", text, rel)
            self.assertIn("WORKER_QA.md", text, rel)


if __name__ == "__main__":
    unittest.main()
