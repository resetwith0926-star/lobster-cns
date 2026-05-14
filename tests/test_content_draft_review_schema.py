from __future__ import annotations

from datetime import datetime

import pytest
from pydantic import ValidationError

from app.schemas.content_draft_review import ContentDraftReviewCreate, ContentDraftReviewRead


def _valid_payload():
    return {
        "draft_id": 1,
        "status": "needs_revision",
        "overall_score": 80,
        "tone_score": 78,
        "medical_safety_score": 90,
        "cta_safety_score": 75,
        "discipline_score": 82,
        "risk_flags_json": '[{"type":"medical_claim","severity":"medium"}]',
        "suggested_rewrites_json": '[{"before":"x","after":"y"}]',
        "review_summary": "Tone is good, reduce claim strength.",
        "raw_review_json": '{"ok": true}',
    }


def test_valid_content_draft_review_create_passes():
    model = ContentDraftReviewCreate.model_validate(_valid_payload())
    assert model.status == "needs_revision"
    assert model.overall_score == 80


def test_invalid_status_is_rejected():
    payload = _valid_payload()
    payload["status"] = "approved"
    with pytest.raises(ValidationError):
        ContentDraftReviewCreate.model_validate(payload)


def test_score_below_zero_is_rejected():
    payload = _valid_payload()
    payload["tone_score"] = -1
    with pytest.raises(ValidationError):
        ContentDraftReviewCreate.model_validate(payload)


def test_score_above_hundred_is_rejected():
    payload = _valid_payload()
    payload["medical_safety_score"] = 101
    with pytest.raises(ValidationError):
        ContentDraftReviewCreate.model_validate(payload)


def test_content_draft_review_read_serializes_timestamps():
    payload = _valid_payload()
    payload.update(
        {
            "id": 9,
            "reviewed_by": "quality_reviewer",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
    )
    model = ContentDraftReviewRead.model_validate(payload)
    dumped = model.model_dump()
    assert dumped["id"] == 9
    assert "created_at" in dumped
    assert "updated_at" in dumped
