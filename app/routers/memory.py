from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.memory import MemoryCreate, MemoryRead
from app.security import require_admin_secret
from app.services.memory_service import MemoryService


router = APIRouter(
    prefix="/memory",
    tags=["memory"],
    dependencies=[Depends(require_admin_secret)],
)


@router.get("", response_model=list[MemoryRead])
def list_memory(db: Session = Depends(get_db)):
    return MemoryService(db).list_memories()


@router.post("", response_model=MemoryRead)
def create_memory(payload: MemoryCreate, db: Session = Depends(get_db)):
    return MemoryService(db).create_memory(
        namespace=payload.namespace,
        category=payload.category,
        content=payload.content,
        importance=payload.importance,
        source=payload.source,
        task_id=payload.task_id,
        actor="admin",
    )


@router.get("/{memory_id}", response_model=MemoryRead)
def get_memory(memory_id: int, db: Session = Depends(get_db)):
    memory = MemoryService(db).get_memory(memory_id)
    if memory is None:
        raise HTTPException(status_code=404, detail="Memory not found.")
    return memory

