from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.content_draft_review import ContentDraftReview
from app.schemas.content_draft_review import ContentDraftReviewRead
from app.security import require_admin_secret
from app.services.content_quality_review_service import ContentQualityReviewService


router = APIRouter(
    tags=["draft-reviews"],
    dependencies=[Depends(require_admin_secret)],
)


@router.post("/drafts/{draft_id}/review-quality", response_model=ContentDraftReviewRead)
def review_draft_quality(draft_id: int, db: Session = Depends(get_db)):
    try:
        return ContentQualityReviewService(db).review_draft(draft_id=draft_id, actor="quality_reviewer")
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if "not found" in message.lower() else 400
        raise HTTPException(status_code=status_code, detail=message) from exc


@router.get("/drafts/{draft_id}/reviews", response_model=list[ContentDraftReviewRead])
def list_draft_reviews(draft_id: int, db: Session = Depends(get_db)):
    return ContentQualityReviewService(db).list_reviews(draft_id=draft_id)


@router.get("/draft-reviews/{review_id}", response_model=ContentDraftReviewRead)
def get_draft_review(review_id: int, db: Session = Depends(get_db)):
    stmt = select(ContentDraftReview).where(ContentDraftReview.id == review_id).limit(1)
    review = db.scalars(stmt).first()
    if review is None:
        raise HTTPException(status_code=404, detail="Draft review not found.")
    return review
