from __future__ import annotations

import json
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.database import _apply_sqlite_startup_migration_guard
from app.models.task import Task
from app.schemas.ceo_decision import CEODecision
from app.services.event_log import EventLog


class TaskQueue:
    def __init__(self, db: Session):
        self.db = db
        self.events = EventLog(db)

    def create_task(
        self,
        title: str,
        description: str = "",
        created_by: str = "admin",
    ) -> Task:
        task = Task(
            title=title,
            description=description,
            status="pending",
            created_by=created_by,
        )
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        self.events.log(
            "task_created",
            actor=created_by,
            task_id=task.id,
            message=f"Task created: {title}",
        )
        return task

    def get_task(self, task_id: int) -> Optional[Task]:
        try:
            return self.db.get(Task, task_id)
        except OperationalError as exc:
            if "no such column: tasks.primary_agent_role" not in str(exc):
                raise
            _apply_sqlite_startup_migration_guard()
            return self.db.get(Task, task_id)

    def require_task(self, task_id: int) -> Task:
        task = self.get_task(task_id)
        if task is None:
            raise ValueError(f"Task {task_id} was not found.")
        return task

    def list_tasks(self, limit: int = 100):
        return self.list_tasks_with_archive(limit=limit, include_archived=False)

    def list_tasks_with_archive(self, limit: int = 100, include_archived: bool = False):
        stmt = select(Task)
        if not include_archived:
            stmt = stmt.where(Task.is_archived.is_(False))
        stmt = stmt.order_by(Task.created_at.desc()).limit(limit)
        return list(self.db.scalars(stmt))

    def archive_task(self, task_id: int, actor: str = "admin") -> Task:
        task = self.require_task(task_id)
        task.is_archived = True
        task.archived_at = datetime.utcnow()
        task.updated_at = datetime.utcnow()
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        self.events.log(
            "task_archived",
            actor=actor,
            task_id=task.id,
            message=f"Task {task.id} archived.",
            metadata={"task_id": task.id},
        )
        return task

    def update_status(self, task: Task, status: str, actor: str = "system") -> Task:
        old_status = task.status
        task.status = status
        task.updated_at = datetime.utcnow()
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        self.events.log(
            "task_status_changed",
            actor=actor,
            task_id=task.id,
            message=f"Task status changed from {old_status} to {status}.",
            metadata={"old_status": old_status, "new_status": status},
        )
        return task

    def save_ceo_decision(
        self,
        task: Task,
        decision: CEODecision,
        raw_output: str,
    ) -> Task:
        task.task_type = decision.task_type
        task.priority = decision.priority
        task.risk_level = decision.risk_level
        task.suggested_agent_role = decision.suggested_agent_role
        task.primary_agent_role = decision.primary_agent_role or decision.suggested_agent_role
        task.supporting_agent_roles_json = json.dumps(
            decision.supporting_agent_roles or [],
            ensure_ascii=False,
        )
        task.ceo_decision_json = decision.model_dump_json()
        task.ceo_decision_text = raw_output
        task.reasoning_summary = decision.reasoning_summary
        task.error = None
        task.reviewed_at = datetime.utcnow()
        task.updated_at = datetime.utcnow()
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        return task

    def fail_task(self, task: Task, error: str, raw_output: str = "") -> Task:
        task.error = error
        task.ceo_decision_text = raw_output
        task.updated_at = datetime.utcnow()
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        return self.update_status(task, "failed", actor="ceo_agent")

    def complete_task(self, task_id: int, result: str = "", actor: str = "admin") -> Task:
        task = self.require_task(task_id)
        task.result = result
        self.db.add(task)
        self.db.commit()
        return self.update_status(task, "completed", actor=actor)

    def cancel_task(self, task_id: int, actor: str = "admin") -> Task:
        task = self.require_task(task_id)
        return self.update_status(task, "cancelled", actor=actor)
