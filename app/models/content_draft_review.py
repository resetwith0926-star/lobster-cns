from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ContentDraftReview(Base):
    __tablename__ = "content_draft_reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    draft_id: Mapped[int] = mapped_column(ForeignKey("content_drafts.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="needs_revision", index=True)
    overall_score: Mapped[int] = mapped_column(Integer, nullable=False)
    tone_score: Mapped[int] = mapped_column(Integer, nullable=False)
    medical_safety_score: Mapped[int] = mapped_column(Integer, nullable=False)
    cta_safety_score: Mapped[int] = mapped_column(Integer, nullable=False)
    discipline_score: Mapped[int] = mapped_column(Integer, nullable=False)
    risk_flags_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    suggested_rewrites_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    review_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    raw_review_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[str] = mapped_column(String(100), nullable=False, default="quality_reviewer")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
