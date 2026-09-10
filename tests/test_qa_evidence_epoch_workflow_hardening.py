from pathlib import Path


def workflow_text() -> str:
    return (
        Path(__file__).resolve().parents[1]
        / ".github"
        / "workflows"
        / "qa-result-bridge.yml"
    ).read_text(encoding="utf-8")


def test_final_stage_refetches_owner_comments_before_fast_marker():
    workflow = workflow_text()
    assert "issue-comments-final.json" in workflow
    assert "superseding owner QA-COMMAND appeared after QA-ACCEPT" in workflow
    final_validate = workflow.rfind("python scripts/qa_evidence_epoch.py validate")
    final_comments = workflow.rfind("--comments-path issue-comments-final.json")
    fast_publish = workflow.rfind("gh api --method POST")
    assert 0 <= final_validate < final_comments < fast_publish


def test_nested_review_comment_pagination_fails_closed_twice():
    workflow = workflow_text()
    assert workflow.count("comments.pageInfo.hasNextPage") >= 2
    assert workflow.count("review comment inventory") >= 2
    assert "comments(first:100){nodes{id body path line startLine outdated} pageInfo{hasNextPage endCursor}}" in workflow


def test_competing_structured_qa_result_is_rejected_before_fast_twice():
    workflow = workflow_text()
    marker = "REVIEW_DRIFT: competing structured QA-RESULT after active QA-COMMAND"
    assert workflow.count(marker) >= 2
    assert workflow.count("selected QA review absent") >= 2
    assert "REVIEW_ID: ${{ steps.attest.outputs.review_id }}" in workflow
    fast_publish = workflow.rfind("gh api --method POST")
    final_guard = workflow.rfind(marker)
    final_epoch = workflow.rfind("python scripts/qa_evidence_epoch.py validate")
    assert 0 <= final_guard < final_epoch < fast_publish
