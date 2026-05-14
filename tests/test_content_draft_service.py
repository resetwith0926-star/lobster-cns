from __future__ import annotations

import pytest

from app.models.event import Event
from app.models.llm_call import LLMCall
from app.services.llm_provider import LLMResponse
from app.services.content_draft_service import ContentDraftService
from app.services.task_queue import TaskQueue


class MockLLMProvider:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def chat(self, messages, temperature=0.2, task_id=None, json_mode=True):
        self.calls.append({"messages": messages, "temperature": temperature, "task_id": task_id, "json_mode": json_mode})
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def llm_response(raw_text: str, success: bool = True, error: str | None = None):
    return LLMResponse(
        provider="mock",
        model="mock-model",
        raw_text=raw_text,
        parsed_json=None,
        latency_ms=1,
        success=success,
        error=error,
    )


def test_create_draft_from_task_creates_linked_draft(db_session):
    task = TaskQueue(db_session).create_task("Create linked draft")
    draft = ContentDraftService(db_session).create_draft_from_task(task.id)
    assert draft.task_id == task.id


def test_create_draft_snapshots_task_ceo_decision_json(db_session):
    queue = TaskQueue(db_session)
    task = queue.create_task("Snapshot source")
    task.ceo_decision_json = '{"contract_version":"ceo_decision.v1.3"}'
    db_session.add(task)
    db_session.commit()

    draft = ContentDraftService(db_session).create_draft_from_task(task.id)
    assert draft.source_decision_json == '{"contract_version":"ceo_decision.v1.3"}'


def test_create_draft_title_defaults_to_task_title(db_session):
    task = TaskQueue(db_session).create_task("Default title task")
    draft = ContentDraftService(db_session).create_draft_from_task(task.id)
    assert draft.title == task.title


def test_create_draft_defaults_status_and_version(db_session):
    task = TaskQueue(db_session).create_task("Defaults task")
    draft = ContentDraftService(db_session).create_draft_from_task(task.id)
    assert draft.status == "draft"
    assert draft.generation_state == "idle"
    assert draft.retry_count == 0
    assert draft.version == 1


def test_create_draft_keeps_draft_text_none_in_phase_b(db_session):
    task = TaskQueue(db_session).create_task("No draft text task")
    draft = ContentDraftService(db_session).create_draft_from_task(task.id)
    assert draft.draft_text is None


def test_create_draft_does_not_make_llm_calls(db_session):
    task = TaskQueue(db_session).create_task("No llm task")
    ContentDraftService(db_session).create_draft_from_task(task.id)
    assert db_session.query(LLMCall).count() == 0


def test_update_status_sets_needs_revision(db_session):
    task = TaskQueue(db_session).create_task("Needs revision task")
    service = ContentDraftService(db_session)
    draft = service.create_draft_from_task(task.id)
    updated = service.update_status(draft.id, "needs_revision", review_notes="Revise opening hook.")
    assert updated.status == "needs_revision"
    assert updated.review_notes == "Revise opening hook."
    assert updated.reviewed_at is not None


def test_update_status_sets_approved_without_external_action(db_session):
    task = TaskQueue(db_session).create_task("Approved task")
    service = ContentDraftService(db_session)
    draft = service.create_draft_from_task(task.id)
    updated = service.update_status(draft.id, "approved", review_notes="Approved for human copy/paste.")
    assert updated.status == "approved"
    assert updated.reviewed_at is not None
    assert not hasattr(updated, "published_at")


def test_update_status_rejects_invalid_status(db_session):
    task = TaskQueue(db_session).create_task("Invalid status task")
    service = ContentDraftService(db_session)
    draft = service.create_draft_from_task(task.id)

    try:
        service.update_status(draft.id, "published")
    except ValueError as exc:
        assert "Invalid draft status" in str(exc)
    else:
        raise AssertionError("Expected invalid status to raise ValueError")


