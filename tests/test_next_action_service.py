from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models.content_draft import ContentDraft
from app.models.task import Task
from app.services.next_action_service import NextActionService


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_next_action_service_returns_safe_defaults_when_empty(db_session, monkeypatch):
    service = NextActionService(db_session)
    monkeypatch.setattr(service, "_get_latest_git_tag", lambda: "v0.1.7.1")

    panel = service.build_dashboard_panel()

    assert panel["version_status"]["current_displayed_version"] == "v0.1.7.1"
    assert panel["task_summary"]["active_count"] == 0
    assert panel["draft_summary"]["failed_count"] == 0
    assert len(panel["next_actions"]) <= 3
    assert "Approved means human use/copying only, not published." in panel["prohibited_actions"]


def test_next_action_service_detects_failed_and_archived_records(db_session, monkeypatch):
    active_task = Task(title="Active task", description="desc", status="pending", is_archived=False)
    archived_task = Task(title="Archived task", description="desc", status="pending", is_archived=True)
    db_session.add_all([active_task, archived_task])
    db_session.commit()
    db_session.refresh(active_task)

    failed_draft = ContentDraft(
        task_id=active_task.id,
        title="Failed draft",
        generation_state="failed",
        retry_count=2,
        is_archived=False,
        status="draft",
        created_by="dashboard",
    )
    archived_draft = ContentDraft(
        task_id=active_task.id,
        title="Archived draft",
        generation_state="ready",
        retry_count=0,
        is_archived=True,
        status="draft",
        created_by="dashboard",
    )
    db_session.add_all([failed_draft, archived_draft])
    db_session.commit()

    service = NextActionService(db_session)
    monkeypatch.setattr(service, "_get_latest_git_tag", lambda: "v0.1.7.1")

    task_summary = service.get_task_summary()
    draft_summary = service.get_draft_summary()
    actions = service.get_next_actions()

    assert task_summary["archived_count"] == 1
    assert draft_summary["archived_count"] == 1
    assert draft_summary["failed_count"] == 1
    assert actions[0] == "Review failed draft: Failed draft"
    assert len(actions) <= 3


def test_next_action_service_excludes_archived_tasks_from_active_next_actions(db_session, monkeypatch):
    active_task = Task(
        title="Still active task",
        description="desc",
        status="pending",
        is_archived=False,
    )
    archived_task = Task(
        title="v0.1.18 Walkthrough Test Task",
        description="desc",
        status="pending",
        is_archived=True,
    )
    db_session.add_all([active_task, archived_task])
    db_session.commit()

    service = NextActionService(db_session)
    monkeypatch.setattr(service, "_get_latest_git_tag", lambda: "v0.1.14")

    task_summary = service.get_task_summary()
    actions = service.get_next_actions()

    assert task_summary["active_count"] == 1
    assert task_summary["archived_count"] == 1
    assert task_summary["first_active_title"] == "Still active task"
    assert "Continue active task: Still active task" in actions
    assert all("v0.1.18 Walkthrough Test Task" not in action for action in actions)


def test_next_action_service_treats_validation_failed_draft_as_non_blocker(db_session, monkeypatch):
    active_task = Task(title="Active task", description="desc", status="pending", is_archived=False)
    db_session.add(active_task)
    db_session.commit()
    db_session.refresh(active_task)

    failed_validation_draft = ContentDraft(
        task_id=active_task.id,
        title="Failed state validation draft",
        generation_state="failed",
        retry_count=2,
        last_error="The read operation timed out",
        is_archived=False,
        status="draft",
        created_by="dashboard",
    )
    db_session.add(failed_validation_draft)
    db_session.commit()

    service = NextActionService(db_session)
    monkeypatch.setattr(service, "_get_latest_git_tag", lambda: "v0.1.8")

    draft_summary = service.get_draft_summary()
    actions = service.get_next_actions()
    panel = service.build_dashboard_panel()
    handoff = service.build_handoff_summary()

    assert draft_summary["failed_count"] == 1
    assert draft_summary["real_failed_count"] == 0
    assert draft_summary["validation_failed_count"] == 1
    assert actions[0] == "Validation failed draft exists for UI testing; not a production blocker."
    assert panel["system_status"] == "validation_only"
    assert "Review failed draft: Failed state validation draft" not in handoff
    assert "Validation failed draft exists for UI testing; not a production blocker." in handoff


def test_next_action_service_git_tag_failure_returns_unknown(db_session, monkeypatch):
    service = NextActionService(db_session)
    monkeypatch.setattr(service, "_get_latest_git_tag", lambda: None)

    version_status = service.get_version_status()

    assert version_status["current_displayed_version"] == "unknown"
    assert version_status["latest_git_tag"] == "unknown"


def test_review_queue_validation_failed_draft_is_not_failed_production(db_session, monkeypatch):
    task = Task(title="Host task", description="desc", status="pending", is_archived=False)
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    draft = ContentDraft(
        task_id=task.id,
        title="Failed state validation draft",
        generation_state="failed",
        retry_count=2,
        last_error="The read operation timed out",
        is_archived=False,
        status="draft",
        created_by="dashboard",
    )
    db_session.add(draft)
    db_session.commit()

    service = NextActionService(db_session)
    monkeypatch.setattr(service, "_get_latest_git_tag", lambda: "v0.1.8.1")

    queue = service.get_review_queue_items()

    assert len(queue["validation_test_records"]) == 1
    assert len(queue["failed_production_drafts"]) == 0
    assert len(queue["needs_attention"]) == 0


