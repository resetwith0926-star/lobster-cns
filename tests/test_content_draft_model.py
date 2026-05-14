from __future__ import annotations

from app.models import ContentDraft
from app.services.task_queue import TaskQueue


def test_can_create_content_draft_linked_to_task(db_session):
    task = TaskQueue(db_session).create_task("Draft source task")
    draft = ContentDraft(task_id=task.id, title="ResetWith 貼文草稿")
    db_session.add(draft)
    db_session.commit()
    db_session.refresh(draft)

    assert draft.id is not None
    assert draft.task_id == task.id


def test_content_draft_defaults_status_to_draft(db_session):
    task = TaskQueue(db_session).create_task("Status default task")
    draft = ContentDraft(task_id=task.id, title="Default status")
    db_session.add(draft)
    db_session.commit()
    db_session.refresh(draft)

    assert draft.status == "draft"


def test_content_draft_defaults_version_to_one(db_session):
    task = TaskQueue(db_session).create_task("Version default task")
    draft = ContentDraft(task_id=task.id, title="Default version")
    db_session.add(draft)
    db_session.commit()
    db_session.refresh(draft)

    assert draft.version == 1


def test_approved_status_does_not_imply_external_publishing_behavior(db_session):
    task = TaskQueue(db_session).create_task("Approved semantics task")
    draft = ContentDraft(task_id=task.id, title="Approved draft", status="approved")
    db_session.add(draft)
    db_session.commit()
    db_session.refresh(draft)

    assert draft.status == "approved"
    assert not hasattr(draft, "published_at")
    assert not hasattr(draft, "platform")