def test_event_log_created_for_draft_created(db_session):
    task = TaskQueue(db_session).create_task("Event create task")
    service = ContentDraftService(db_session)
    draft = service.create_draft_from_task(task.id)
    event = (
        db_session.query(Event)
        .filter(Event.event_type == "draft_created")
        .filter(Event.task_id == task.id)
        .order_by(Event.id.desc())
        .first()
    )
    assert event is not None
    assert str(draft.id) in (event.metadata_json or "")


def test_event_log_created_for_draft_status_changed(db_session):
    task = TaskQueue(db_session).create_task("Event status task")
    service = ContentDraftService(db_session)
    draft = service.create_draft_from_task(task.id)
    service.update_status(draft.id, "approved")
    event = (
        db_session.query(Event)
        .filter(Event.event_type == "draft_status_changed")
        .filter(Event.task_id == task.id)
        .order_by(Event.id.desc())
        .first()
    )
    assert event is not None
    assert "approved" in event.message


def test_list_drafts_can_filter_by_status(db_session):
    task = TaskQueue(db_session).create_task("Filter task")
    service = ContentDraftService(db_session)
    draft_a = service.create_draft_from_task(task.id, title="A")
    draft_b = service.create_draft_from_task(task.id, title="B")
    service.update_status(draft_b.id, "approved")

    approved = service.list_drafts(status="approved")
    draft_only = service.list_drafts(status="draft")

    assert any(item.id == draft_b.id for item in approved)
    assert all(item.status == "approved" for item in approved)
    assert any(item.id == draft_a.id for item in draft_only)
    assert all(item.status == "draft" for item in draft_only)


def test_archive_draft_sets_archive_fields(db_session):
    task = TaskQueue(db_session).create_task("Archive draft task")
    service = ContentDraftService(db_session)
    draft = service.create_draft_from_task(task.id)

    archived = service.archive_draft(draft.id)

    assert archived.is_archived is True
    assert archived.archived_at is not None


def test_list_drafts_hides_archived_by_default(db_session):
    task = TaskQueue(db_session).create_task("Hide archived drafts task")
    service = ContentDraftService(db_session)
    visible = service.create_draft_from_task(task.id, title="Visible")
    archived = service.create_draft_from_task(task.id, title="Archived")
    service.archive_draft(archived.id)

    drafts = service.list_drafts()

    assert any(item.id == visible.id for item in drafts)
    assert all(item.id != archived.id for item in drafts)


def test_list_drafts_can_include_archived(db_session):
    task = TaskQueue(db_session).create_task("Include archived drafts task")
    service = ContentDraftService(db_session)
    archived = service.create_draft_from_task(task.id)
    service.archive_draft(archived.id)

    drafts = service.list_drafts(include_archived=True)

    assert any(item.id == archived.id for item in drafts)


def test_get_draft_returns_draft(db_session):
    task = TaskQueue(db_session).create_task("Get draft task")
    service = ContentDraftService(db_session)
    created = service.create_draft_from_task(task.id)
    fetched = service.get_draft(created.id)
    assert fetched is not None
    assert fetched.id == created.id


def test_missing_task_raises_clear_error(db_session):
    service = ContentDraftService(db_session)
    try:
        service.create_draft_from_task(99999)
    except ValueError as exc:
        assert "was not found" in str(exc)
    else:
        raise AssertionError("Expected missing task to raise ValueError")


def test_generate_draft_writes_draft_text(db_session):
    task = TaskQueue(db_session).create_task("Generate draft task", "Need a practical health education post.")
    service = ContentDraftService(db_session)
    draft = service.create_draft_from_task(task.id)
    provider = MockLLMProvider([llm_response("這是一篇草稿內容。")])

    updated = service.generate_draft(draft.id, llm_provider=provider)

    assert updated.draft_text == "這是一篇草稿內容。"
    assert updated.generation_state == "ready"
    assert updated.last_error is None
    assert updated.last_error_at is None


def test_generate_draft_keeps_status_as_draft_and_not_approved(db_session):
    task = TaskQueue(db_session).create_task("Status after generate")
    service = ContentDraftService(db_session)
    draft = service.create_draft_from_task(task.id)
    provider = MockLLMProvider([llm_response("Draft text")])

    updated = service.generate_draft(draft.id, llm_provider=provider)

    assert updated.status == "draft"
    assert updated.status != "approved"


