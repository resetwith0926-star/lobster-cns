from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.agent import AgentRead
from app.security import require_admin_secret
from app.services.agent_registry import AgentRegistry


router = APIRouter(
    prefix="/agents",
    tags=["agents"],
    dependencies=[Depends(require_admin_secret)],
)


@router.get("", response_model=list[AgentRead])
def list_agents(db: Session = Depends(get_db)):
    return AgentRegistry(db).list_agents()


@router.get("/{agent_id}", response_model=AgentRead)
def get_agent(agent_id: str, db: Session = Depends(get_db)):
    agent = AgentRegistry(db).get_agent(agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found.")
    return agent

