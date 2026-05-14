from __future__ import annotations

import json
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.agent import Agent


DEFAULT_AGENTS = [
    {
        "id": "ceo_agent",
        "name": "CEO Agent",
        "role": "ceo",
        "platform": "internal",
        "description": "Central CEO brain. Reviews tasks and produces structured decisions only.",
        "status": "ready",
        "permissions": ["review_tasks", "write_decisions", "write_memory", "write_events"],
        "is_enabled": True,
    },
    {
        "id": "facebook_page_agent",
        "name": "Facebook Page Agent",
        "role": "facebook_page_agent",
        "platform": "facebook",
        "description": "Future placeholder for Facebook Page work. Disabled in v0.1.",
        "status": "placeholder",
        "permissions": [],
        "is_enabled": False,
    },
    {
        "id": "facebook_personal_agent",
        "name": "Facebook Personal Agent",
        "role": "facebook_personal_agent",
        "platform": "facebook",
        "description": "Future placeholder for personal Facebook work. Disabled in v0.1.",
        "status": "placeholder",
        "permissions": [],
        "is_enabled": False,
    },
    {
        "id": "instagram_agent",
        "name": "Instagram Agent",
        "role": "instagram_agent",
        "platform": "instagram",
        "description": "Future placeholder for Instagram work. Disabled in v0.1.",
        "status": "placeholder",
        "permissions": [],
        "is_enabled": False,
    },
    {
        "id": "x_agent",
        "name": "X Agent",
        "role": "x_agent",
        "platform": "x",
        "description": "Future placeholder for X work. Disabled in v0.1.",
        "status": "placeholder",
        "permissions": [],
        "is_enabled": False,
    },
    {
        "id": "line_agent",
        "name": "LINE Agent",
        "role": "line_agent",
        "platform": "line",
        "description": "Future placeholder for LINE work. Disabled in v0.1.",
        "status": "placeholder",
        "permissions": [],
        "is_enabled": False,
    },
    {
        "id": "telegram_agent",
        "name": "Telegram Agent",
        "role": "telegram_agent",
        "platform": "telegram",
        "description": "Future placeholder for Telegram work. Disabled in v0.1.",
        "status": "placeholder",
        "permissions": [],
        "is_enabled": False,
    },
    {
        "id": "content_agent",
        "name": "Content Agent",
        "role": "content_agent",
        "platform": "internal",
        "description": "Future placeholder for content drafting. Disabled in v0.1.",
        "status": "placeholder",
        "permissions": [],
        "is_enabled": False,
    },
    {
        "id": "sales_agent",
        "name": "Sales Agent",
        "role": "sales_agent",
        "platform": "internal",
        "description": "Future placeholder for sales support. Disabled in v0.1.",
        "status": "placeholder",
        "permissions": [],
        "is_enabled": False,
    },
    {
        "id": "dev_agent",
        "name": "Development Agent",
        "role": "dev_agent",
        "platform": "internal",
        "description": "Future placeholder for development tasks. Disabled in v0.1.",
        "status": "placeholder",
        "permissions": [],
        "is_enabled": False,
    },
]


class AgentRegistry:
    def __init__(self, db: Session):
        self.db = db

    def ensure_default_agents(self) -> None:
        now = datetime.utcnow()
        for item in DEFAULT_AGENTS:
            agent = self.db.get(Agent, item["id"])
            if agent is None:
                agent = Agent(
                    id=item["id"],
                    name=item["name"],
                    role=item["role"],
                    platform=item["platform"],
                    description=item["description"],
                    status=item["status"],
                    permissions_json=json.dumps(item["permissions"], ensure_ascii=False),
                    is_enabled=item["is_enabled"],
                    created_at=now,
                    updated_at=now,
                )
                self.db.add(agent)
        self.db.commit()

    def list_agents(self) -> list[Agent]:
        stmt = select(Agent).order_by(Agent.id.asc())
        return list(self.db.scalars(stmt))

    def get_agent(self, agent_id: str) -> Optional[Agent]:
        return self.db.get(Agent, agent_id)

    def can_execute(self, agent_id: str) -> bool:
        agent = self.get_agent(agent_id)
        return bool(agent and agent.is_enabled)

    def ensure_can_execute(self, agent_id: str) -> None:
        if not self.can_execute(agent_id):
            raise PermissionError(f"Agent '{agent_id}' is disabled or missing.")
