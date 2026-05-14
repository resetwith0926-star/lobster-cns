from __future__ import annotations

from app.services.event_log import EventLog


def test_event_log_creates_and_lists_events(db_session):
    events = EventLog(db_session)

    created = events.log("task_created", actor="admin", message="Created")
    recent = events.list_recent()

    assert created.id is not None
    assert recent[0].event_type == "task_created"

