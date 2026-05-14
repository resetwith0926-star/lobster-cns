from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


MemoryNamespace = Literal["business", "brand", "sales", "content", "system", "user"]
MemoryCategory = Literal["rule", "preference", "decision", "strategy", "warning", "note"]


class MemoryCreate(BaseModel):
    namespace: MemoryNamespace
    category: MemoryCategory
    content: str = Field(min_length=1)
    importance: int = Field(default=1, ge=1, le=5)
    source: str = "manual"
    task_id: Optional[int] = None


class MemoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    namespace: str
    category: str
    content: str
    importance: int
    source: Optional[str]
    task_id: Optional[int]
    created_at: datetime
    updated_at: datetime

