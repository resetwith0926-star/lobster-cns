from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class LLMCallRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    provider: str
    model: str
    task_id: Optional[int]
    prompt_preview: str
    raw_response: Optional[str]
    parsed_json: Optional[str]
    latency_ms: Optional[float]
    success: bool
    error: Optional[str]
    created_at: datetime

