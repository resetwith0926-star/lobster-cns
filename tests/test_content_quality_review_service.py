from __future__ import annotations

import json

from app.models.agent import Agent
from app.models.content_draft_review import ContentDraftReview
from app.models.event import Event
from app.services.content_draft_service import ContentDraftService
from app.services.content_quality_review_service import ContentQualityReviewService
from app.services.llm_provider import LLMResponse
from app.services.task_queue import TaskQueue


class MockLLMProvider:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def chat(self, messages, temperature=0.2, task_id=None, json_mode=True):
        self.calls.append({"messages": messages, "temperature": temperature, "task_id": task_id, "json_mode": json_mode})
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def llm_json_response(payload: dict, success: bool = True, error: str | None = None):
    raw = json.dumps(payload, ensure_ascii=False)
    return LLMResponse(
        provider="mock",
        model="mock-model",
        raw_text=raw,
        parsed_json=payload if success else None,
        latency_ms=2,
        success=success,
        error=error,
    )


def llm_text_response(raw_text: str, success: bool = True, error: str | None = None):
    return LLMResponse(
        provider="mock",
        model="mock-model",
        raw_text=raw_text,
        parsed_json=None,
        latency_ms=2,
        success=success,
        error=error,
    )


def _valid_review_payload():
    return {
        "contract_version": "content_review.v1",
        "status": "pass",
        "overall_score": 88,
        "tone_score": 90,
        "medical_safety_score": 86,
        "cta_safety_score": 84,
        "discipline_score": 80,
        "risk_flags": [],
        "suggested_rewrites": [],
        "review_summary": "整體可用，語氣穩定。",
        "approval_recommendation": "approve",
    }


def _make_draft_with_text(db_session, draft_text: str = "這是一段草稿內容"):
    task = TaskQueue(db_session).create_task("Quality review task", "desc")
    draft_service = ContentDraftService(db_session)
    draft = draft_service.create_draft_from_task(task.id, title="Draft A")
    draft.draft_text = draft_text
    db_session.add(draft)
    db_session.commit()
    db_session.refresh(draft)
    return task, draft


def test_review_draft_creates_review_from_valid_json(db_session):
    _task, draft = _make_draft_with_text(db_session)
    provider = MockLLMProvider([llm_json_response(_valid_review_payload())])
    review = ContentQualityReviewService(db_session).review_draft(draft.id, llm_provider=provider)
    assert isinstance(review, ContentDraftReview)
    assert review.draft_id == draft.id


def test_review_draft_rejects_missing_draft(db_session):
    service = ContentQualityReviewService(db_session)
    try:
        service.review_draft(99999, llm_provider=MockLLMProvider([llm_json_response(_valid_review_payload())]))
    except ValueError as exc:
        assert "not found" in str(exc).lower()
    else:
        raise AssertionError("Expected missing draft to raise ValueError")


def test_review_draft_rejects_empty_draft_text(db_session):
    task = TaskQueue(db_session).create_task("No text", "desc")
    draft = ContentDraftService(db_session).create_draft_from_task(task.id)
    service = ContentQualityReviewService(db_session)
    try:
        service.review_draft(draft.id, llm_provider=MockLLMProvider([llm_json_response(_valid_review_payload())]))
    except ValueError as exc:
        assert "draft text is required" in str(exc).lower()
    else:
        raise AssertionError("Expected empty draft text to raise ValueError")


def test_review_draft_stores_scores_risk_flags_and_rewrites(db_session):
    _task, draft = _make_draft_with_text(db_session)
    payload = _valid_review_payload()
    payload["risk_flags"] = [{"type": "other", "severity": "low", "text": "x", "reason": "y", "suggested_fix": "z"}]
    payload["suggested_rewrites"] = [{"original": "a", "rewrite": "b", "reason": "c"}]
    review = ContentQualityReviewService(db_session).review_draft(draft.id, llm_provider=MockLLMProvider([llm_json_response(payload)]))
    assert review.overall_score == 88
    assert json.loads(review.risk_flags_json or "[]")[0]["type"] == "other"
    assert json.loads(review.suggested_rewrites_json or "[]")[0]["rewrite"] == "b"


def test_approval_recommendation_mapping(db_session):
    _task, draft = _make_draft_with_text(db_session)
    service = ContentQualityReviewService(db_session)
    p1 = _valid_review_payload()
    p1["approval_recommendation"] = "approve"
    p1["status"] = "needs_revision"
    r1 = service.review_draft(draft.id, llm_provider=MockLLMProvider([llm_json_response(p1)]))
    assert r1.status == "pass"

    p2 = _valid_review_payload()
    p2["approval_recommendation"] = "revise"
    r2 = service.review_draft(draft.id, llm_provider=MockLLMProvider([llm_json_response(p2)]))
    assert r2.status == "needs_revision"

    p3 = _valid_review_payload()
    p3["approval_recommendation"] = "block"
    r3 = service.review_draft(draft.id, llm_provider=MockLLMProvider([llm_json_response(p3)]))
    assert r3.status == "blocked"


