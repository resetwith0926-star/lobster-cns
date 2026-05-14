from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class AgentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    role: str
    platform: Optional[str]
    description: str
    status: str
    permissions_json: str
    is_enabled: bool
    last_heartbeat_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

