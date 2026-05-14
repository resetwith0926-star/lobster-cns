from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.content_draft_review import ContentDraftReview
from app.services.content_draft_service import ContentDraftService
from app.services.deepseek_provider import DeepSeekLLMProvider
from app.services.event_log import EventLog
from app.services.llm_provider import LLMProvider, LLMResponse
from app.services.prompt_registry import load_prompt


_ALLOWED_STATUS = {"pass", "needs_revision", "blocked"}
_APPROVAL_TO_STATUS = {"approve": "pass", "revise": "needs_revision", "block": "blocked"}


class _RiskFlag(BaseModel):
    type: str
    severity: str
    text: str
    reason: str
    suggested_fix: str


class _SuggestedRewrite(BaseModel):
    original: str
    rewrite: str
    reason: str


class _ContentQualityReviewDecision(BaseModel):
    contract_version: str = Field(pattern=r"^content_review\.v1$")
    status: str
    overall_score: int
    tone_score: int
    medical_safety_score: int
    cta_safety_score: int
    discipline_score: int
    risk_flags: List[_RiskFlag] = Field(default_factory=list)
    suggested_rewrites: List[_SuggestedRewrite] = Field(default_factory=list)
    review_summary: str
    approval_recommendation: str


class ContentQualityReviewService:
    def __init__(self, db: Session):
        self.db = db
        self.drafts = ContentDraftService(db)
        self.events = EventLog(db)

    def review_draft(
        self,
        draft_id: int,
        llm_provider: Optional[LLMProvider] = None,
        actor: str = "quality_reviewer",
    ) -> ContentDraftReview:
        draft = self.drafts.require_draft(draft_id)
        if not (draft.draft_text or "").strip():
            raise ValueError("Draft text is required before quality review.")

        self.events.log(
            "content_quality_review_started",
            actor=actor,
            task_id=draft.task_id,
            message=f"Content quality review started for draft {draft.id}.",
            metadata={"draft_id": draft.id},
        )

        provider = llm_provider or DeepSeekLLMProvider(self.db)
        response = provider.chat(
            self._build_review_messages(draft.draft_text, draft.title, draft.channel_hint, draft.target_audience),
            temperature=0.1,
            task_id=draft.task_id,
            json_mode=True,
        )

        decision = self._decision_from_response(response)
        if decision is None:
            repair_response = provider.chat(
                self._build_repair_messages(response.raw_text),
                temperature=0.0,
                task_id=draft.task_id,
                json_mode=True,
            )
            decision = self._decision_from_response(repair_response)
            if decision is None:
                error_message = repair_response.error or "Content quality review JSON repair failed."
                self.events.log(
                    "error",
                    actor=actor,
                    task_id=draft.task_id,
                    message=error_message,
                    metadata={"draft_id": draft.id, "stage": "content_quality_review"},
                )
                raise ValueError(error_message)

        record = ContentDraftReview(
            draft_id=draft.id,
            status=decision["status"],
            overall_score=decision["overall_score"],
            tone_score=decision["tone_score"],
            medical_safety_score=decision["medical_safety_score"],
            cta_safety_score=decision["cta_safety_score"],
            discipline_score=decision["discipline_score"],
            risk_flags_json=json.dumps(decision["risk_flags"], ensure_ascii=False),
            suggested_rewrites_json=json.dumps(decision["suggested_rewrites"], ensure_ascii=False),
            review_summary=decision["review_summary"],
            raw_review_json=json.dumps(decision, ensure_ascii=False),
            reviewed_by=actor,
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)

        self.events.log(
            "content_quality_review_completed",
            actor=actor,
            task_id=draft.task_id,
            message=f"Content quality review completed for draft {draft.id}.",
            metadata={"draft_id": draft.id, "review_id": record.id, "status": record.status},
        )
        return record

    def get_latest_review(self, draft_id: int) -> Optional[ContentDraftReview]:
        stmt = (
            select(ContentDraftReview)
            .where(ContentDraftReview.draft_id == draft_id)
            .order_by(ContentDraftReview.created_at.desc(), ContentDraftReview.id.desc())
            .limit(1)
        )
        return self.db.scalars(stmt).first()

    def list_reviews(self, draft_id: int) -> list[ContentDraftReview]:
        stmt = (
            select(ContentDraftReview)
            .where(ContentDraftReview.draft_id == draft_id)
            .order_by(ContentDraftReview.created_at.desc(), ContentDraftReview.id.desc())
        )
        return list(self.db.scalars(stmt))

    def _build_review_messages(
        self,
        draft_text: str,
        title: str,
        channel_hint: Optional[str],
        target_audience: Optional[str],
    ) -> list[dict[str, str]]:
        system_prompt = load_prompt("content_quality_review_system.md")
        user_prompt = f"""Draft title:
{title}

Channel hint:
{channel_hint or "not specified"}

Target audience:
{target_audience or "not specified"}

Draft text:
{draft_text}
"""
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    def _build_repair_messages(self, raw_text: str) -> list[dict[str, str]]:
        repair_prompt = load_prompt("content_quality_review_repair.md")
        return [
            {"role": "system", "content": repair_prompt},
            {"role": "user", "content": raw_text or ""},
        ]

    def _decision_from_response(self, response: LLMResponse) -> Optional[Dict[str, Any]]:
        if not response.success or response.parsed_json is None:
            return None
        if not isinstance(response.parsed_json, dict):
            return None

        normalized = self._normalize_decision_payload(response.parsed_json)
        try:
            _ContentQualityReviewDecision.model_validate(normalized)
        except ValidationError:
            return None
        return normalized

    def _normalize_decision_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        normalized = dict(payload)
        normalized["contract_version"] = "content_review.v1"

        approval_recommendation = str(normalized.get("approval_recommendation") or "").strip().lower()
        mapped_status = _APPROVAL_TO_STATUS.get(approval_recommendation)

        raw_status = str(normalized.get("status") or "").strip().lower()
        if mapped_status:
            normalized["status"] = mapped_status
        elif raw_status in _ALLOWED_STATUS:
            normalized["status"] = raw_status
        else:
            normalized["status"] = "needs_revision"

        normalized["risk_flags"] = normalized.get("risk_flags") if isinstance(normalized.get("risk_flags"), list) else []
        normalized["suggested_rewrites"] = (
            normalized.get("suggested_rewrites") if isinstance(normalized.get("suggested_rewrites"), list) else []
        )

        for key in [
            "overall_score",
            "tone_score",
            "medical_safety_score",
            "cta_safety_score",
            "discipline_score",
        ]:
            normalized[key] = self._clamp_score(normalized.get(key))

        summary = normalized.get("review_summary")
        if not isinstance(summary, str) or not summary.strip():
            normalized["review_summary"] = "Needs revision for safer and clearer wording."

        if approval_recommendation not in _APPROVAL_TO_STATUS:
            normalized["approval_recommendation"] = "revise"
        else:
            normalized["approval_recommendation"] = approval_recommendation

        # Safety override: if high-severity medical risk exists, never pass.
        if self._has_high_medical_risk(normalized["risk_flags"]):
            normalized["status"] = "blocked"
            normalized["approval_recommendation"] = "block"

        # Safety guidance: medium/high hard-sell pressure should usually need revision.
        if normalized["status"] == "pass" and self._has_medium_or_high_pressure_risk(normalized["risk_flags"]):
            normalized["status"] = "needs_revision"
            normalized["approval_recommendation"] = "revise"

        return normalized

    @staticmethod
    def _clamp_score(value: Any) -> int:
        try:
            numeric = int(value)
        except (TypeError, ValueError):
            numeric = 60
        return max(0, min(100, numeric))

    @staticmethod
    def _has_high_medical_risk(risk_flags: List[Dict[str, Any]]) -> bool:
        for flag in risk_flags:
            if not isinstance(flag, dict):
                continue
            flag_type = str(flag.get("type") or "").strip().lower()
            severity = str(flag.get("severity") or "").strip().lower()
            if flag_type in {"medical_claim", "guaranteed_outcome"} and severity == "high":
                return True
        return False

    @staticmethod
    def _has_medium_or_high_pressure_risk(risk_flags: List[Dict[str, Any]]) -> bool:
        for flag in risk_flags:
            if not isinstance(flag, dict):
                continue
            flag_type = str(flag.get("type") or "").strip().lower()
            severity = str(flag.get("severity") or "").strip().lower()
            if flag_type in {"hard_sell", "fear_pressure"} and severity in {"medium", "high"}:
                return True
        return False
