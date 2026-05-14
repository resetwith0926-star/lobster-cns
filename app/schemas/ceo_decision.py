from __future__ import annotations

from typing import Any, Dict, List, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


TaskType = Literal[
    "strategy",
    "content",
    "sales",
    "health",
    "operations",
    "development",
    "research",
    "admin",
    "unknown",
]
Priority = Literal["low", "medium", "high", "urgent"]
RiskLevel = Literal["low", "medium", "high"]
SuggestedAgentRole = Literal[
    "ceo_agent",
    "content_agent",
    "sales_agent",
    "dev_agent",
    "facebook_page_agent",
    "facebook_personal_agent",
    "instagram_agent",
    "x_agent",
    "line_agent",
    "telegram_agent",
    "unknown",
]
RecommendedNextStatus = Literal["planned", "waiting_approval", "failed"]
EstimatedComplexity = Literal["simple", "medium", "complex"]
MemoryNamespace = Literal["business", "brand", "sales", "content", "system", "user"]
MemoryCategory = Literal["rule", "preference", "decision", "strategy", "warning", "note"]
RubricScale = Literal["low", "medium", "high"]


class DecisionRubric(BaseModel):
    objective_clarity: RubricScale
    audience_clarity: RubricScale
    business_value: RubricScale
    trust_building: RubricScale
    objection_handling: RubricScale
    risk_control: RubricScale
    execution_readiness: RubricScale


class ApprovalChecklist(BaseModel):
    requires_human_review: bool
    external_action_blocked: bool
    medical_claims_checked: bool
    sales_pressure_checked: bool
    brand_tone_checked: bool
    platform_risk_checked: bool

    @field_validator("requires_human_review")
    @classmethod
    def human_review_must_be_true(cls, value: bool) -> bool:
        if value is not True:
            raise ValueError("approval_checklist.requires_human_review must be true.")
        return value

    @field_validator("external_action_blocked")
    @classmethod
    def external_action_must_be_blocked(cls, value: bool) -> bool:
        if value is not True:
            raise ValueError("approval_checklist.external_action_blocked must be true.")
        return value


class MemoryToSave(BaseModel):
    namespace: MemoryNamespace
    category: MemoryCategory
    content: str = Field(min_length=1)
    importance: int = Field(ge=1, le=5)


class CEODecision(BaseModel):
    contract_version: Literal["ceo_decision.v1", "ceo_decision.v1.2", "ceo_decision.v1.3"]
    task_type: TaskType
    priority: Priority
    risk_level: RiskLevel
    suggested_agent_role: SuggestedAgentRole
    primary_agent_role: SuggestedAgentRole
    supporting_agent_roles: List[SuggestedAgentRole] = Field(default_factory=list)
    task_summary: str
    ceo_decision: str
    reasoning_summary: str
    recommended_steps: List[str] = Field(default_factory=list)
    requires_human_approval: bool
    approval_checklist: ApprovalChecklist
    decision_rubric: DecisionRubric
    recommended_next_status: RecommendedNextStatus
    blocked_by: List[str] = Field(default_factory=list)
    success_criteria: List[str] = Field(default_factory=list)
    estimated_complexity: EstimatedComplexity
    simulation_only: bool
    memory_to_save: List[MemoryToSave] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def upgrade_legacy_payload(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        payload: Dict[str, Any] = dict(data)
        existing_version = payload.get("contract_version")
        if existing_version in (None, "ceo_decision.v1", "ceo_decision.v1.2", "ceo_decision.v1.3"):
            payload["contract_version"] = "ceo_decision.v1.3"

        suggested_role = payload.get("suggested_agent_role", "unknown")
        payload.setdefault("primary_agent_role", suggested_role)
        payload.setdefault("supporting_agent_roles", [])

        payload.setdefault(
            "decision_rubric",
            {
                "objective_clarity": "medium",
                "audience_clarity": "medium",
                "business_value": "medium",
                "trust_building": "medium",
                "objection_handling": "medium",
                "risk_control": "high",
                "execution_readiness": "medium",
            },
        )
        payload.setdefault(
            "approval_checklist",
            {
                "requires_human_review": True,
                "external_action_blocked": True,
                "medical_claims_checked": True,
                "sales_pressure_checked": True,
                "brand_tone_checked": True,
                "platform_risk_checked": True,
            },
        )
        return payload

    @field_validator("requires_human_approval")
    @classmethod
    def human_approval_is_required(cls, value: bool) -> bool:
        if value is not True:
            raise ValueError("requires_human_approval must be true in v0.1.2.")
        return value

    @field_validator("simulation_only")
    @classmethod
    def simulation_only_is_required(cls, value: bool) -> bool:
        if value is not True:
            raise ValueError("simulation_only must be true in v0.1.2.")
        return value
