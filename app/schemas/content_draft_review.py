from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


ContentDraftReviewStatus = Literal["pass", "needs_revision", "blocked"]


class ContentDraftReviewBase(BaseModel):
    draft_id: int
    status: ContentDraftReviewStatus
    overall_score: int = Field(ge=0, le=100)
    tone_score: int = Field(ge=0, le=100)
    medical_safety_score: int = Field(ge=0, le=100)
    cta_safety_score: int = Field(ge=0, le=100)
    discipline_score: int = Field(ge=0, le=100)
    risk_flags_json: Optional[str] = None
    suggested_rewrites_json: Optional[str] = None
    review_summary: Optional[str] = None
    raw_review_json: Optional[str] = None
    reviewed_by: str = "quality_reviewer"


class ContentDraftReviewCreate(ContentDraftReviewBase):
    pass


class ContentDraftReviewRead(ContentDraftReviewBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class ContentDraftReviewListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    draft_id: int
    status: ContentDraftReviewStatus
    overall_score: int = Field(ge=0, le=100)
    reviewed_by: str
    created_at: datetime
