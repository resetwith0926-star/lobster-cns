from __future__ import annotations

import json

import pytest
from sqlalchemy.exc import OperationalError

from app.services.event_log import EventLog
from app.schemas.ceo_decision import CEODecision
from app.services import task_queue as task_queue_module
from app.services.task_queue import TaskQueue


def test_create_task(db_session):
    queue = TaskQueue(db_session)

    task = queue.create_task("ResetWith 下週內容方向", "Plan content.")

    assert task.id is not None
    assert task.status == "pending"


def test_list_tasks(db_session):
    queue = TaskQueue(db_session)
    queue.create_task("Task A")
    queue.create_task("Task B")

    tasks = queue.list_tasks()

    assert len(tasks) == 2


def test_archive_task_sets_archive_fields(db_session):
    queue = TaskQueue(db_session)
    task = queue.create_task("Archive task")

    archived = queue.archive_task(task.id)

    assert archived.is_archived is True
    assert archived.archived_at is not None


def test_list_tasks_hides_archived_by_default(db_session):
    queue = TaskQueue(db_session)
    visible = queue.create_task("Visible task")
    archived = queue.create_task("Archived task")
    queue.archive_task(archived.id)

    tasks = queue.list_tasks()

    assert any(task.id == visible.id for task in tasks)
    assert all(task.id != archived.id for task in tasks)


def test_list_tasks_can_include_archived(db_session):
    queue = TaskQueue(db_session)
    archived = queue.create_task("Archived task include")
    queue.archive_task(archived.id)

    tasks = queue.list_tasks_with_archive(include_archived=True)

    assert any(task.id == archived.id for task in tasks)


def test_create_task_logs_task_created_event(db_session):
    queue = TaskQueue(db_session)
    events = EventLog(db_session)

    task = queue.create_task("Task with event")
    task_events = events.list_for_task(task.id)

    assert any(event.event_type == "task_created" for event in task_events)


def _valid_v13_decision():
    return CEODecision.model_validate(
        {
            "contract_version": "ceo_decision.v1.3",
            "task_type": "content",
            "priority": "medium",
            "risk_level": "low",
            "suggested_agent_role": "content_agent",
            "primary_agent_role": "content_agent",
            "supporting_agent_roles": ["sales_agent"],
            "task_summary": "Plan content.",
            "ceo_decision": "Create plan and wait approval.",
            "reasoning_summary": "Planning only.",
            "recommended_steps": ["Draft", "Review", "Approve"],
            "requires_human_approval": True,
            "approval_checklist": {
                "requires_human_review": True,
                "external_action_blocked": True,
                "medical_claims_checked": True,
                "sales_pressure_checked": True,
                "brand_tone_checked": True,
                "platform_risk_checked": True,
            },
            "decision_rubric": {
                "objective_clarity": "high",
                "audience_clarity": "medium",
                "business_value": "high",
                "trust_building": "medium",
                "objection_handling": "medium",
                "risk_control": "high",
                "execution_readiness": "medium",
            },
            "recommended_next_status": "waiting_approval",
            "blocked_by": [],
            "success_criteria": ["Clear plan"],
            "estimated_complexity": "simple",
            "simulation_only": True,
            "memory_to_save": [],
        }
    )


def test_save_ceo_decision_writes_primary_and_supporting_roles(db_session):
    queue = TaskQueue(db_session)
    task = queue.create_task("Task with v1.3 decision")
    decision = _valid_v13_decision()

    saved = queue.save_ceo_decision(task, decision, raw_output="raw")

    assert saved.primary_agent_role == "content_agent"
    assert json.loads(saved.supporting_agent_roles_json or "[]") == ["sales_agent"]


def test_save_ceo_decision_legacy_defaults_primary_and_supporting_roles(db_session):
    queue = TaskQueue(db_session)
    task = queue.create_task("Task with legacy decision")
    legacy_decision = CEODecision.model_validate(
        {
            "contract_version": "ceo_decision.v1.2",
            "task_type": "sales",
            "priority": "high",
            "risk_level": "medium",
            "suggested_agent_role": "sales_agent",
            "task_summary": "Legacy decision payload.",
            "ceo_decision": "Plan follow-up and request approval.",
            "reasoning_summary": "Need soft CTA flow.",
            "recommended_steps": ["Map intent", "Draft response"],
            "requires_human_approval": True,
            "recommended_next_status": "waiting_approval",
            "blocked_by": [],
            "success_criteria": ["Ready plan"],
            "estimated_complexity": "medium",
            "simulation_only": True,
            "memory_to_save": [],
        }
    )

    saved = queue.save_ceo_decision(task, legacy_decision, raw_output="legacy-raw")

    assert saved.primary_agent_role == "sales_agent"
    assert json.loads(saved.supporting_agent_roles_json or "[]") == []


def test_get_task_applies_migration_guard_when_column_missing(db_session, monkeypatch):
    queue = TaskQueue(db_session)
    task = queue.create_task("Column guard task")
    call_count = {"n": 0}

    original_get = db_session.get

    def flaky_get(model, task_id):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise OperationalError(
                "SELECT ...",
                {"id": task_id},
                Exception("no such column: tasks.primary_agent_role"),
            )
        return original_get(model, task_id)

    migration_called = {"ok": False}

    def fake_guard():
        migration_called["ok"] = True

    monkeypatch.setattr(db_session, "get", flaky_get)
    monkeypatch.setattr(task_queue_module, "_apply_sqlite_startup_migration_guard", fake_guard)

    found = queue.get_task(task.id)

    assert found is not None
    assert found.id == task.id
    assert migration_called["ok"] is True
    assert call_count["n"] == 2
