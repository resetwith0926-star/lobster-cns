from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.content_draft import (
    ContentDraftCreate,
    ContentDraftRead,
    ContentDraftReviseRequest,
    ContentDraftStatus,
    ContentDraftStatusUpdateRequest,
)
from app.security import require_admin_secret
from app.services.content_draft_service import ContentDraftService


router = APIRouter(
    prefix="/drafts",
    tags=["drafts"],
    dependencies=[Depends(require_admin_secret)],
)


@router.post("", response_model=ContentDraftRead)
def create_draft(payload: ContentDraftCreate, db: Session = Depends(get_db)):
    try:
        return ContentDraftService(db).create_draft_from_task(
            task_id=payload.task_id,
            title=payload.title,
            channel_hint=payload.channel_hint,
            target_audience=payload.target_audience,
            created_by=payload.created_by,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("", response_model=list[ContentDraftRead])
def list_drafts(
    status: Optional[ContentDraftStatus] = Query(default=None),
    db: Session = Depends(get_db),
):
    return ContentDraftService(db).list_drafts(status=status)


@router.get("/{draft_id}", response_model=ContentDraftRead)
def get_draft(draft_id: int, db: Session = Depends(get_db)):
    draft = ContentDraftService(db).get_draft(draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft not found.")
    return draft


@router.post("/{draft_id}/generate", response_model=ContentDraftRead)
def generate_draft(draft_id: int, db: Session = Depends(get_db)):
    try:
        return ContentDraftService(db).generate_draft(draft_id=draft_id, actor="ceo_agent")
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if "was not found" in message else 400
        raise HTTPException(status_code=status_code, detail=message) from exc


@router.post("/{draft_id}/revise", response_model=ContentDraftRead)
def revise_draft(
    draft_id: int,
    payload: ContentDraftReviseRequest,
    db: Session = Depends(get_db),
):
    try:
        return ContentDraftService(db).revise_draft(
            draft_id=draft_id,
            revision_instruction=payload.revision_instruction,
            actor="admin",
        )
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if "was not found" in message else 400
        raise HTTPException(status_code=status_code, detail=message) from exc


@router.post("/{draft_id}/status", response_model=ContentDraftRead)
def update_draft_status(
    draft_id: int,
    payload: ContentDraftStatusUpdateRequest,
    db: Session = Depends(get_db),
):
    try:
        return ContentDraftService(db).update_status(
            draft_id=draft_id,
            status=payload.status,
            review_notes=payload.review_notes,
            actor="admin",
        )
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if "was not found" in message else 400
        raise HTTPException(status_code=status_code, detail=message) from exc
