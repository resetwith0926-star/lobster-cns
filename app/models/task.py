from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending", index=True)
    task_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    priority: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    risk_level: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    suggested_agent_role: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    primary_agent_role: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    supporting_agent_roles_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ceo_decision_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ceo_decision_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reasoning_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    result: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_archived: Mapped[bool] = mapped_column(nullable=False, default=False, index=True)
    archived_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_by: Mapped[str] = mapped_column(String(100), nullable=False, default="admin")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
