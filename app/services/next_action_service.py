from __future__ import annotations

import subprocess
from datetime import datetime
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.content_draft import ContentDraft
from app.models.task import Task
from app.services.task_queue import TaskQueue


PROHIBITED_ACTIONS = [
    "Do not enable agents.",
    "Do not connect platforms.",
    "Do not auto-post.",
    "Do not auto-DM.",
    "Do not auto-comment.",
    "Do not start Phase B.",
    "Do not add content performance log.",
    "Do not add execution readiness gate.",
    "Approved means human use/copying only, not published.",
]

VALIDATION_MARKERS = ("validation", "test", "failed state validation")
RECOVERY_HINTS = {
    "needs_attention": (
        "Check the reason, review last_error or review notes, then decide whether to revise, "
        "retry, or archive manually."
    ),
    "failed_production_drafts": (
        "Review last_error. Retry manually with a shorter prompt or split the request into smaller drafts."
    ),
    "validation_test_records": (
        "No production action needed. This record is for UI validation only, not a production blocker."
    ),
    "ready_for_review": (
        "Open the draft, review the content, run quality review if needed, then manually decide "
        "whether to revise or approve."
    ),
    "approved_for_human_copy": (
        "approved is human-use/copying only, not published. Copy manually if needed."
    ),
    "archived": (
        "No action needed. Use show_archived=1 only when reviewing old records."
    ),
}


