from __future__ import annotations

from copy import deepcopy
from typing import Dict, List, Optional

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.models.task import Task
from app.schemas.ceo_decision import CEODecision
from app.services.event_log import EventLog
from app.services.llm_provider import LLMProvider, LLMResponse
from app.services.memory_service import MemoryService
from app.services.prompt_registry import load_prompt
from app.services.task_queue import TaskQueue


class CEOAgent:
    _ALLOWED_MEMORY_NAMESPACES = {"business", "brand", "sales", "content", "system", "user"}

    def __init__(self, db: Session, llm_provider: LLMProvider):
        self.db = db
        self.llm_provider = llm_provider
        self.tasks = TaskQueue(db)
        self.memory = MemoryService(db)
        self.events = EventLog(db)

    def review_task(self, task_id: int) -> CEODecision:
        task = self.tasks.require_task(task_id)
        self.tasks.update_status(task, "reviewing", actor="ceo_agent")
        self.events.log(
            "task_review_started",
            actor="ceo_agent",
            task_id=task.id,
            message="CEOAgent started reviewing task.",
        )

        memories = self.memory.retrieve_relevant(
            f"{task.title}\n{task.description}",
            task_id=task.id,
        )
        response = self.llm_provider.chat(
            self._build_messages(task, memories),
            temperature=0.2,
            task_id=task.id,
            json_mode=True,
        )
        decision = self._decision_from_response(response)

        if decision is None:
            repair_response = self.llm_provider.chat(
                self._build_repair_messages(response.raw_text),
                temperature=0.0,
                task_id=task.id,
                json_mode=True,
            )
            decision = self._decision_from_response(repair_response)
            if decision is None:
                raw_output = repair_response.raw_text or response.raw_text
                error = repair_response.error or "CEO decision JSON repair failed."
                self.tasks.fail_task(task, error=error, raw_output=raw_output)
                self.events.log(
                    "error",
                    actor="ceo_agent",
                    task_id=task.id,
                    message=error,
                )
                raise ValueError(error)
            response = repair_response

        self.tasks.save_ceo_decision(task, decision, response.raw_text)
        self.tasks.update_status(task, decision.recommended_next_status, actor="ceo_agent")

        for memory in decision.memory_to_save:
            self.memory.create_memory(
                namespace=memory.namespace,
                category=memory.category,
                content=memory.content,
                importance=memory.importance,
                source="ceo_agent",
                task_id=task.id,
                actor="ceo_agent",
            )

        self.events.log(
            "ceo_decision_created",
            actor="ceo_agent",
            task_id=task.id,
            message="CEOAgent created a structured decision.",
            metadata={"suggested_agent_role": decision.suggested_agent_role},
        )
        self.events.log(
            "task_review_completed",
            actor="ceo_agent",
            task_id=task.id,
            message="CEOAgent completed task review.",
        )
        return decision

    def _build_messages(self, task: Task, memories) -> List[Dict[str, str]]:
        system_prompt = load_prompt("ceo_agent_system.md")
        memory_lines = [
            f"- [{memory.namespace}/{memory.category}/importance={memory.importance}] {memory.content}"
            for memory in memories
        ]
        memory_text = "\n".join(memory_lines) if memory_lines else "No relevant memory yet."
        user_prompt = f"""Task title:
{task.title}

Task description:
{task.description}

Relevant memory:
{memory_text}

Return the CEO decision JSON only."""
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    def _build_repair_messages(self, raw_output: str) -> List[Dict[str, str]]:
        repair_prompt = load_prompt("ceo_decision_repair.md")
        return [
            {"role": "system", "content": repair_prompt},
            {"role": "user", "content": raw_output},
        ]

    def _decision_from_response(self, response: LLMResponse) -> Optional[CEODecision]:
        if not response.success:
            return None
        if response.parsed_json is None:
            return None
        try:
            normalized = self._normalize_decision_payload(response.parsed_json)
            return CEODecision.model_validate(normalized)
        except ValidationError:
            return None

    def _normalize_decision_payload(self, payload):
        if not isinstance(payload, dict):
            return payload
        normalized = deepcopy(payload)

        suggested = normalized.get("suggested_agent_role")
        primary = normalized.get("primary_agent_role")

        if not primary and suggested:
            normalized["primary_agent_role"] = suggested
        if not suggested and primary:
            normalized["suggested_agent_role"] = primary

        normalized.setdefault("supporting_agent_roles", [])
        normalized["simulation_only"] = True
        normalized["requires_human_approval"] = True

        checklist = normalized.get("approval_checklist")
        if not isinstance(checklist, dict):
            checklist = {}
            normalized["approval_checklist"] = checklist

        checklist["requires_human_review"] = True
        checklist["external_action_blocked"] = True
        checklist.setdefault("medical_claims_checked", True)
        checklist.setdefault("sales_pressure_checked", True)
        checklist.setdefault("brand_tone_checked", True)
        checklist.setdefault("platform_risk_checked", True)

        memory_to_save = normalized.get("memory_to_save")
        if isinstance(memory_to_save, list):
            for item in memory_to_save:
                if not isinstance(item, dict):
                    continue
                namespace = item.get("namespace")
                if namespace in self._ALLOWED_MEMORY_NAMESPACES:
                    continue

                item["namespace"] = "system"
                content = item.get("content")
                if isinstance(content, str):
                    marker = f"[normalized from namespace={namespace}] "
                    if not content.startswith(marker):
                        item["content"] = f"{marker}{content}"

        return normalized
