import importlib.util
import json
from pathlib import Path

from scripts.qa_evidence_epoch import aggregate_digest


ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


listener = load_module("qa_worker_listener", "scripts/qa_worker_listener.py")
project_sync = load_module("qa_project_sync", "scripts/qa_project_sync.py")
CONFIG = json.loads((ROOT / "config" / "qa_worker.json").read_text(encoding="utf-8"))


def candidate(pr: int, priority, created: str, comment_id: int):
    return {
        "target_pr": pr,
        "command_id": f"cmd-{pr}",
        "exact_head": f"{pr:040x}"[-40:],
        "qa_mode": "FULL",
        "priority": priority,
        "command_created_at": created,
        "command_comment_id": comment_id,
        "status": "READY",
        "updated_at": created,
        "review_id": None,
    }


def epoch_lines(head: str):
    review_digest = "1" * 64
    gate_digest = "2" * 64
    policy_digest = "3" * 64
    evidence_digest = aggregate_digest(head, review_digest, gate_digest, policy_digest)
    return [
        "EVIDENCE_EPOCH",
        "epoch_version=1",
        f"snapshot_head={head}",
        f"review_digest={review_digest}",
        f"gate_digest={gate_digest}",
        f"policy_digest={policy_digest}",
        f"evidence_digest={evidence_digest}",
    ]


def valid_command_comment(pr: int, comment_id: int, head: str):
    body = "\n".join([
        listener.COMMAND_HEADER,
        f"command_id=cmd-{comment_id}",
        f"target_pr={pr}",
        "controller=ChatGPT",
        "executor=AGY",
        "role=QA_EXECUTOR",
        f"exact_head={head}",
        "qa_mode=FULL",
        "result_sink=PR_REVIEW",
        "allow_issue_create=false",
        "allow_merge=false",
        "allow_fast_marker=false",
        "allow_code_mutation=false",
        "project_lifecycle_mutation=false",
        "",
        *epoch_lines(head),
    ])
    return {
        "id": comment_id,
        "created_at": f"2026-09-14T10:{comment_id:02d}:00Z",
        "body": body,
        "author_association": "OWNER",
        "user": {"login": "rassvetpublic-spec"},
        "html_url": f"https://example.invalid/{comment_id}",
    }


def valid_result_review(pr: int, command_id: str, head: str, review_id: int = 100):
    body = "\n".join([
        listener.RESULT_HEADER,
        f"command_id={command_id}",
        f"target_pr={pr}",
        "controller=ChatGPT",
        "executor=AGY",
        "role=QA_EXECUTOR",
        f"exact_head={head}",
        "qa_mode=FULL",
        "result_sink=PR_REVIEW",
        "verdict=QA PASS",
        "blocking_findings=0",
        "follow_up_candidates=0",
        "",
        *epoch_lines(head),
        "",
        "FOLLOW_UP_CANDIDATES",
    ])
    return {
        "id": review_id,
        "body": body,
        "author_association": "OWNER",
        "user": {"login": "rassvetpublic-spec"},
        "commit_id": head,
        "state": "COMMENTED",
        "submitted_at": "2026-09-14T11:00:00Z",
    }


def test_queue_policy_is_project_priority_then_command_fifo():
    policy = CONFIG["queue_policy"]
    assert policy["mode"] == "PROJECT_PRIORITY_COMMAND_FIFO"
    assert policy["priority_field"] == "Приоритет"
    assert policy["priority_order"] == ["P0", "P1", "P2", "P3"]
    assert policy["fallback"] == "COMMAND_FIFO"
    assert policy["allow_title_priority"] is False
    assert policy["promotion_store_adapter"] == "DISABLED_UNTIL_ISSUE_98"


def test_p0_overtakes_p1_but_fifo_is_preserved_inside_priority():
    items = [
        candidate(20, "P1", "2026-09-14T09:00:00Z", 20),
        candidate(30, "P0", "2026-09-14T10:00:00Z", 30),
        candidate(10, "P0", "2026-09-14T08:00:00Z", 10),
        candidate(5, None, "2026-09-14T07:00:00Z", 5),
    ]
    ordered = sorted(items, key=lambda item: listener.candidate_sort_key(item, CONFIG))
    assert [item["target_pr"] for item in ordered] == [10, 30, 20, 5]


def test_fifo_tie_breaker_is_comment_id_then_pr_number():
    items = [
        candidate(30, "P2", "2026-09-14T10:00:00Z", 8),
        candidate(20, "P2", "2026-09-14T10:00:00Z", 7),
        candidate(10, "P2", "2026-09-14T10:00:00Z", 7),
    ]
    ordered = sorted(items, key=lambda item: listener.candidate_sort_key(item, CONFIG))
    assert [item["target_pr"] for item in ordered] == [10, 20, 30]


def test_project_priority_failure_degrades_only_to_fifo():
    class BrokenGitHub:
        def graphql(self, query, variables):
            raise RuntimeError("нет Project")

    priorities, source = listener.project_priority_map(BrokenGitHub(), CONFIG)
    assert priorities == {}
    assert source == "COMMAND_FIFO"


