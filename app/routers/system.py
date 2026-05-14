from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.agent import Agent
from app.models.event import Event
from app.models.llm_call import LLMCall
from app.models.memory import Memory
from app.models.task import Task
from app.security import require_admin_secret


router = APIRouter(
    prefix="/system",
    tags=["system"],
    dependencies=[Depends(require_admin_secret)],
)


@router.get("/status")
def system_status(db: Session = Depends(get_db)):
    return {
        "app_env": settings.app_env,
        "llm_provider": settings.llm_provider,
        "deepseek_model": settings.deepseek_model,
        "tasks": db.scalar(select(func.count(Task.id))),
        "agents": db.scalar(select(func.count(Agent.id))),
        "events": db.scalar(select(func.count(Event.id))),
        "memories": db.scalar(select(func.count(Memory.id))),
        "llm_calls": db.scalar(select(func.count(LLMCall.id))),
    }

