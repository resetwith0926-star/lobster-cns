from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.task import TaskComplete, TaskCreate, TaskRead
from app.security import require_admin_secret
from app.services.ceo_agent import CEOAgent
from app.services.deepseek_provider import DeepSeekLLMProvider
from app.services.task_queue import TaskQueue


router = APIRouter(
    prefix="/tasks",
    tags=["tasks"],
    dependencies=[Depends(require_admin_secret)],
)


@router.post("", response_model=TaskRead)
def create_task(payload: TaskCreate, db: Session = Depends(get_db)):
    return TaskQueue(db).create_task(
        title=payload.title,
        description=payload.description,
        created_by=payload.created_by,
    )


@router.get("", response_model=list[TaskRead])
def list_tasks(db: Session = Depends(get_db)):
    return TaskQueue(db).list_tasks()


@router.get("/{task_id}", response_model=TaskRead)
def get_task(task_id: int, db: Session = Depends(get_db)):
    task = TaskQueue(db).get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found.")
    return task


@router.post("/{task_id}/review", response_model=TaskRead)
def review_task(task_id: int, db: Session = Depends(get_db)):
    try:
        CEOAgent(db, DeepSeekLLMProvider(db)).review_task(task_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return TaskQueue(db).require_task(task_id)


@router.post("/{task_id}/complete", response_model=TaskRead)
def complete_task(
    task_id: int,
    payload: TaskComplete,
    db: Session = Depends(get_db),
):
    try:
        return TaskQueue(db).complete_task(task_id, result=payload.result, actor="admin")
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{task_id}/cancel", response_model=TaskRead)
def cancel_task(task_id: int, db: Session = Depends(get_db)):
    try:
        return TaskQueue(db).cancel_task(task_id, actor="admin")
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