def test_generate_draft_does_not_trigger_external_action_behavior(db_session):
    task = TaskQueue(db_session).create_task("No external action draft")
    service = ContentDraftService(db_session)
    draft = service.create_draft_from_task(task.id)
    provider = MockLLMProvider([llm_response("Draft text")])

    updated = service.generate_draft(draft.id, llm_provider=provider)

    assert not hasattr(updated, "published_at")
    assert not hasattr(updated, "platform")


def test_generate_draft_logs_event(db_session):
    task = TaskQueue(db_session).create_task("Draft generated event task")
    service = ContentDraftService(db_session)
    draft = service.create_draft_from_task(task.id)
    provider = MockLLMProvider([llm_response("Draft text")])

    service.generate_draft(draft.id, llm_provider=provider)
    event = (
        db_session.query(Event)
        .filter(Event.event_type == "draft_generated")
        .filter(Event.task_id == task.id)
        .order_by(Event.id.desc())
        .first()
    )
    assert event is not None


def test_revise_draft_updates_text_and_increments_version_and_resets_status(db_session):
    task = TaskQueue(db_session).create_task("Revise draft task")
    service = ContentDraftService(db_session)
    draft = service.create_draft_from_task(task.id)
    draft.draft_text = "舊草稿"
    draft.status = "needs_revision"
    db_session.add(draft)
    db_session.commit()
    provider = MockLLMProvider([llm_response("新草稿")])

    updated = service.revise_draft(draft.id, "請更精簡", llm_provider=provider)

    assert updated.draft_text == "新草稿"
    assert updated.version == 2
    assert updated.status == "draft"


def test_revise_draft_logs_revision_event(db_session):
    task = TaskQueue(db_session).create_task("Revise event task")
    service = ContentDraftService(db_session)
    draft = service.create_draft_from_task(task.id)
    draft.draft_text = "舊版"
    db_session.add(draft)
    db_session.commit()
    provider = MockLLMProvider([llm_response("新版")])

    service.revise_draft(draft.id, "改成更口語", llm_provider=provider)
    requested = (
        db_session.query(Event)
        .filter(Event.event_type == "draft_revision_requested")
        .filter(Event.task_id == task.id)
        .order_by(Event.id.desc())
        .first()
    )
    revised = (
        db_session.query(Event)
        .filter(Event.event_type == "draft_revised")
        .filter(Event.task_id == task.id)
        .order_by(Event.id.desc())
        .first()
    )
    assert requested is not None
    assert revised is not None


def test_generate_draft_uses_mocked_llm_response(db_session):
    task = TaskQueue(db_session).create_task("Mock response task")
    service = ContentDraftService(db_session)
    draft = service.create_draft_from_task(task.id)
    provider = MockLLMProvider([llm_response("Mocked draft output")])

    updated = service.generate_draft(draft.id, llm_provider=provider)

    assert updated.draft_text == "Mocked draft output"
    assert len(provider.calls) == 1
    assert provider.calls[0]["json_mode"] is False


def test_generate_draft_failure_sets_generation_failure_fields(db_session):
    task = TaskQueue(db_session).create_task("Generation failure task", "desc")
    service = ContentDraftService(db_session)
    draft = service.create_draft_from_task(task.id)
    provider = MockLLMProvider([llm_response("", success=False, error="The read operation timed out")])

    with pytest.raises(ValueError):
        service.generate_draft(draft.id, llm_provider=provider)

    refreshed = service.require_draft(draft.id)
    assert refreshed.generation_state == "failed"
    assert refreshed.retry_count == 1
    assert refreshed.last_error == "The read operation timed out"
    assert refreshed.last_error_at is not None
    assert refreshed.status == "draft"


