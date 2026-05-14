from __future__ import annotations

from datetime import datetime
import json
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class TaskCreate(BaseModel):
    title: str = Field(min_length=1)
    description: str = ""
    created_by: str = "admin"


class TaskComplete(BaseModel):
    result: str = ""


class TaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    status: str
    task_type: Optional[str]
    priority: Optional[str]
    risk_level: Optional[str]
    suggested_agent_role: Optional[str]
    primary_agent_role: Optional[str]
    supporting_agent_roles_json: Optional[str]
    supporting_agent_roles: List[str] = Field(default_factory=list)
    ceo_decision_json: Optional[str]
    ceo_decision_text: Optional[str]
    reasoning_summary: Optional[str]
    result: Optional[str]
    error: Optional[str]
    is_archived: bool
    archived_at: Optional[datetime]
    created_by: str
    created_at: datetime
    updated_at: datetime
    reviewed_at: Optional[datetime]

    @model_validator(mode="before")
    @classmethod
    def normalize_supporting_roles(cls, data: Any) -> Any:
        if isinstance(data, dict):
            payload: Dict[str, Any] = dict(data)
            if "supporting_agent_roles" not in payload or payload.get("supporting_agent_roles") is None:
                raw = payload.get("supporting_agent_roles_json")
                payload["supporting_agent_roles"] = _parse_roles(raw)
            return payload

        if hasattr(data, "supporting_agent_roles_json"):
            raw = getattr(data, "supporting_agent_roles_json")
            if not hasattr(data, "supporting_agent_roles") or getattr(data, "supporting_agent_roles", None) is None:
                setattr(data, "supporting_agent_roles", _parse_roles(raw))
        return data


def _parse_roles(raw: Optional[str]) -> List[str]:
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if isinstance(parsed, list):
        return [str(item) for item in parsed]
    return []