def test_compact_table_is_russian_and_bounded():
    state = listener.empty_state()
    for number in range(1, 13):
        item = candidate(number, "P1", f"2026-09-14T10:{number:02d}:00Z", number)
        state["candidates"][listener.candidate_key(number, item["command_id"], item["exact_head"])] = item
    text = listener.table_text(state, CONFIG, limit=100)
    assert "Последние QA:" in text
    assert "Приоритет" in text
    assert "Статус" in text
    assert "Ревью" in text
    assert "Review" not in text
    assert "Ожидают: 12" in text
    assert text.count("| #") == CONFIG["recent_qa_output"]["max_limit"]


def test_human_output_language_is_russian():
    assert CONFIG["human_output_language"] == "ru"
    labels = CONFIG["recent_qa_output"]["status_labels"]
    assert labels["READY"] == "Готов к QA"
    assert labels["RUNNING"] == "На проверке"
    assert labels["PASS"] == "QA пройден"


def test_project_projection_has_no_second_state_or_final_authority_and_listener_never_writes_project():
    assert CONFIG["project"]["schema_mode"] == "EXISTING_FIELDS_ONLY"
    assert set(CONFIG["project"]["managed_fields"]) == {
        "Статус", "Исполнение", "Проверяющий", "Доказательство"
    }
    project_source = (ROOT / "scripts" / "qa_project_sync.py").read_text(encoding="utf-8")
    listener_source = (ROOT / "scripts" / "qa_worker_listener.py").read_text(encoding="utf-8")
    assert "qa_state_field" not in project_source
    assert "createProjectV2Field" not in project_source
    assert set(project_sync.STATE_MAP) == {"READY", "IN_REVIEW", "STALE"}
    assert "PASS" not in project_sync.STATE_MAP
    assert "BLOCKED" not in project_sync.STATE_MAP
    assert "qa_project_sync" not in listener_source
    assert "sync_project(" not in listener_source


def test_token_budget_is_shared_with_review_and_idle_is_zero():
    budget = CONFIG["token_budget"]
    assert budget["soft_input_tokens"] == 24000
    assert budget["max_input_tokens"] == 32000
    assert budget["max_output_tokens"] == 4000
    assert budget["hard_total_model_tokens"] == 40000
    assert budget["idle_poll_llm_tokens"] == 0
    assert CONFIG["review_policy"]["extra_token_budget"] == 0


def test_latest_malformed_command_fails_closed_without_old_fallback():
    head = "a" * 40
    old = valid_command_comment(17, 10, head)
    newest = valid_command_comment(17, 11, head)
    newest["body"] = newest["body"].replace("allow_merge=false", "allow_merge=true")
    assert listener.validate_command(old, 17, CONFIG) is not None
    assert listener.latest_authoritative_command_from_comments([old, newest], 17, CONFIG) is None


def test_command_requires_complete_valid_epoch():
    head = "b" * 40
    valid = valid_command_comment(22, 12, head)
    assert listener.validate_command(valid, 22, CONFIG) is not None
    invalid = dict(valid)
    invalid["body"] = valid["body"].replace("review_digest=" + "1" * 64, "review_digest=broken")
    assert listener.validate_command(invalid, 22, CONFIG) is None
    missing = dict(valid)
    missing["body"] = "\n".join(line for line in valid["body"].splitlines() if line != "EVIDENCE_EPOCH")
    assert listener.validate_command(missing, 22, CONFIG) is None


def test_claim_epoch_fails_closed_on_live_drift(monkeypatch):
    head = "c" * 40
    comment = valid_command_comment(23, 13, head)
    command = listener.validate_command(comment, 23, CONFIG)
    assert command is not None
    drift = dict(command["epoch"])
    drift["review_digest"] = "9" * 64
    monkeypatch.setattr(listener, "live_evidence_snapshot", lambda gh, pr, exact_head: drift)
    fresh, reason = listener.command_epoch_is_current(object(), 23, command)
    assert fresh is False
    assert reason == "EVIDENCE_DRIFT:review_digest"


def test_result_requires_trusted_complete_envelope_and_matching_epoch():
    head = "d" * 40
    comment = valid_command_comment(24, 14, head)
    command = listener.validate_command(comment, 24, CONFIG)
    assert command is not None
    valid_review = valid_result_review(24, command["command_id"], head)

    class FakeGitHub:
        def __init__(self, reviews):
            self.reviews = reviews
        def paged(self, path, limit_pages=20):
            return list(self.reviews)

    result = listener.result_for_command(FakeGitHub([valid_review]), 24, comment, command, CONFIG)
    assert result is not None
    assert result["fields"]["verdict"] == "QA PASS"

    untrusted = dict(valid_review)
    untrusted["user"] = {"login": "someone-else"}
    untrusted["author_association"] = "CONTRIBUTOR"
    assert listener.result_for_command(FakeGitHub([untrusted]), 24, comment, command, CONFIG) is None

    malformed = dict(valid_review)
    malformed["body"] = valid_review["body"].replace("blocking_findings=0", "blocking_findings=1")
    assert listener.result_for_command(FakeGitHub([malformed]), 24, comment, command, CONFIG) is None
