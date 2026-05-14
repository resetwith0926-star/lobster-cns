from __future__ import annotations

import json

import pytest

from app.models.task import Task
from app.models.memory import Memory
from app.schemas.ceo_decision import CEODecision
from app.services.ceo_agent import CEOAgent
from app.services.event_log import EventLog
from app.services.llm_provider import LLMResponse
from app.services.task_queue import TaskQueue


VALID_DECISION = {
    "contract_version": "ceo_decision.v1.3",
    "task_type": "content",
    "priority": "high",
    "risk_level": "low",
    "suggested_agent_role": "content_agent",
    "primary_agent_role": "content_agent",
    "supporting_agent_roles": ["sales_agent"],
    "task_summary": "Plan next week's ResetWith content.",
    "ceo_decision": "Create a planning brief and wait for owner approval.",
    "reasoning_summary": "This is content strategy and no external action should be taken.",
    "recommended_steps": ["Review memory", "Draft themes", "Ask owner to approve"],
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
    "success_criteria": ["Task is classified", "Next steps are clear"],
    "estimated_complexity": "medium",
    "simulation_only": True,
    "memory_to_save": [
        {
            "namespace": "content",
            "category": "strategy",
            "content": "Content plans must wait for owner approval before publishing.",
            "importance": 3,
        }
    ],
}


class MockProvider:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def chat(self, messages, temperature=0.2, task_id=None, json_mode=True):
        self.calls.append({"messages": messages, "json_mode": json_mode})
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def llm_response(parsed_json, raw_text="{}"):
    return LLMResponse(
        provider="mock",
        model="mock-model",
        raw_text=raw_text,
        parsed_json=parsed_json,
        latency_ms=1,
        success=True,
    )


def test_review_task_with_mocked_deepseek_response(db_session):
    task = TaskQueue(db_session).create_task("ResetWith 下週內容方向", "Plan content.")
    provider = MockProvider([llm_response(VALID_DECISION, raw_text="valid")])

    decision = CEOAgent(db_session, provider).review_task(task.id)
    refreshed = db_session.get(Task, task.id)

    assert isinstance(decision, CEODecision)
    assert refreshed.status == "waiting_approval"
    assert refreshed.task_type == "content"
    assert refreshed.suggested_agent_role == "content_agent"
    assert refreshed.reasoning_summary is not None
    assert refreshed.ceo_decision_json is not None
    assert refreshed.primary_agent_role == "content_agent"
    assert json.loads(refreshed.supporting_agent_roles_json or "[]") == ["sales_agent"]
    assert provider.calls[0]["json_mode"] is True


def test_review_task_logs_review_events(db_session):
    task = TaskQueue(db_session).create_task("Review event task")
    provider = MockProvider([llm_response(VALID_DECISION, raw_text="valid")])

    CEOAgent(db_session, provider).review_task(task.id)
    events = EventLog(db_session).list_for_task(task.id)
    event_types = [event.event_type for event in events]

    assert "task_review_started" in event_types
    assert "ceo_decision_created" in event_types
    assert "task_review_completed" in event_types


def test_repair_invalid_json_once(db_session):
    task = TaskQueue(db_session).create_task("Repair task")
    provider = MockProvider(
        [
            llm_response(None, raw_text="not json"),
            llm_response(VALID_DECISION, raw_text="repaired"),
        ]
    )

    decision = CEOAgent(db_session, provider).review_task(task.id)

    assert decision.contract_version == "ceo_decision.v1.3"
    assert len(provider.calls) == 2


def test_mark_task_failed_when_repair_fails(db_session):
    task = TaskQueue(db_session).create_task("Fail task")
    provider = MockProvider(
        [
            llm_response(None, raw_text="bad"),
            llm_response(None, raw_text="still bad"),
        ]
    )

    with pytest.raises(ValueError):
        CEOAgent(db_session, provider).review_task(task.id)

    refreshed = db_session.get(Task, task.id)
    assert refreshed.status == "failed"
    assert refreshed.error is not None


def test_ceo_agent_cannot_mark_task_completed(db_session):
    task = TaskQueue(db_session).create_task("No completion task")
    provider = MockProvider([llm_response(VALID_DECISION, raw_text="valid")])

    CEOAgent(db_session, provider).review_task(task.id)
    refreshed = db_session.get(Task, task.id)

    assert refreshed.status != "completed"
    assert not hasattr(CEOAgent, "complete_task")


def test_review_task_defaults_primary_from_suggested_when_missing(db_session):
    task = TaskQueue(db_session).create_task("Primary fallback task")
    partial = dict(VALID_DECISION)
    partial.pop("primary_agent_role")
    provider = MockProvider([llm_response(partial, raw_text="valid")])

    decision = CEOAgent(db_session, provider).review_task(task.id)
    refreshed = db_session.get(Task, task.id)

    assert decision.primary_agent_role == "content_agent"
    assert refreshed.primary_agent_role == "content_agent"
    assert refreshed.suggested_agent_role == "content_agent"


def test_review_task_defaults_supporting_roles_when_missing(db_session):
    task = TaskQueue(db_session).create_task("Supporting fallback task")
    partial = dict(VALID_DECISION)
    partial.pop("supporting_agent_roles")
    provider = MockProvider([llm_response(partial, raw_text="valid")])

    decision = CEOAgent(db_session, provider).review_task(task.id)
    refreshed = db_session.get(Task, task.id)

    assert decision.supporting_agent_roles == []
    assert json.loads(refreshed.supporting_agent_roles_json or "[]") == []


