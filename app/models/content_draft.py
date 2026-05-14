from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ContentDraft(Base):
    __tablename__ = "content_drafts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    channel_hint: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    target_audience: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    source_decision_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    draft_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="draft", index=True)
    generation_state: Mapped[str] = mapped_column(String(50), nullable=False, default="idle", index=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_error_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    is_archived: Mapped[bool] = mapped_column(nullable=False, default=False, index=True)
    archived_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    review_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_by: Mapped[str] = mapped_column(String(100), nullable=False, default="ceo_agent")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
