from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.llm_call import LLMCall
from app.schemas.llm_call import LLMCallRead
from app.security import require_admin_secret


router = APIRouter(
    prefix="/llm-calls",
    tags=["llm-calls"],
    dependencies=[Depends(require_admin_secret)],
)


@router.get("", response_model=list[LLMCallRead])
def list_llm_calls(db: Session = Depends(get_db)):
    stmt = select(LLMCall).order_by(LLMCall.created_at.desc()).limit(100)
    return list(db.scalars(stmt))