def test_review_task_enforces_safety_flags_when_provider_returns_false(db_session):
    task = TaskQueue(db_session).create_task("Safety enforcement task")
    unsafe = dict(VALID_DECISION)
    unsafe["simulation_only"] = False
    unsafe["requires_human_approval"] = False
    unsafe["approval_checklist"] = dict(unsafe["approval_checklist"])
    unsafe["approval_checklist"]["requires_human_review"] = False
    unsafe["approval_checklist"]["external_action_blocked"] = False
    provider = MockProvider([llm_response(unsafe, raw_text="unsafe")])

    decision = CEOAgent(db_session, provider).review_task(task.id)
    refreshed = db_session.get(Task, task.id)

    assert decision.simulation_only is True
    assert decision.requires_human_approval is True
    assert decision.approval_checklist.requires_human_review is True
    assert decision.approval_checklist.external_action_blocked is True
    saved = json.loads(refreshed.ceo_decision_json or "{}")
    assert saved["simulation_only"] is True
    assert saved["requires_human_approval"] is True
    assert saved["approval_checklist"]["requires_human_review"] is True
    assert saved["approval_checklist"]["external_action_blocked"] is True


def test_repair_handles_partial_v13_output(db_session):
    task = TaskQueue(db_session).create_task("Partial repair task")
    initial = llm_response(None, raw_text="not-valid-json")
    repaired = {
        "contract_version": "ceo_decision.v1.3",
        "task_type": "sales",
        "priority": "high",
        "risk_level": "medium",
        "suggested_agent_role": "sales_agent",
        "task_summary": "Prioritize sales flow experiment.",
        "ceo_decision": "Plan and wait for owner approval.",
        "reasoning_summary": "Need controlled test.",
        "recommended_steps": ["Define audience", "Prepare draft", "Request approval"],
        "recommended_next_status": "waiting_approval",
        "blocked_by": [],
        "success_criteria": ["Flow drafted"],
        "estimated_complexity": "medium",
        "memory_to_save": [],
    }
    provider = MockProvider([initial, llm_response(repaired, raw_text="repaired")])

    decision = CEOAgent(db_session, provider).review_task(task.id)
    refreshed = db_session.get(Task, task.id)

    assert decision.primary_agent_role == "sales_agent"
    assert decision.supporting_agent_roles == []
    assert decision.requires_human_approval is True
    assert decision.simulation_only is True
    assert decision.approval_checklist.requires_human_review is True
    assert decision.approval_checklist.external_action_blocked is True
    assert refreshed.suggested_agent_role == "sales_agent"


def test_review_task_normalizes_invalid_memory_namespace_to_system(db_session):
    task = TaskQueue(db_session).create_task("Namespace normalize task")
    payload = dict(VALID_DECISION)
    payload["memory_to_save"] = [
        {
            "namespace": "development",
            "category": "strategy",
            "content": "Create implementation tasks for codex.",
            "importance": 2,
        }
    ]
    provider = MockProvider([llm_response(payload, raw_text="valid")])

    decision = CEOAgent(db_session, provider).review_task(task.id)
    refreshed = db_session.get(Task, task.id)
    saved = json.loads(refreshed.ceo_decision_json or "{}")

    assert decision.memory_to_save[0].namespace == "system"
    assert decision.memory_to_save[0].content.startswith("[normalized from namespace=development]")
    assert saved["memory_to_save"][0]["namespace"] == "system"


def test_review_task_keeps_valid_memory_namespaces_unchanged(db_session):
    task = TaskQueue(db_session).create_task("Namespace keep task")
    payload = dict(VALID_DECISION)
    payload["memory_to_save"] = [
        {
            "namespace": "content",
            "category": "strategy",
            "content": "Keep content planning practical.",
            "importance": 3,
        }
    ]
    provider = MockProvider([llm_response(payload, raw_text="valid")])

    decision = CEOAgent(db_session, provider).review_task(task.id)

    assert decision.memory_to_save[0].namespace == "content"
    assert decision.memory_to_save[0].content == "Keep content planning practical."


def test_invalid_memory_namespace_does_not_fail_review(db_session):
    task = TaskQueue(db_session).create_task("Invalid namespace no fail task")
    payload = dict(VALID_DECISION)
    payload["memory_to_save"] = [
        {
            "namespace": "development",
            "category": "note",
            "content": "Dev coordination note.",
            "importance": 1,
        }
    ]
    provider = MockProvider([llm_response(payload, raw_text="valid")])

    decision = CEOAgent(db_session, provider).review_task(task.id)
    refreshed = db_session.get(Task, task.id)

    assert decision.contract_version == "ceo_decision.v1.3"
    assert refreshed.status == "waiting_approval"


def test_saved_memory_uses_system_namespace_after_normalization(db_session):
    task = TaskQueue(db_session).create_task("Saved memory namespace task")
    payload = dict(VALID_DECISION)
    payload["memory_to_save"] = [
        {
            "namespace": "development",
            "category": "strategy",
            "content": "Align dev tasks with CEO plan.",
            "importance": 2,
        }
    ]
    provider = MockProvider([llm_response(payload, raw_text="valid")])

    CEOAgent(db_session, provider).review_task(task.id)
    saved_memory = (
        db_session.query(Memory)
        .filter(Memory.task_id == task.id)
        .order_by(Memory.id.desc())
        .first()
    )
    assert saved_memory is not None
    assert saved_memory.namespace == "system"