class NextActionService:
    def __init__(self, db: Session):
        self.db = db

    def get_version_status(self) -> dict[str, str]:
        latest_tag = self._get_latest_git_tag()
        current_displayed_version = latest_tag or "unknown"
        return {
            "current_displayed_version": current_displayed_version,
            "latest_git_tag": latest_tag or "unknown",
        }

    def get_task_summary(self) -> dict[str, object]:
        active_tasks = self.db.scalar(
            select(func.count(Task.id)).where(Task.is_archived.is_(False))
        ) or 0
        archived_tasks = self.db.scalar(
            select(func.count(Task.id)).where(Task.is_archived.is_(True))
        ) or 0
        active_task_records = TaskQueue(self.db).list_tasks_with_archive(
            limit=1,
            include_archived=False,
        )
        first_active_task = active_task_records[0] if active_task_records else None
        return {
            "active_count": active_tasks,
            "archived_count": archived_tasks,
            "first_active_title": first_active_task.title if first_active_task else None,
        }

    def get_draft_summary(self) -> dict[str, object]:
        active_drafts = self.db.scalar(
            select(func.count(ContentDraft.id)).where(ContentDraft.is_archived.is_(False))
        ) or 0
        archived_drafts = self.db.scalar(
            select(func.count(ContentDraft.id)).where(ContentDraft.is_archived.is_(True))
        ) or 0
        failed_drafts = self.db.scalar(
            select(func.count(ContentDraft.id)).where(ContentDraft.generation_state == "failed")
        ) or 0
        ready_drafts = self.db.scalar(
            select(func.count(ContentDraft.id)).where(ContentDraft.generation_state == "ready")
        ) or 0
        first_failed_draft = self.db.scalar(
            select(ContentDraft)
            .where(ContentDraft.generation_state == "failed")
            .order_by(ContentDraft.updated_at.desc())
        )
        failed_draft_records = list(
            self.db.scalars(
                select(ContentDraft)
                .where(ContentDraft.generation_state == "failed")
                .order_by(ContentDraft.updated_at.desc())
            )
        )
        real_failed_drafts = [
            draft for draft in failed_draft_records if not self.is_validation_record(draft.title)
        ]
        validation_failed_drafts = [
            draft for draft in failed_draft_records if self.is_validation_record(draft.title)
        ]
        return {
            "active_count": active_drafts,
            "archived_count": archived_drafts,
            "failed_count": failed_drafts,
            "ready_count": ready_drafts,
            "first_failed_title": first_failed_draft.title if first_failed_draft else None,
            "real_failed_count": len(real_failed_drafts),
            "validation_failed_count": len(validation_failed_drafts),
            "first_real_failed_title": real_failed_drafts[0].title if real_failed_drafts else None,
        }

    def get_next_actions(self) -> list[str]:
        version_status = self.get_version_status()
        task_summary = self.get_task_summary()
        draft_summary = self.get_draft_summary()
        review_queue = self.get_review_queue_items()

        actions: list[str] = []
        failed_production_items = review_queue["failed_production_drafts"]
        first_active_title = task_summary["first_active_title"]
        latest_tag = version_status["latest_git_tag"]

        if failed_production_items:
            actions.append(f"Review failed draft: {failed_production_items[0]['title']}")
        elif draft_summary["validation_failed_count"]:
            actions.append("Validation failed draft exists for UI testing; not a production blocker.")
        elif review_queue["needs_attention"]:
            actions.append(f"Review queue item needs attention: {review_queue['needs_attention'][0]['title']}")
        if latest_tag == "v0.1.7.1":
            actions.append("Plan v0.1.8 only; do not enter Phase B")
        if first_active_title:
            actions.append(f"Continue active task: {first_active_title}")
        if len(actions) < 3:
            actions.append("Use the handoff summary below before starting a new conversation")
        if not actions:
            actions.append("System looks stable; no urgent action")
        return actions[:3]

    def get_prohibited_actions(self) -> list[str]:
        return list(PROHIBITED_ACTIONS)

    def build_handoff_summary(self) -> str:
        version_status = self.get_version_status()
        task_summary = self.get_task_summary()
        draft_summary = self.get_draft_summary()
        next_actions = self.get_next_actions()
        prohibited_actions = self.get_prohibited_actions()

        system_status = self._determine_system_status(
            task_summary=task_summary,
            draft_summary=draft_summary,
        )

        lines = [
            "Identity: 銳思維思 AI 營運系統總顧問",
            "Final goal: build 銳思維思 as AI operating mother system before copying to downline",
            f"Current version: {version_status['current_displayed_version']}",
            f"Latest tag: {version_status['latest_git_tag']}",
            f"Current system status: {system_status}",
            f"Active tasks count: {task_summary['active_count']}",
            f"Failed drafts count: {draft_summary['failed_count']}",
            f"Real failed drafts count: {draft_summary['real_failed_count']}",
            (
                "Archived counts: "
                f"tasks={task_summary['archived_count']}, drafts={draft_summary['archived_count']}"
            ),
            "Top next actions:",
        ]
        lines.extend(f"- {action}" for action in next_actions)
        lines.append("Prohibited actions:")
        lines.extend(f"- {action}" for action in prohibited_actions)
        lines.append(
            f"Generated timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        return "\n".join(lines)

    def build_codex_task_brief(self) -> str:
        version_status = self.get_version_status()
        task_summary = self.get_task_summary()
        draft_summary = self.get_draft_summary()
        review_queue = self.get_review_queue_items()
        next_actions = self.get_next_actions() or ["No urgent next action. Review dashboard state manually."]
        prohibited_actions = self.get_prohibited_actions()
        handoff_summary = self.build_handoff_summary().strip() or "No handoff summary available. Use current dashboard state."

        review_queue_lines = [
            f"- Needs Attention: {len(review_queue['needs_attention'])}",
            f"- Failed Production Drafts: {len(review_queue['failed_production_drafts'])}",
            f"- Validation / Test Records: {len(review_queue['validation_test_records'])}",
            f"- Ready for Review: {len(review_queue['ready_for_review'])}",
            f"- Approved for Human Copy: {len(review_queue['approved_for_human_copy'])}",
            f"- Archived: {len(review_queue['archived'])}",
        ]

        lines = [
            "Title: Lobster CNS Codex Task Brief",
            f"Current version / latest tag: {version_status.get('current_displayed_version', 'unknown')} / {version_status.get('latest_git_tag', 'unknown')}",
            "Goal: Prepare a safe, human-reviewed Codex task brief for manual copy/paste only.",
            "Current context:",
            f"- Active tasks: {task_summary.get('active_count', 0)}",
            f"- Failed drafts: {draft_summary.get('failed_count', 0)}",
            f"- Active drafts: {draft_summary.get('active_count', 0)}",
            "Review Queue summary:",
        ]
        lines.extend(review_queue_lines)
        lines.extend(
            [
                f"Recommended next action: {next_actions[0] if next_actions else 'No urgent next action. Review dashboard state manually.'}",
                "Explicitly out of scope:",
                "- Do not connect platforms.",
                "- Do not enable agents.",
                "- Do not auto-post.",
                "- Do not auto-DM.",
                "- Do not auto-comment.",
                "- Do not start Phase B.",
                "- Do not add content performance log.",
                "- Do not add execution readiness gate.",
                "Files likely affected: unknown / to be determined",
                "Tests required:",
                "- Run .venv/bin/pytest -q",
                "- Verify /dashboard still renders",
                "- Verify /dashboard/tasks still renders",
                "- Verify /dashboard/drafts still renders",
                "Safety constraints:",
                "- This brief is for human review and manual use only.",
                "- Not approved.",
                "- Not published.",
                "- Not executed.",
                "- Do not auto-send to Codex.",
                "- Do not auto-execute.",
                "- Do not connect platforms.",
                "- Do not enable agents.",
                "- Approved means human use/copying only, not published.",
                "- Do not stage unrelated files.",
                "- Do not commit unless instructed.",
                "- Do not tag unless instructed.",
                "- Do not push.",
                "Report format:",
                "- Files changed",
                "- Tests run",
                "- Risk or blocker",
                "- Manual verification result",
                "Human review only notice:",
                "- This brief is for human review and manual use only.",
                f"Handoff summary:\n{handoff_summary}",
            ]
        )
        return "\n".join(lines)

    def build_dashboard_panel(self) -> dict[str, object]:
        version_status = self.get_version_status()
        task_summary = self.get_task_summary()
        draft_summary = self.get_draft_summary()
        review_queue = self.get_review_queue_items()
        return {
            "version_status": version_status,
            "task_summary": task_summary,
            "draft_summary": draft_summary,
            "system_status": self._determine_system_status(
                task_summary=task_summary,
                draft_summary=draft_summary,
            ),
            "review_queue": review_queue,
            "review_queue_hints": {
                "needs_attention": self.get_recovery_hints("needs_attention"),
                "failed_production_drafts": self.get_recovery_hints("failed_production_drafts"),
                "validation_test_records": self.get_recovery_hints("validation_test_records"),
                "ready_for_review": self.get_recovery_hints("ready_for_review"),
                "approved_for_human_copy": self.get_recovery_hints("approved_for_human_copy"),
                "archived": self.get_recovery_hints("archived"),
            },
            "next_actions": self.get_next_actions(),
            "prohibited_actions": self.get_prohibited_actions(),
            "handoff_summary": self.build_handoff_summary(),
            "codex_task_brief": self.build_codex_task_brief(),
        }

    def get_review_queue_items(self) -> dict[str, list[dict[str, object]]]:
        drafts = list(
            self.db.scalars(select(ContentDraft).order_by(ContentDraft.updated_at.desc()))
        )
        return {
            "needs_attention": self.get_needs_attention_items(drafts),
            "failed_production_drafts": self.get_failed_production_drafts(drafts),
            "validation_test_records": self.get_validation_test_records(drafts),
            "ready_for_review": self.get_ready_for_review_items(drafts),
            "approved_for_human_copy": self.get_approved_for_human_copy_items(drafts),
            "archived": self.get_archived_items(drafts),
        }

    def get_needs_attention_items(
        self, drafts: list[ContentDraft] | None = None
    ) -> list[dict[str, object]]:
        drafts = drafts or self._list_drafts_for_queue()
        items: list[dict[str, object]] = []
        seen_ids: set[int] = set()
        for draft in drafts:
            if draft.is_archived or self.is_validation_record(draft.title):
                continue
            if draft.generation_state == "failed":
                items.append(self._serialize_draft_item(draft))
                seen_ids.add(draft.id)
                continue
            if draft.status == "needs_revision" and draft.id not in seen_ids:
                items.append(self._serialize_draft_item(draft))
                seen_ids.add(draft.id)
                continue
            if (
                draft.retry_count >= 2
                and draft.last_error
                and draft.id not in seen_ids
            ):
                items.append(self._serialize_draft_item(draft))
                seen_ids.add(draft.id)
        return items

    def get_failed_production_drafts(
        self, drafts: list[ContentDraft] | None = None
    ) -> list[dict[str, object]]:
        drafts = drafts or self._list_drafts_for_queue()
        return [
            self._serialize_draft_item(draft)
            for draft in drafts
            if draft.generation_state == "failed"
            and not draft.is_archived
            and not self.is_validation_record(draft.title)
        ]

    def get_validation_test_records(
        self, drafts: list[ContentDraft] | None = None
    ) -> list[dict[str, object]]:
        drafts = drafts or self._list_drafts_for_queue()
        return [
            self._serialize_draft_item(draft)
            for draft in drafts
            if self.is_validation_record(draft.title)
        ]

    def get_ready_for_review_items(
        self, drafts: list[ContentDraft] | None = None
    ) -> list[dict[str, object]]:
        drafts = drafts or self._list_drafts_for_queue()
        return [
            self._serialize_draft_item(draft)
            for draft in drafts
            if draft.generation_state == "ready"
            and draft.status == "draft"
            and not draft.is_archived
        ]

    def get_approved_for_human_copy_items(
        self, drafts: list[ContentDraft] | None = None
    ) -> list[dict[str, object]]:
        drafts = drafts or self._list_drafts_for_queue()
        return [
            self._serialize_draft_item(draft)
            for draft in drafts
            if draft.status == "approved" and not draft.is_archived
        ]

    def get_archived_items(
        self, drafts: list[ContentDraft] | None = None
    ) -> list[dict[str, object]]:
        drafts = drafts or self._list_drafts_for_queue()
        return [
            self._serialize_draft_item(draft)
            for draft in drafts
            if draft.is_archived
        ]

    def is_validation_record(self, title: str | None) -> bool:
        if not title:
            return False
        normalized = title.lower()
        return any(marker in normalized for marker in VALIDATION_MARKERS)

    def get_recovery_hints(self, category_or_status: str) -> str:
        return RECOVERY_HINTS.get(
            category_or_status,
            "Review the current state and continue with manual operator judgment.",
        )

    def get_manual_next_step(self, draft: ContentDraft) -> str:
        if draft.is_archived:
            return self.get_recovery_hints("archived")
        if self.is_validation_record(draft.title):
            return self.get_recovery_hints("validation_test_records")
        if draft.generation_state == "failed":
            return self.get_recovery_hints("failed_production_drafts")
        if draft.status == "approved":
            return self.get_recovery_hints("approved_for_human_copy")
        if draft.generation_state == "ready" and draft.status == "draft":
            return self.get_recovery_hints("ready_for_review")
        if draft.status == "needs_revision":
            return self.get_recovery_hints("needs_attention")
        if draft.retry_count >= 2 and draft.last_error:
            return self.get_recovery_hints("needs_attention")
        return self.get_recovery_hints("ready_for_review")

    def _determine_system_status(
        self,
        task_summary: dict[str, object],
        draft_summary: dict[str, object],
    ) -> str:
        if draft_summary["real_failed_count"]:
            return "needs_attention"
        if draft_summary["validation_failed_count"]:
            return "validation_only"
        if task_summary["active_count"]:
            return "active"
        return "stable"

    def _list_drafts_for_queue(self) -> list[ContentDraft]:
        return list(
            self.db.scalars(select(ContentDraft).order_by(ContentDraft.updated_at.desc()))
        )

    def _serialize_draft_item(self, draft: ContentDraft) -> dict[str, object]:
        return {
            "id": draft.id,
            "title": draft.title,
            "status": draft.status,
            "generation_state": draft.generation_state,
            "is_archived": draft.is_archived,
            "retry_count": draft.retry_count,
            "last_error": draft.last_error,
            "last_error_at": draft.last_error_at,
            "updated_at": draft.updated_at,
            "is_validation": self.is_validation_record(draft.title),
        }

    def _get_latest_git_tag(self) -> str | None:
        repo_root = Path(__file__).resolve().parents[2]
        try:
            result = subprocess.run(
                ["git", "tag", "--sort=-v:refname"],
                cwd=repo_root,
                capture_output=True,
                text=True,
                check=True,
            )
        except Exception:
            return None

        tags = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        return tags[0] if tags else None
