from __future__ import annotations

import json
from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.event import Event


class EventLog:
    def __init__(self, db: Session):
        self.db = db

    def log(
        self,
        event_type: str,
        actor: str = "system",
        task_id: Optional[int] = None,
        message: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Event:
        event = Event(
            event_type=event_type,
            actor=actor,
            task_id=task_id,
            message=message,
            metadata_json=json.dumps(metadata or {}, ensure_ascii=False),
        )
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event

    def list_recent(self, limit: int = 100):
        stmt = select(Event).order_by(Event.created_at.desc()).limit(limit)
        return list(self.db.scalars(stmt))

    def list_for_task(self, task_id: int):
        stmt = (
            select(Event)
            .where(Event.task_id == task_id)
            .order_by(Event.created_at.asc())
        )
        return list(self.db.scalars(stmt))

