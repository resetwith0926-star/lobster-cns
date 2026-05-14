from __future__ import annotations

import json
from typing import Optional
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.event import Event
from app.models.llm_call import LLMCall
from app.models.memory import Memory
from app.models.task import Task
from app.models.content_draft import ContentDraft
from app.models.content_draft_review import ContentDraftReview
from app.services.agent_registry import AgentRegistry
from app.services.content_draft_service import ContentDraftService
from app.services.content_quality_review_service import ContentQualityReviewService
from app.services.deepseek_provider import DeepSeekLLMProvider
from app.services.ceo_agent import CEOAgent
from app.services.event_log import EventLog
from app.services.memory_service import MemoryService
from app.services.next_action_service import NextActionService
from app.services.task_queue import TaskQueue


router = APIRouter(tags=["dashboard"])
templates = Jinja2Templates(directory="app/templates")

STATUS_LABELS = {
    "pending": "待處理",
    "reviewing": "審查中",
    "planned": "已規劃",
    "waiting_approval": "等待人工批准",
    "completed": "已完成",
    "failed": "失敗",
    "cancelled": "已取消",
}

EVENT_LABELS = {
    "task_created": "建立任務",
    "task_review_started": "開始審查",
    "task_review_completed": "審查完成",
    "task_status_changed": "狀態變更",
    "ceo_decision_created": "CEO 決策已建立",
    "llm_call_started": "LLM 呼叫開始",
    "llm_call_completed": "LLM 呼叫完成",
    "llm_call_failed": "LLM 呼叫失敗",
    "memory_created": "建立記憶",
    "memory_retrieved": "讀取記憶",
    "agent_registry_seeded": "角色表初始化",
    "task_archived": "任務已封存",
    "draft_archived": "草稿已封存",
    "error": "錯誤",
}

PRIORITY_LABELS = {
    "low": "低",
    "medium": "中",
    "high": "高",
    "urgent": "緊急",
}

RISK_LABELS = {
    "low": "低風險",
    "medium": "中風險",
    "high": "高風險",
}

ROLE_LABELS = {
    "ceo_agent": "CEO 大腦",
    "content_agent": "內容代理",
    "sales_agent": "銷售代理",
    "dev_agent": "開發代理",
    "facebook_page_agent": "FB 粉專代理",
    "facebook_personal_agent": "FB 個人帳號代理",
    "instagram_agent": "IG 代理",
    "x_agent": "X 代理",
    "line_agent": "LINE 代理",
    "telegram_agent": "Telegram 代理",
    "unknown": "尚未判定",
}

NAMESPACE_OPTIONS = [
    ("business", "事業"),
    ("brand", "品牌"),
    ("sales", "銷售"),
    ("content", "內容"),
    ("system", "系統"),
    ("user", "使用者"),
]

CATEGORY_OPTIONS = [
    ("rule", "規則"),
    ("preference", "偏好"),
    ("decision", "決策"),
    ("strategy", "策略"),
    ("warning", "警示"),
    ("note", "備註"),
]


@router.get("/")
@router.get("/dashboard")
def index(request: Request, db: Session = Depends(get_db)):
    next_action_panel = NextActionService(db).build_dashboard_panel()
    counts = [
        {"label": "任務總數", "value": db.scalar(select(func.count(Task.id)))},
        {"label": "待處理任務", "value": _count_tasks(db, "pending")},
        {"label": "審查中任務", "value": _count_tasks(db, "reviewing")},
        {"label": "已規劃任務", "value": _count_tasks(db, "planned")},
        {"label": "等待批准任務", "value": _count_tasks(db, "waiting_approval")},
        {"label": "失敗任務", "value": _count_tasks(db, "failed")},
        {"label": "記憶數量", "value": db.scalar(select(func.count(Memory.id)))},
        {"label": "LLM 呼叫數", "value": db.scalar(select(func.count(LLMCall.id)))},
    ]
    recent_errors = list(
        db.scalars(
            select(Event)
            .where(Event.event_type == "error")
            .order_by(Event.created_at.desc())
            .limit(5)
        )
    )
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "counts": counts,
            "operator_summary": _build_operator_summary(db),
            "next_action_panel": next_action_panel,
            "recent_errors": recent_errors,
            "recent_events": EventLog(db).list_recent(limit=10),
            "event_labels": EVENT_LABELS,
        },
    )