def test_review_queue_real_failed_draft_enters_failed_and_attention(db_session, monkeypatch):
    task = Task(title="Host task", description="desc", status="pending", is_archived=False)
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    draft = ContentDraft(
        task_id=task.id,
        title="Production failed draft",
        generation_state="failed",
        retry_count=2,
        last_error="The read operation timed out",
        is_archived=False,
        status="draft",
        created_by="dashboard",
    )
    db_session.add(draft)
    db_session.commit()

    service = NextActionService(db_session)
    monkeypatch.setattr(service, "_get_latest_git_tag", lambda: "v0.1.8.1")

    queue = service.get_review_queue_items()

    assert len(queue["failed_production_drafts"]) == 1
    assert len(queue["needs_attention"]) == 1


def test_review_queue_ready_approved_and_archived_categories(db_session, monkeypatch):
    task = Task(title="Host task", description="desc", status="pending", is_archived=False)
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    ready = ContentDraft(
        task_id=task.id,
        title="Ready review draft",
        generation_state="ready",
        retry_count=0,
        is_archived=False,
        status="draft",
        created_by="dashboard",
    )
    approved = ContentDraft(
        task_id=task.id,
        title="Approved copy draft",
        generation_state="ready",
        retry_count=0,
        is_archived=False,
        status="approved",
        created_by="dashboard",
    )
    archived = ContentDraft(
        task_id=task.id,
        title="Archived draft",
        generation_state="ready",
        retry_count=0,
        is_archived=True,
        status="draft",
        created_by="dashboard",
    )
    db_session.add_all([ready, approved, archived])
    db_session.commit()

    service = NextActionService(db_session)
    monkeypatch.setattr(service, "_get_latest_git_tag", lambda: "v0.1.8.1")

    queue = service.get_review_queue_items()

    assert len(queue["ready_for_review"]) == 1
    assert queue["ready_for_review"][0]["title"] == "Ready review draft"
    assert len(queue["approved_for_human_copy"]) == 1
    assert queue["approved_for_human_copy"][0]["title"] == "Approved copy draft"
    assert len(queue["archived"]) == 1
    assert queue["archived"][0]["title"] == "Archived draft"


def test_get_recovery_hints_returns_expected_texts(db_session):
    service = NextActionService(db_session)

    assert "Review last_error" in service.get_recovery_hints("failed_production_drafts")
    assert "not a production blocker" in service.get_recovery_hints("validation_test_records")
    assert "Open the draft" in service.get_recovery_hints("ready_for_review")
    assert "human-use/copying only, not published" in service.get_recovery_hints("approved_for_human_copy")
    assert "No action needed" in service.get_recovery_hints("archived")


def test_get_recovery_hints_returns_safe_default_for_unknown_category(db_session):
    service = NextActionService(db_session)

    assert service.get_recovery_hints("unknown_category") == (
        "Review the current state and continue with manual operator judgment."
    )


def test_get_manual_next_step_returns_expected_hints(db_session):
    service = NextActionService(db_session)

    failed = ContentDraft(
        task_id=1,
        title="Production failed draft",
        generation_state="failed",
        retry_count=2,
        last_error="The read operation timed out",
        status="draft",
        created_by="dashboard",
    )
    validation = ContentDraft(
        task_id=1,
        title="Failed state validation draft",
        generation_state="failed",
        retry_count=2,
        last_error="The read operation timed out",
        status="draft",
        created_by="dashboard",
    )
    approved = ContentDraft(
        task_id=1,
        title="Approved copy draft",
        generation_state="ready",
        status="approved",
        created_by="dashboard",
    )

    assert "Retry manually with a shorter prompt" in service.get_manual_next_step(failed)
    assert "not a production blocker" in service.get_manual_next_step(validation)
    assert "human-use/copying only, not published" in service.get_manual_next_step(approved)


def test_build_codex_task_brief_contains_required_sections(db_session, monkeypatch):
    service = NextActionService(db_session)
    monkeypatch.setattr(service, "_get_latest_git_tag", lambda: "v0.1.10")
    monkeypatch.setattr(service, "get_next_actions", lambda: ["Review dashboard state manually."])
    monkeypatch.setattr(service, "build_handoff_summary", lambda: "Example handoff summary")

    brief = service.build_codex_task_brief()

    assert "Title: Lobster CNS Codex Task Brief" in brief
    assert "Current version / latest tag: v0.1.10 / v0.1.10" in brief
    assert "Goal:" in brief
    assert "Current context:" in brief
    assert "Review Queue summary:" in brief
    assert "Needs Attention" in brief
    assert "Failed Production Drafts" in brief
    assert "Validation / Test Records" in brief
    assert "Ready for Review" in brief
    assert "Approved for Human Copy" in brief
    assert "Archived" in brief
    assert "Explicitly out of scope:" in brief
    assert "Files likely affected: unknown / to be determined" in brief
    assert "Do not commit unless instructed." in brief
    assert "Do not tag unless instructed." in brief
    assert "Do not push." in brief
    assert "This brief is for human review and manual use only." in brief


def test_build_codex_task_brief_uses_safe_fallbacks(db_session, monkeypatch):
    service = NextActionService(db_session)
    monkeypatch.setattr(service, "_get_latest_git_tag", lambda: None)
    monkeypatch.setattr(service, "get_next_actions", lambda: [])
    monkeypatch.setattr(service, "build_handoff_summary", lambda: "")

    brief = service.build_codex_task_brief()

    assert "Current version / latest tag: unknown / unknown" in brief
    assert "No urgent next action. Review dashboard state manually." in brief
    assert "No handoff summary available. Use current dashboard state." in brief
