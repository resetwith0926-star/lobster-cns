# CEO Decision JSON Repair Prompt

Repair the provided output into the required CEO decision JSON contract.

Do not add new strategic content. Do not invent new recommendations beyond what is already present. Only repair structure, field names, missing required booleans, and enum-compatible values.

The repaired JSON must use `contract_version: ceo_decision.v1.3`, `simulation_only: true`, and `requires_human_approval: true`.

If the original output says approval is not needed, override it to `requires_human_approval: true` because v0.1.3 always requires human approval.

If required fields are missing, fill them with conservative values based on the original text:
- task_type: use one of strategy, content, sales, health, operations, development, research, admin, unknown
- priority: use low, medium, high, or urgent
- risk_level: use low, medium, or high
- suggested_agent_role: use ceo_agent, content_agent, sales_agent, dev_agent, facebook_page_agent, facebook_personal_agent, instagram_agent, x_agent, line_agent, telegram_agent, or unknown
- primary_agent_role: default to suggested_agent_role when missing
- supporting_agent_roles: use [] when missing
- decision_rubric values: objective_clarity, audience_clarity, business_value, trust_building, objection_handling, risk_control, execution_readiness each must be low|medium|high
- approval_checklist booleans: requires_human_review, external_action_blocked, medical_claims_checked, sales_pressure_checked, brand_tone_checked, platform_risk_checked
- recommended_next_status: use planned, waiting_approval, or failed
- estimated_complexity: use simple, medium, or complex
- blocked_by: use [] if none is clearly stated
- memory_to_save: use [] if no durable memory is clearly useful

Required JSON shape:

{
  "contract_version": "ceo_decision.v1.3",
  "task_type": "unknown",
  "priority": "low",
  "risk_level": "low",
  "suggested_agent_role": "ceo_agent",
  "primary_agent_role": "ceo_agent",
  "supporting_agent_roles": [],
  "task_summary": "short summary",
  "ceo_decision": "CEO-level decision",
  "reasoning_summary": "brief explanation, no hidden chain-of-thought",
  "recommended_steps": [
    "step 1"
  ],
  "requires_human_approval": true,
  "approval_checklist": {
    "requires_human_review": true,
    "external_action_blocked": true,
    "medical_claims_checked": true,
    "sales_pressure_checked": true,
    "brand_tone_checked": true,
    "platform_risk_checked": true
  },
  "decision_rubric": {
    "objective_clarity": "medium",
    "audience_clarity": "medium",
    "business_value": "medium",
    "trust_building": "medium",
    "objection_handling": "medium",
    "risk_control": "high",
    "execution_readiness": "medium"
  },
  "recommended_next_status": "planned",
  "blocked_by": [],
  "success_criteria": [
    "criterion 1"
  ],
  "estimated_complexity": "simple",
  "simulation_only": true,
  "memory_to_save": []
}

Return JSON only.
