from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class EventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_type: str
    actor: str
    task_id: Optional[int]
    message: str
    metadata_json: Optional[str]
    created_at: datetime

