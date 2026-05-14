from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.event import EventRead
from app.security import require_admin_secret
from app.services.event_log import EventLog


router = APIRouter(
    prefix="/events",
    tags=["events"],
    dependencies=[Depends(require_admin_secret)],
)


@router.get("", response_model=list[EventRead])
def list_events(db: Session = Depends(get_db)):
    return EventLog(db).list_recent()