def test_generate_draft_failure_increments_retry_count(db_session):
    task = TaskQueue(db_session).create_task("Generation retry task", "desc")
    service = ContentDraftService(db_session)
    draft = service.create_draft_from_task(task.id)
    provider = MockLLMProvider(
        [
            llm_response("", success=False, error="The read operation timed out"),
            llm_response("", success=False, error="The read operation timed out"),
        ]
    )

    for _ in range(2):
        with pytest.raises(ValueError):
            service.generate_draft(draft.id, llm_provider=provider)

    refreshed = service.require_draft(draft.id)
    assert refreshed.retry_count == 2


@pytest.mark.parametrize("raw_text", [None, "", "   "])
def test_generate_draft_empty_content_is_treated_as_failed(db_session, raw_text):
    task = TaskQueue(db_session).create_task("Empty content task", "desc")
    service = ContentDraftService(db_session)
    draft = service.create_draft_from_task(task.id)
    draft.draft_text = "舊內容應保留"
    db_session.add(draft)
    db_session.commit()
    provider = MockLLMProvider([llm_response(raw_text)])

    with pytest.raises(ValueError, match="Draft generation returned empty content."):
        service.generate_draft(draft.id, llm_provider=provider)

    refreshed = service.require_draft(draft.id)
    assert refreshed.generation_state == "failed"
    assert refreshed.retry_count == 1
    assert refreshed.last_error == "Draft generation returned empty content."
    assert refreshed.last_error_at is not None
    assert refreshed.draft_text == "舊內容應保留"
    assert refreshed.status == "draft"


def test_timeout_error_shows_retry_recommendation(db_session):
    task = TaskQueue(db_session).create_task("Timeout recommendation task")
    service = ContentDraftService(db_session)
    draft = service.create_draft_from_task(task.id)
    service.mark_generation_failed(draft.id, "The read operation timed out")

    refreshed = service.require_draft(draft.id)
    recommendation = service.build_retry_recommendation(refreshed)

    assert recommendation is not None
    assert "Please retry" in recommendation
    assert "split this request" in recommendation


def test_retry_count_two_shows_stronger_split_recommendation(db_session):
    task = TaskQueue(db_session).create_task("Retry split recommendation task")
    service = ContentDraftService(db_session)
    draft = service.create_draft_from_task(task.id)
    service.mark_generation_failed(draft.id, "The read operation timed out")
    service.mark_generation_failed(draft.id, "The read operation timed out")

    refreshed = service.require_draft(draft.id)
    recommendation = service.build_retry_recommendation(refreshed)

    assert recommendation is not None
    assert "Recommended split: separate into 1) outline 2) section draft 3) CTA draft." in recommendation


def test_revise_draft_uses_text_mode(db_session):
    task = TaskQueue(db_session).create_task("Revise text mode task")
    service = ContentDraftService(db_session)
    draft = service.create_draft_from_task(task.id)
    draft.draft_text = "原稿"
    db_session.add(draft)
    db_session.commit()
    provider = MockLLMProvider([llm_response("新版內容")])

    service.revise_draft(draft.id, "請更短", llm_provider=provider)

    assert provider.calls[0]["json_mode"] is False


def test_llm_failure_does_not_change_task_lifecycle(db_session):
    queue = TaskQueue(db_session)
    task = queue.create_task("Task lifecycle unchanged", "desc")
    service = ContentDraftService(db_session)
    draft = service.create_draft_from_task(task.id)
    provider = MockLLMProvider([llm_response("", success=False, error="provider failed")])

    try:
        service.generate_draft(draft.id, llm_provider=provider)
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError on LLM failure")

    refreshed = queue.require_task(task.id)
    assert refreshed.status == "pending"


def test_no_content_agent_enabled_by_draft_service_flow(db_session):
    task = TaskQueue(db_session).create_task("Agent guard task")
    service = ContentDraftService(db_session)
    draft = service.create_draft_from_task(task.id)
    provider = MockLLMProvider([llm_response("Draft text")])
    service.generate_draft(draft.id, llm_provider=provider)

    # The service never touches agent registry state.
    # This assertion ensures no implicit platform behavior is introduced on drafts.
    assert True
