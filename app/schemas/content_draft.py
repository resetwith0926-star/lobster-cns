from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


ContentDraftStatus = Literal["draft", "needs_revision", "approved", "rejected"]
ContentDraftGenerationState = Literal["idle", "generating", "ready", "failed"]


class ContentDraftBase(BaseModel):
    task_id: int
    title: str = Field(min_length=1)
    channel_hint: Optional[str] = None
    target_audience: Optional[str] = None
    source_decision_json: Optional[str] = None
    draft_text: Optional[str] = None
    status: ContentDraftStatus = "draft"
    review_notes: Optional[str] = None
    version: int = Field(default=1, ge=1)
    created_by: str = "ceo_agent"


class ContentDraftCreate(ContentDraftBase):
    title: Optional[str] = Field(default=None, min_length=1)


class ContentDraftGenerateRequest(BaseModel):
    pass


class ContentDraftReviseRequest(BaseModel):
    revision_instruction: str = Field(min_length=1)


class ContentDraftStatusUpdateRequest(BaseModel):
    status: ContentDraftStatus
    review_notes: Optional[str] = None


class ContentDraftRead(ContentDraftBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    generation_state: ContentDraftGenerationState = "idle"
    retry_count: int = 0
    last_error: Optional[str] = None
    last_error_at: Optional[datetime] = None
    is_archived: bool = False
    archived_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    reviewed_at: Optional[datetime] = None


class ContentDraftListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_id: int
    title: str
    status: ContentDraftStatus
    generation_state: ContentDraftGenerationState = "idle"
    retry_count: int = 0
    is_archived: bool = False
    version: int
    updated_at: datetime