def test_high_medical_claim_prevents_pass(db_session):
    _task, draft = _make_draft_with_text(db_session)
    payload = _valid_review_payload()
    payload["risk_flags"] = [
        {"type": "medical_claim", "severity": "high", "text": "保證三天逆轉", "reason": "誇大醫療效果", "suggested_fix": "改成教育敘述"}
    ]
    review = ContentQualityReviewService(db_session).review_draft(draft.id, llm_provider=MockLLMProvider([llm_json_response(payload)]))
    assert review.status == "blocked"


def test_scores_are_clamped(db_session):
    _task, draft = _make_draft_with_text(db_session)
    payload = _valid_review_payload()
    payload["overall_score"] = 999
    payload["tone_score"] = -5
    review = ContentQualityReviewService(db_session).review_draft(draft.id, llm_provider=MockLLMProvider([llm_json_response(payload)]))
    assert review.overall_score == 100
    assert review.tone_score == 0


def test_invalid_json_triggers_single_repair(db_session):
    _task, draft = _make_draft_with_text(db_session)
    provider = MockLLMProvider(
        [
            llm_text_response("not json", success=True),
            llm_json_response(_valid_review_payload()),
        ]
    )
    review = ContentQualityReviewService(db_session).review_draft(draft.id, llm_provider=provider)
    assert review.status == "pass"
    assert len(provider.calls) == 2
    assert provider.calls[0]["json_mode"] is True
    assert provider.calls[1]["json_mode"] is True


def test_repair_failure_logs_error_and_raises(db_session):
    task, draft = _make_draft_with_text(db_session)
    provider = MockLLMProvider([llm_text_response("bad"), llm_text_response("still bad")])
    service = ContentQualityReviewService(db_session)
    try:
        service.review_draft(draft.id, llm_provider=provider)
    except ValueError as exc:
        assert "failed" in str(exc).lower() or "error" in str(exc).lower()
    else:
        raise AssertionError("Expected repair failure to raise ValueError")

    error_event = (
        db_session.query(Event)
        .filter(Event.event_type == "error")
        .filter(Event.task_id == task.id)
        .order_by(Event.id.desc())
        .first()
    )
    assert error_event is not None


def test_review_does_not_change_content_draft_status(db_session):
    _task, draft = _make_draft_with_text(db_session)
    draft.status = "needs_revision"
    db_session.add(draft)
    db_session.commit()
    service = ContentQualityReviewService(db_session)
    service.review_draft(draft.id, llm_provider=MockLLMProvider([llm_json_response(_valid_review_payload())]))
    db_session.refresh(draft)
    assert draft.status == "needs_revision"


def test_review_logs_started_and_completed_events(db_session):
    task, draft = _make_draft_with_text(db_session)
    service = ContentQualityReviewService(db_session)
    service.review_draft(draft.id, llm_provider=MockLLMProvider([llm_json_response(_valid_review_payload())]))
    started = (
        db_session.query(Event)
        .filter(Event.event_type == "content_quality_review_started", Event.task_id == task.id)
        .first()
    )
    completed = (
        db_session.query(Event)
        .filter(Event.event_type == "content_quality_review_completed", Event.task_id == task.id)
        .first()
    )
    assert started is not None
    assert completed is not None


def test_get_latest_review_and_list_reviews(db_session):
    _task, draft = _make_draft_with_text(db_session)
    service = ContentQualityReviewService(db_session)
    r1 = service.review_draft(draft.id, llm_provider=MockLLMProvider([llm_json_response(_valid_review_payload())]))
    p2 = _valid_review_payload()
    p2["overall_score"] = 65
    r2 = service.review_draft(draft.id, llm_provider=MockLLMProvider([llm_json_response(p2)]))

    latest = service.get_latest_review(draft.id)
    all_reviews = service.list_reviews(draft.id)

    assert latest is not None and latest.id == r2.id
    assert len(all_reviews) == 2
    assert {r.id for r in all_reviews} == {r1.id, r2.id}


def test_no_agents_enabled_during_review_flow(db_session):
    _task, draft = _make_draft_with_text(db_session)
    service = ContentQualityReviewService(db_session)
    service.review_draft(draft.id, llm_provider=MockLLMProvider([llm_json_response(_valid_review_payload())]))
    enabled_count = db_session.query(Agent).filter(Agent.is_enabled.is_(True)).count()
    # conftest does not auto-seed registry; still we assert no accidental enablement side-effect.
    assert enabled_count == 0
