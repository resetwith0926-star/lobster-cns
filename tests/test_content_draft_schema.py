from __future__ import annotations

from datetime import datetime

import pytest
from pydantic import ValidationError

from app.schemas.content_draft import ContentDraftCreate, ContentDraftRead


def test_content_draft_create_valid_data_passes():
    payload = ContentDraftCreate(task_id=1, title="ResetWith 一週內容草稿")
    assert payload.task_id == 1
    assert payload.title == "ResetWith 一週內容草稿"
    assert payload.status == "draft"
    assert payload.version == 1


def test_content_draft_create_invalid_status_rejected():
    with pytest.raises(ValidationError):
        ContentDraftCreate(task_id=1, title="Bad status", status="published")


def test_content_draft_create_version_below_one_rejected():
    with pytest.raises(ValidationError):
        ContentDraftCreate(task_id=1, title="Bad version", version=0)


def test_content_draft_read_serializes_timestamps():
    payload = ContentDraftRead(
        id=9,
        task_id=3,
        title="讀取測試",
        status="approved",
        version=1,
        created_by="ceo_agent",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        reviewed_at=datetime.utcnow(),
    )
    dumped = payload.model_dump()
    assert isinstance(dumped["created_at"], datetime)
    assert isinstance(dumped["updated_at"], datetime)