@router.get("/dashboard/tasks")
def dashboard_tasks(request: Request, db: Session = Depends(get_db)):
    show_archived = request.query_params.get("show_archived") == "1"
    tasks = TaskQueue(db).list_tasks_with_archive(limit=200, include_archived=show_archived)
    statuses = [
        "pending",
        "reviewing",
        "planned",
        "waiting_approval",
        "completed",
        "failed",
        "cancelled",
    ]
    return templates.TemplateResponse(
        request,
        "tasks.html",
        {
            "tasks": tasks,
            "show_archived": show_archived,
            "operator_summary": _build_operator_summary(db),
            "statuses": statuses,
            "status_labels": STATUS_LABELS,
            "priority_labels": PRIORITY_LABELS,
            "role_labels": ROLE_LABELS,
        },
    )


@router.post("/dashboard/tasks")
def dashboard_create_task(
    title: str = Form(...),
    description: str = Form(""),
    db: Session = Depends(get_db),
):
    TaskQueue(db).create_task(title=title, description=description, created_by="dashboard")
    return RedirectResponse("/dashboard/tasks", status_code=303)


@router.get("/dashboard/tasks/{task_id}")
def dashboard_task_detail(
    request: Request,
    task_id: int,
    db: Session = Depends(get_db),
):
    try:
        task = TaskQueue(db).require_task(task_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    decision = None
    if task.ceo_decision_json:
        try:
            parsed = json.loads(task.ceo_decision_json)
            decision = parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            decision = None
    decision_view = _build_decision_view(task, decision)
    llm_calls = list(
        db.scalars(
            select(LLMCall)
            .where(LLMCall.task_id == task.id)
            .order_by(LLMCall.created_at.desc())
        )
    )
    related_drafts = list(
        db.scalars(
            select(ContentDraft)
            .where(ContentDraft.task_id == task.id)
            .order_by(ContentDraft.updated_at.desc())
        )
    )
    return templates.TemplateResponse(
        request,
        "task_detail.html",
        {
            "task": task,
            "show_archived": request.query_params.get("show_archived") == "1",
            "decision": decision,
            "decision_view": decision_view,
            "events": EventLog(db).list_for_task(task.id),
            "llm_calls": llm_calls,
            "related_drafts": related_drafts,
            "memories": MemoryService(db).list_memories(limit=50),
            "status_labels": STATUS_LABELS,
            "event_labels": EVENT_LABELS,
            "priority_labels": PRIORITY_LABELS,
            "risk_labels": RISK_LABELS,
            "role_labels": ROLE_LABELS,
        },
    )


@router.post("/dashboard/tasks/{task_id}/archive")
def dashboard_archive_task(task_id: int, db: Session = Depends(get_db)):
    try:
        TaskQueue(db).archive_task(task_id=task_id, actor="dashboard")
    except ValueError:
        pass
    return RedirectResponse("/dashboard/tasks?show_archived=1", status_code=303)


@router.post("/dashboard/tasks/{task_id}/drafts")
def dashboard_create_draft_from_task(
    task_id: int,
    title: str = Form(""),
    channel_hint: str = Form(""),
    target_audience: str = Form(""),
    db: Session = Depends(get_db),
):
    try:
        draft = ContentDraftService(db).create_draft_from_task(
            task_id=task_id,
            title=title or None,
            channel_hint=channel_hint or None,
            target_audience=target_audience or None,
            created_by="dashboard",
        )
        return RedirectResponse(f"/dashboard/drafts/{draft.id}", status_code=303)
    except ValueError:
        return RedirectResponse(f"/dashboard/tasks/{task_id}", status_code=303)


@router.post("/dashboard/tasks/{task_id}/review")
def dashboard_review_task(task_id: int, db: Session = Depends(get_db)):
    try:
        CEOAgent(db, DeepSeekLLMProvider(db)).review_task(task_id)
    except ValueError:
        pass
    return RedirectResponse(f"/dashboard/tasks/{task_id}", status_code=303)


@router.get("/dashboard/drafts")
def dashboard_drafts(
    request: Request,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    show_archived = request.query_params.get("show_archived") == "1"
    drafts = ContentDraftService(db).list_drafts(status=status or None, include_archived=show_archived)
    return templates.TemplateResponse(
        request,
        "drafts.html",
        {
            "drafts": drafts,
            "operator_summary": _build_operator_summary(db),
            "current_status": status or "",
            "show_archived": show_archived,
            "status_options": ["draft", "needs_revision", "approved", "rejected"],
            "status_labels": {
                "draft": "草稿",
                "needs_revision": "需修訂",
                "approved": "已批准（人工可用）",
                "rejected": "已拒絕",
            },
        },
    )


@router.get("/dashboard/drafts/{draft_id}")
def dashboard_draft_detail(request: Request, draft_id: int, db: Session = Depends(get_db)):
    draft = ContentDraftService(db).get_draft(draft_id)
    if draft is None:
        return RedirectResponse("/dashboard/drafts", status_code=303)
    task = TaskQueue(db).get_task(draft.task_id)
    decision = None
    if draft.source_decision_json:
        try:
            parsed = json.loads(draft.source_decision_json)
            decision = parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            decision = None

    latest_review = db.scalars(
        select(ContentDraftReview)
        .where(ContentDraftReview.draft_id == draft.id)
        .order_by(ContentDraftReview.created_at.desc(), ContentDraftReview.id.desc())
        .limit(1)
    ).first()
    review_history = list(
        db.scalars(
            select(ContentDraftReview)
            .where(ContentDraftReview.draft_id == draft.id)
            .order_by(ContentDraftReview.created_at.desc(), ContentDraftReview.id.desc())
        )
    )

    return templates.TemplateResponse(
        request,
        "draft_detail.html",
        {
            "draft": draft,
            "task": task,
            "decision": decision,
            "latest_review": latest_review,
            "review_history": review_history,
            "draft_error": request.query_params.get("draft_error"),
            "retry_recommendation": ContentDraftService(db).build_retry_recommendation(draft),
            "status_options": ["draft", "needs_revision", "approved", "rejected"],
            "status_labels": {
                "draft": "草稿",
                "needs_revision": "需修訂",
                "approved": "已批准（人工可用）",
                "rejected": "已拒絕",
            },
        },
    )


@router.post("/dashboard/drafts/{draft_id}/generate")
def dashboard_generate_draft(draft_id: int, db: Session = Depends(get_db)):
    service = ContentDraftService(db)
    draft = service.get_draft(draft_id)
    if draft is None:
        return RedirectResponse("/dashboard/drafts", status_code=303)
    try:
        service.generate_draft(draft_id=draft_id, actor="dashboard")
    except ValueError as exc:
        error_message = f"Draft generation failed. Please retry. Reason: {str(exc).strip()}"
        query = urlencode({"draft_error": error_message})
        return RedirectResponse(f"/dashboard/drafts/{draft_id}?{query}", status_code=303)
    return RedirectResponse(f"/dashboard/drafts/{draft_id}", status_code=303)


@router.post("/dashboard/drafts/{draft_id}/archive")
def dashboard_archive_draft(draft_id: int, db: Session = Depends(get_db)):
    try:
        ContentDraftService(db).archive_draft(draft_id=draft_id, actor="dashboard")
    except ValueError:
        pass
    return RedirectResponse("/dashboard/drafts?show_archived=1", status_code=303)


@router.post("/dashboard/drafts/{draft_id}/review-quality")
def dashboard_review_draft_quality(draft_id: int, db: Session = Depends(get_db)):
    draft = ContentDraftService(db).get_draft(draft_id)
    if draft is None:
        return RedirectResponse("/dashboard/drafts", status_code=303)
    try:
        ContentQualityReviewService(db).review_draft(draft_id=draft_id, actor="dashboard")
    except ValueError:
        pass
    return RedirectResponse(f"/dashboard/drafts/{draft_id}", status_code=303)


@router.post("/dashboard/drafts/{draft_id}/revise")
def dashboard_revise_draft(
    draft_id: int,
    revision_instruction: str = Form(...),
    db: Session = Depends(get_db),
):
    service = ContentDraftService(db)
    draft = service.get_draft(draft_id)
    if draft is None:
        return RedirectResponse("/dashboard/drafts", status_code=303)
    try:
        service.revise_draft(
            draft_id=draft_id,
            revision_instruction=revision_instruction,
            actor="dashboard",
        )
    except ValueError:
        pass
    return RedirectResponse(f"/dashboard/drafts/{draft_id}", status_code=303)


@router.post("/dashboard/drafts/{draft_id}/status")
def dashboard_update_draft_status(
    draft_id: int,
    status: str = Form(...),
    review_notes: str = Form(""),
    db: Session = Depends(get_db),
):
    service = ContentDraftService(db)
    draft = service.get_draft(draft_id)
    if draft is None:
        return RedirectResponse("/dashboard/drafts", status_code=303)
    try:
        service.update_status(
            draft_id=draft_id,
            status=status,
            review_notes=review_notes or None,
            actor="dashboard",
        )
    except ValueError:
        pass
    return RedirectResponse(f"/dashboard/drafts/{draft_id}", status_code=303)


@router.get("/dashboard/agents")
def dashboard_agents(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(
        request,
        "agents.html",
        {"agents": AgentRegistry(db).list_agents(), "role_labels": ROLE_LABELS},
    )


@router.get("/dashboard/events")
def dashboard_events(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(
        request,
        "events.html",
        {"events": EventLog(db).list_recent(limit=200), "event_labels": EVENT_LABELS},
    )


@router.get("/dashboard/memory")
def dashboard_memory(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(
        request,
        "memory.html",
        {
            "memories": MemoryService(db).list_memories(limit=200),
            "namespace_options": NAMESPACE_OPTIONS,
            "category_options": CATEGORY_OPTIONS,
        },
    )


@router.post("/dashboard/memory")
def dashboard_create_memory(
    namespace: str = Form(...),
    category: str = Form(...),
    content: str = Form(...),
    importance: int = Form(1),
    db: Session = Depends(get_db),
):
    MemoryService(db).create_memory(
        namespace=namespace,
        category=category,
        content=content,
        importance=importance,
        source="dashboard",
        actor="dashboard",
    )
    return RedirectResponse("/dashboard/memory", status_code=303)


@router.get("/dashboard/llm-calls")
def dashboard_llm_calls(request: Request, db: Session = Depends(get_db)):
    calls = list(db.scalars(select(LLMCall).order_by(LLMCall.created_at.desc()).limit(100)))
    return templates.TemplateResponse(
        request,
        "llm_calls.html",
        {"llm_calls": calls},
    )


def _count_tasks(db: Session, status: str) -> int:
    return db.scalar(select(func.count(Task.id)).where(Task.status == status)) or 0


def _count_rows(db: Session, model, *criteria) -> int:
    stmt = select(func.count(model.id))
    for criterion in criteria:
        stmt = stmt.where(criterion)
    return db.scalar(stmt) or 0


def _build_operator_summary(db: Session) -> dict:
    return {
        "active_task_count": _count_rows(db, Task, Task.is_archived.is_(False)),
        "archived_task_count": _count_rows(db, Task, Task.is_archived.is_(True)),
        "active_draft_count": _count_rows(db, ContentDraft, ContentDraft.is_archived.is_(False)),
        "archived_draft_count": _count_rows(db, ContentDraft, ContentDraft.is_archived.is_(True)),
        "failed_draft_count": _count_rows(
            db,
            ContentDraft,
            ContentDraft.is_archived.is_(False),
            ContentDraft.generation_state == "failed",
        ),
        "ready_draft_count": _count_rows(
            db,
            ContentDraft,
            ContentDraft.is_archived.is_(False),
            ContentDraft.generation_state == "ready",
        ),
    }


def _parse_roles_json(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if isinstance(parsed, list):
        return [str(v) for v in parsed]
    return []


def _build_decision_view(task: Task, decision: dict | None) -> dict:
    decision = decision or {}
    suggested = decision.get("suggested_agent_role") or task.suggested_agent_role
    primary = decision.get("primary_agent_role") or task.primary_agent_role or suggested
    supporting = decision.get("supporting_agent_roles")
    if not isinstance(supporting, list):
        supporting = _parse_roles_json(task.supporting_agent_roles_json)
    rubric = decision.get("decision_rubric")
    if not isinstance(rubric, dict):
        rubric = {}
    checklist = decision.get("approval_checklist")
    if not isinstance(checklist, dict):
        checklist = {}
    return {
        "suggested_agent_role": suggested,
        "primary_agent_role": primary,
        "supporting_agent_roles": supporting,
        "decision_rubric": rubric,
        "approval_checklist": checklist,
    }
