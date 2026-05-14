from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.content_draft import ContentDraft
from app.services.deepseek_provider import DeepSeekLLMProvider
from app.services.event_log import EventLog
from app.services.llm_provider import LLMProvider
from app.services.prompt_registry import load_prompt
from app.services.task_queue import TaskQueue


ALLOWED_DRAFT_STATUSES = {"draft", "needs_revision", "approved", "rejected"}
TIMEOUT_ERROR_MARKERS = ("timed out", "timeout", "read operation timed out")


class ContentDraftService:
    def __init__(self, db: Session):
        self.db = db
        self.tasks = TaskQueue(db)
        self.events = EventLog(db)

    def create_draft_from_task(
        self,
        task_id: int,
        title: Optional[str] = None,
        channel_hint: Optional[str] = None,
        target_audience: Optional[str] = None,
        created_by: str = "ceo_agent",
    ) -> ContentDraft:
        task = self.tasks.require_task(task_id)
        draft = ContentDraft(
            task_id=task.id,
            title=title or task.title,
            channel_hint=channel_hint,
            target_audience=target_audience,
            source_decision_json=task.ceo_decision_json,
            draft_text=None,
            status="draft",
            generation_state="idle",
            retry_count=0,
            version=1,
            created_by=created_by,
        )
        self.db.add(draft)
        self.db.commit()
        self.db.refresh(draft)

        self.events.log(
            "draft_created",
            actor=created_by,
            task_id=task.id,
            message=f"Content draft created for task {task.id}.",
            metadata={"draft_id": draft.id, "status": draft.status},
        )
        return draft

    def update_status(
        self,
        draft_id: int,
        status: str,
        review_notes: Optional[str] = None,
        actor: str = "admin",
    ) -> ContentDraft:
        if status not in ALLOWED_DRAFT_STATUSES:
            raise ValueError(f"Invalid draft status: {status}")

        draft = self.require_draft(draft_id)
        old_status = draft.status
        draft.status = status
        draft.review_notes = review_notes
        draft.updated_at = datetime.utcnow()
        if status in {"needs_revision", "approved", "rejected"}:
            draft.reviewed_at = datetime.utcnow()

        self.db.add(draft)
        self.db.commit()
        self.db.refresh(draft)
        self.events.log(
            "draft_status_changed",
            actor=actor,
            task_id=draft.task_id,
            message=f"Draft status changed from {old_status} to {status}.",
            metadata={"draft_id": draft.id, "old_status": old_status, "new_status": status},
        )
        return draft

    def get_draft(self, draft_id: int) -> Optional[ContentDraft]:
        return self.db.get(ContentDraft, draft_id)

    def require_draft(self, draft_id: int) -> ContentDraft:
        draft = self.get_draft(draft_id)
        if draft is None:
            raise ValueError(f"ContentDraft {draft_id} was not found.")
        return draft

    def list_drafts(self, status: Optional[str] = None, include_archived: bool = False) -> list[ContentDraft]:
        stmt = select(ContentDraft).order_by(ContentDraft.created_at.desc())
        if status is not None:
            stmt = stmt.where(ContentDraft.status == status)
        if not include_archived:
            stmt = stmt.where(ContentDraft.is_archived.is_(False))
        return list(self.db.scalars(stmt))

    def archive_draft(self, draft_id: int, actor: str = "admin") -> ContentDraft:
        draft = self.require_draft(draft_id)
        draft.is_archived = True
        draft.archived_at = datetime.utcnow()
        draft.updated_at = datetime.utcnow()
        self.db.add(draft)
        self.db.commit()
        self.db.refresh(draft)
        self.events.log(
            "draft_archived",
            actor=actor,
            task_id=draft.task_id,
            message=f"Draft {draft.id} archived.",
            metadata={"draft_id": draft.id},
        )
        return draft

    def mark_generation_started(self, draft_id: int) -> ContentDraft:
        draft = self.require_draft(draft_id)
        draft.generation_state = "generating"
        draft.updated_at = datetime.utcnow()
        self.db.add(draft)
        self.db.commit()
        self.db.refresh(draft)
        return draft

    def mark_generation_failed(self, draft_id: int, error_message: str) -> ContentDraft:
        draft = self.require_draft(draft_id)
        draft.generation_state = "failed"
        draft.retry_count = max(draft.retry_count, 0) + 1
        draft.last_error = (error_message or "Draft generation failed.").strip()
        draft.last_error_at = datetime.utcnow()
        draft.updated_at = datetime.utcnow()
        self.db.add(draft)
        self.db.commit()
        self.db.refresh(draft)
        return draft

    def mark_generation_succeeded(self, draft_id: int) -> ContentDraft:
        draft = self.require_draft(draft_id)
        draft.generation_state = "ready"
        draft.last_error = None
        draft.last_error_at = None
        draft.updated_at = datetime.utcnow()
        self.db.add(draft)
        self.db.commit()
        self.db.refresh(draft)
        return draft

    def build_retry_recommendation(self, draft: ContentDraft) -> str | None:
        if not draft.last_error:
            return None
        error_text = draft.last_error.lower()
        if not any(marker in error_text for marker in TIMEOUT_ERROR_MARKERS):
            return None

        message = (
            "Draft generation failed. Please retry. If repeated timeouts continue, "
            "split this request into a shorter draft or smaller section."
        )
        if draft.retry_count >= 2:
            message += " Recommended split: separate into 1) outline 2) section draft 3) CTA draft."
        return message

    def generate_draft(
        self,
        draft_id: int,
        llm_provider: Optional[LLMProvider] = None,
        actor: str = "ceo_agent",
    ) -> ContentDraft:
        draft = self.mark_generation_started(draft_id)
        task = self.tasks.require_task(draft.task_id)
        provider = llm_provider or DeepSeekLLMProvider(self.db)
        try:
            response = provider.chat(
                self._build_generation_messages(draft=draft, task_title=task.title, task_description=task.description),
                temperature=0.3,
                task_id=task.id,
                json_mode=False,
            )
        except Exception as exc:
            error_message = str(exc).strip() or "Draft generation failed."
            self.mark_generation_failed(draft.id, error_message)
            self.events.log(
                "error",
                actor=actor,
                task_id=task.id,
                message=error_message,
                metadata={"draft_id": draft.id, "stage": "draft_generation"},
            )
            raise ValueError(error_message) from exc

        if not response.success:
            error_message = response.error or "Draft generation failed."
            self.mark_generation_failed(draft.id, error_message)
            self.events.log(
                "error",
                actor=actor,
                task_id=task.id,
                message=error_message,
                metadata={"draft_id": draft.id, "stage": "draft_generation"},
            )
            raise ValueError(error_message)

        draft_text = (response.raw_text or "").strip()
        if not draft_text:
            error_message = "Draft generation returned empty content."
            self.mark_generation_failed(draft.id, error_message)
            self.events.log(
                "error",
                actor=actor,
                task_id=task.id,
                message=error_message,
                metadata={"draft_id": draft.id, "stage": "draft_generation"},
            )
            raise ValueError(error_message)

        draft.draft_text = draft_text
        self.db.add(draft)
        self.db.flush()
        draft = self.mark_generation_succeeded(draft.id)
        self.events.log(
            "draft_generated",
            actor=actor,
            task_id=draft.task_id,
            message=f"Draft generated for draft {draft.id}.",
            metadata={"draft_id": draft.id, "status": draft.status, "version": draft.version},
        )
        return draft

    def revise_draft(
        self,
        draft_id: int,
        revision_instruction: str,
        llm_provider: Optional[LLMProvider] = None,
        actor: str = "admin",
    ) -> ContentDraft:
        draft = self.require_draft(draft_id)
        task = self.tasks.require_task(draft.task_id)
        provider = llm_provider or DeepSeekLLMProvider(self.db)
        self.events.log(
            "draft_revision_requested",
            actor=actor,
            task_id=draft.task_id,
            message=f"Draft revision requested for draft {draft.id}.",
            metadata={"draft_id": draft.id},
        )

        response = provider.chat(
            self._build_revision_messages(
                draft=draft,
                task_title=task.title,
                task_description=task.description,
                revision_instruction=revision_instruction,
            ),
            temperature=0.2,
            task_id=task.id,
            json_mode=False,
        )
        if not response.success:
            error_message = response.error or "Draft revision failed."
            self.events.log(
                "error",
                actor=actor,
                task_id=task.id,
                message=error_message,
                metadata={"draft_id": draft.id, "stage": "draft_revision"},
            )
            raise ValueError(error_message)

        draft.draft_text = (response.raw_text or "").strip()
        draft.version = max(draft.version, 1) + 1
        draft.status = "draft"
        draft.updated_at = datetime.utcnow()
        self.db.add(draft)
        self.db.commit()
        self.db.refresh(draft)
        self.events.log(
            "draft_revised",
            actor=actor,
            task_id=draft.task_id,
            message=f"Draft revised for draft {draft.id}.",
            metadata={"draft_id": draft.id, "status": draft.status, "version": draft.version},
        )
        return draft

    def _build_generation_messages(self, draft: ContentDraft, task_title: str, task_description: str):
        system_prompt = load_prompt("content_draft_system.md")
        user_prompt = f"""Task title:
{task_title}

Task description:
{task_description}

Draft title:
{draft.title}

Channel hint:
{draft.channel_hint or "not specified"}

Target audience:
{draft.target_audience or "not specified"}

CEO decision snapshot:
{draft.source_decision_json or "not available"}

Generate one content draft for human review only.
"""
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    def _build_revision_messages(
        self,
        draft: ContentDraft,
        task_title: str,
        task_description: str,
        revision_instruction: str,
    ):
        system_prompt = load_prompt("content_draft_revision.md")
        user_prompt = f"""Task title:
{task_title}

Task description:
{task_description}

Current draft text:
{draft.draft_text or ""}

Revision instruction:
{revision_instruction}

Return revised draft text only.
"""
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
