from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.ceo_decision import CEODecision


def valid_decision_payload():
    return {
        "contract_version": "ceo_decision.v1.3",
        "task_type": "content",
        "priority": "high",
        "risk_level": "low",
        "suggested_agent_role": "content_agent",
        "primary_agent_role": "content_agent",
        "supporting_agent_roles": ["sales_agent"],
        "task_summary": "Plan next week's ResetWith content.",
        "ceo_decision": "Prepare a weekly content direction before execution.",
        "reasoning_summary": "The task is content strategy and should remain planning-only.",
        "recommended_steps": ["Review brand memory", "Draft themes", "Ask owner to approve"],
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
            "audience_clarity": "high",
            "business_value": "high",
            "trust_building": "medium",
            "objection_handling": "medium",
            "risk_control": "high",
            "execution_readiness": "medium",
        },
        "recommended_next_status": "waiting_approval",
        "blocked_by": [],
        "success_criteria": ["Decision is structured", "Owner can approve next step"],
        "estimated_complexity": "medium",
        "simulation_only": True,
        "memory_to_save": [
            {
                "namespace": "content",
                "category": "strategy",
                "content": "ResetWith content planning requires owner approval before publishing.",
                "importance": 3,
            }
        ],
    }


def test_valid_ceo_decision_contract():
    decision = CEODecision.model_validate(valid_decision_payload())

    assert decision.contract_version == "ceo_decision.v1.3"
    assert decision.requires_human_approval is True
    assert decision.simulation_only is True
    assert decision.primary_agent_role == "content_agent"
    assert decision.supporting_agent_roles == ["sales_agent"]


def test_rejects_wrong_contract_version():
    payload = valid_decision_payload()
    payload["contract_version"] = "wrong"

    with pytest.raises(ValidationError):
        CEODecision.model_validate(payload)


def test_rejects_non_simulation_decision():
    payload = valid_decision_payload()
    payload["simulation_only"] = False

    with pytest.raises(ValidationError):
        CEODecision.model_validate(payload)


def test_rejects_decision_without_human_approval():
    payload = valid_decision_payload()
    payload["requires_human_approval"] = False

    with pytest.raises(ValidationError):
        CEODecision.model_validate(payload)


def test_v12_style_payload_is_compatible():
    payload = {
        "contract_version": "ceo_decision.v1.2",
        "task_type": "sales",
        "priority": "medium",
        "risk_level": "medium",
        "suggested_agent_role": "sales_agent",
        "task_summary": "Review sales response flow.",
        "ceo_decision": "Keep this as planning with owner approval.",
        "reasoning_summary": "Needs trust-first, low-pressure structure.",
        "recommended_steps": ["Map objections", "Draft CTA", "Request owner approval"],
        "requires_human_approval": True,
        "recommended_next_status": "waiting_approval",
        "blocked_by": [],
        "success_criteria": ["Clear response map", "Approval before execution"],
        "estimated_complexity": "medium",
        "simulation_only": True,
        "memory_to_save": [],
    }

    decision = CEODecision.model_validate(payload)

    assert decision.contract_version == "ceo_decision.v1.3"
    assert decision.primary_agent_role == "sales_agent"
    assert decision.supporting_agent_roles == []


def test_missing_primary_agent_role_defaults_to_suggested():
    payload = valid_decision_payload()
    payload.pop("primary_agent_role")

    decision = CEODecision.model_validate(payload)

    assert decision.primary_agent_role == decision.suggested_agent_role


def test_missing_supporting_agent_roles_defaults_to_empty_list():
    payload = valid_decision_payload()
    payload.pop("supporting_agent_roles")

    decision = CEODecision.model_validate(payload)

    assert decision.supporting_agent_roles == []


def test_rejects_false_requires_human_review_in_checklist():
    payload = valid_decision_payload()
    payload["approval_checklist"]["requires_human_review"] = False

    with pytest.raises(ValidationError):
        CEODecision.model_validate(payload)


def test_rejects_false_external_action_blocked_in_checklist():
    payload = valid_decision_payload()
    payload["approval_checklist"]["external_action_blocked"] = False

    with pytest.raises(ValidationError):
        CEODecision.model_validate(payload)


def test_rejects_invalid_decision_rubric_value():
    payload = valid_decision_payload()
    payload["decision_rubric"]["objective_clarity"] = "very_high"

    with pytest.raises(ValidationError):
        CEODecision.model_validate(payload)
