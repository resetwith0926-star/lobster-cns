from __future__ import annotations

from app.models.content_draft import ContentDraft
from app.models.content_draft_review import ContentDraftReview
from app.services.task_queue import TaskQueue


def _create_draft(db_session, title: str = "Draft for review") -> ContentDraft:
    task = TaskQueue(db_session).create_task("Review model task", "desc")
    draft = ContentDraft(task_id=task.id, title=title, status="draft", version=1, created_by="dashboard")
    db_session.add(draft)
    db_session.commit()
    db_session.refresh(draft)
    return draft


def test_can_create_content_draft_review_linked_to_draft(db_session):
    draft = _create_draft(db_session)
    review = ContentDraftReview(
        draft_id=draft.id,
        status="needs_revision",
        overall_score=72,
        tone_score=70,
        medical_safety_score=85,
        cta_safety_score=68,
        discipline_score=66,
    )
    db_session.add(review)
    db_session.commit()
    db_session.refresh(review)

    assert review.id is not None
    assert review.draft_id == draft.id


def test_status_allows_pass_needs_revision_blocked(db_session):
    draft = _create_draft(db_session)
    statuses = ["pass", "needs_revision", "blocked"]
    for idx, status in enumerate(statuses):
        review = ContentDraftReview(
            draft_id=draft.id,
            status=status,
            overall_score=80 + idx,
            tone_score=80,
            medical_safety_score=80,
            cta_safety_score=80,
            discipline_score=80,
        )
        db_session.add(review)
    db_session.commit()

    rows = db_session.query(ContentDraftReview).filter(ContentDraftReview.draft_id == draft.id).all()
    assert {row.status for row in rows} == {"pass", "needs_revision", "blocked"}


def test_scores_are_stored_correctly(db_session):
    draft = _create_draft(db_session)
    review = ContentDraftReview(
        draft_id=draft.id,
        status="pass",
        overall_score=91,
        tone_score=89,
        medical_safety_score=93,
        cta_safety_score=88,
        discipline_score=90,
    )
    db_session.add(review)
    db_session.commit()
    db_session.refresh(review)

    assert review.overall_score == 91
    assert review.tone_score == 89
    assert review.medical_safety_score == 93
    assert review.cta_safety_score == 88
    assert review.discipline_score == 90


def test_review_does_not_change_content_draft_status_automatically(db_session):
    draft = _create_draft(db_session)
    original_status = draft.status
    review = ContentDraftReview(
        draft_id=draft.id,
        status="blocked",
        overall_score=30,
        tone_score=40,
        medical_safety_score=20,
        cta_safety_score=35,
        discipline_score=50,
    )
    db_session.add(review)
    db_session.commit()
    db_session.refresh(draft)

    assert draft.status == original_status


def test_review_does_not_imply_publishing_behavior(db_session):
    draft = _create_draft(db_session)
    review = ContentDraftReview(
        draft_id=draft.id,
        status="pass",
        overall_score=88,
        tone_score=88,
        medical_safety_score=88,
        cta_safety_score=88,
        discipline_score=88,
    )
    db_session.add(review)
    db_session.commit()

    assert not hasattr(review, "published_at")
    assert not hasattr(review, "platform")
