from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.main as main_module
from app.database import Base, get_db
from app.main import app
from app.models.content_draft import ContentDraft
from app.models.task import Task
from app.services.agent_registry import AgentRegistry


AUTH_HEADERS = {"X-Admin-Secret": "change-me"}


@pytest.fixture()
def client(monkeypatch):
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    def init_test_db():
        Base.metadata.create_all(bind=test_engine)
        db = TestingSessionLocal()
        try:
            AgentRegistry(db).ensure_default_agents()
        finally:
            db.close()

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    monkeypatch.setattr(main_module, "init_db", init_test_db)
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        test_client.app.state.testing_session_local = TestingSessionLocal
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)


def test_health_is_public(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_admin_api_rejects_missing_x_admin_secret(client):
    response = client.get("/tasks")

    assert response.status_code == 401


def test_admin_api_accepts_secret_and_creates_task(client):
    response = client.post(
        "/tasks",
        json={
            "title": "ResetWith 下週內容方向",
            "description": "Plan content direction.",
        },
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    assert response.json()["status"] == "pending"


def test_dashboard_overview_loads(client):
    response = client.get("/")

    assert response.status_code == 200
    assert "CEO 治理核心" in response.text


def test_dashboard_landing_route_loads(client):
    response = client.get("/dashboard")

    assert response.status_code == 200
    assert "CEO 治理核心" in response.text
    assert "操作摘要" in response.text
    assert "Next Action / Handoff" in response.text
    assert "Codex Task Brief Generator" in response.text
    assert "Codex Brief Practical Loop Validation" in response.text
    assert "Codex Response Evaluation Note" in response.text
    assert "Codex Result Handoff Summary" in response.text
    assert "Practical Loop Flow" in response.text
    assert "Codex Brief Acceptance Criteria" in response.text
    assert "Codex Response Evaluation Criteria" in response.text
    assert "CODEX RESULT HANDOFF SUMMARY" in response.text
    assert "Scope Control" in response.text
    assert "Forbidden Actions" in response.text
    assert "Files Changed / Tests / Git Status" in response.text
    assert "Ready to Commit" in response.text
    assert "Ready to Tag" in response.text
    assert "What changed" in response.text
    assert "Files changed" in response.text
    assert "Tests run" in response.text
    assert "Test result" in response.text
    assert "Git status" in response.text
    assert "Scope control result" in response.text
    assert "Forbidden actions check" in response.text
    assert "Ready to commit" in response.text
    assert "Ready to tag" in response.text
    assert "Prohibited actions" in response.text
    assert "Copyable handoff summary" in response.text
    assert "Human review only. This does not execute Codex." in response.text
    assert "This validation note is for human review only. It does not execute Codex and does not store validation results." in response.text
    assert "This is a human-use/manual-only checklist. It does not auto-score, auto-judge, auto-execute, commit, tag, or push." in response.text
    assert "This summary is for human reference only and is not an automated decision." in response.text
    assert "<form" not in response.text
    assert "<input" not in response.text
    assert "<select" not in response.text


def test_dashboard_handoff_clarifies_validation_failed_draft(client):
    task_resp = client.post(
        "/tasks",
        json={"title": "Validation host task", "description": "desc"},
        headers=AUTH_HEADERS,
    )
    draft_resp = client.post(
        "/drafts",
        json={"task_id": task_resp.json()["id"], "title": "Failed state validation draft"},
        headers=AUTH_HEADERS,
    )

    session_local = client.app.state.testing_session_local
    with session_local() as db:
        draft = db.get(ContentDraft, draft_resp.json()["id"])
        draft.generation_state = "failed"
        draft.retry_count = 2
        draft.last_error = "The read operation timed out"
        db.commit()

    response = client.get("/dashboard")

    assert response.status_code == 200
    assert "Validation failed draft exists for UI testing; not a production blocker." in response.text
    assert "validation_only" in response.text


def test_dashboard_review_queue_section_renders_all_categories(client):
    task_resp = client.post(
        "/tasks",
        json={"title": "Queue host task", "description": "desc"},
        headers=AUTH_HEADERS,
    )
    task_id = task_resp.json()["id"]
    failed_resp = client.post(
        "/drafts",
        json={"task_id": task_id, "title": "Production failed draft"},
        headers=AUTH_HEADERS,
    )
    validation_resp = client.post(
        "/drafts",
        json={"task_id": task_id, "title": "Failed state validation draft"},
        headers=AUTH_HEADERS,
    )
    ready_resp = client.post(
        "/drafts",
        json={"task_id": task_id, "title": "Ready review draft"},
        headers=AUTH_HEADERS,
    )
    approved_resp = client.post(
        "/drafts",
        json={"task_id": task_id, "title": "Approved copy draft"},
        headers=AUTH_HEADERS,
    )
    archived_resp = client.post(
        "/drafts",
        json={"task_id": task_id, "title": "Archived draft"},
        headers=AUTH_HEADERS,
    )

    session_local = client.app.state.testing_session_local
    with session_local() as db:
        failed = db.get(ContentDraft, failed_resp.json()["id"])
        validation = db.get(ContentDraft, validation_resp.json()["id"])
        ready = db.get(ContentDraft, ready_resp.json()["id"])
        approved = db.get(ContentDraft, approved_resp.json()["id"])
        archived = db.get(ContentDraft, archived_resp.json()["id"])
        failed.generation_state = "failed"
        failed.retry_count = 2
        failed.last_error = "The read operation timed out"
        validation.generation_state = "failed"
        validation.retry_count = 2
        validation.last_error = "The read operation timed out"
        ready.generation_state = "ready"
        ready.status = "draft"
        approved.generation_state = "ready"
        approved.status = "approved"
        archived.generation_state = "ready"
        archived.is_archived = True
        db.commit()

    response = client.get("/dashboard")

    assert response.status_code == 200
    assert "Review Queue" in response.text
    assert "Needs Attention" in response.text
    assert "Failed Production Drafts" in response.text
    assert "Validation / Test Records" in response.text
    assert "Ready for Review" in response.text
    assert "Approved for Human Copy" in response.text
    assert "Archived" in response.text
    assert "not a production blocker" in response.text
    assert "approved is human-use/copying only, not published" in response.text
    assert "Review last_error. Retry manually with a shorter prompt or split the request into smaller drafts." in response.text
    assert "No production action needed. This record is for UI validation only, not a production blocker." in response.text
    assert "Open the draft, review the content, run quality review if needed, then manually decide whether to revise or approve." in response.text
    assert "No action needed. Use show_archived=1 only when reviewing old records." in response.text


def test_dashboard_overview_shows_operator_summary_counts(client):
    active_task_resp = client.post(
        "/tasks",
        json={"title": "Active operator summary task", "description": "desc"},
        headers=AUTH_HEADERS,
    )
    archived_task_resp = client.post(
        "/tasks",
        json={"title": "Archive validation test task", "description": "desc"},
        headers=AUTH_HEADERS,
    )
    active_task_id = active_task_resp.json()["id"]
    archived_task_id = archived_task_resp.json()["id"]
    client.post(f"/dashboard/tasks/{archived_task_id}/archive", follow_redirects=False)

    ready_draft_resp = client.post(
        "/drafts",
        json={"task_id": active_task_id, "title": "Ready summary draft"},
        headers=AUTH_HEADERS,
    )
    failed_draft_resp = client.post(
        "/drafts",
        json={"task_id": active_task_id, "title": "Failed state validation draft"},
        headers=AUTH_HEADERS,
    )
    archived_draft_resp = client.post(
        "/drafts",
        json={"task_id": active_task_id, "title": "Archive validation test draft"},
        headers=AUTH_HEADERS,
    )

    session_local = client.app.state.testing_session_local
    with session_local() as db:
        ready = db.get(ContentDraft, ready_draft_resp.json()["id"])
        failed = db.get(ContentDraft, failed_draft_resp.json()["id"])
        archived = db.get(ContentDraft, archived_draft_resp.json()["id"])
        ready.generation_state = "ready"
        failed.generation_state = "failed"
        archived.is_archived = True
        db.commit()

    response = client.get("/")

    assert response.status_code == 200
    assert "操作摘要" in response.text
    assert "<strong>Active tasks:</strong> 1" in response.text
    assert "<strong>Archived tasks:</strong> 1" in response.text
    assert "<strong>Active drafts:</strong> 2" in response.text
    assert "<strong>Archived drafts:</strong> 1" in response.text
    assert "<strong>Failed drafts:</strong> 1" in response.text
    assert "<strong>Ready drafts:</strong> 1" in response.text


def test_dashboard_handoff_excludes_archived_task_from_continue_active_task(client):
    active_task_resp = client.post(
        "/tasks",
        json={"title": "Still active task", "description": "desc"},
        headers=AUTH_HEADERS,
    )
    archived_task_resp = client.post(
        "/tasks",
        json={"title": "v0.1.18 Walkthrough Test Task", "description": "desc"},
        headers=AUTH_HEADERS,
    )
    archived_task_id = archived_task_resp.json()["id"]
    client.post(f"/dashboard/tasks/{archived_task_id}/archive", follow_redirects=False)

    response = client.get("/dashboard")

    assert response.status_code == 200
    assert "Continue active task: Still active task" in response.text
    assert "Continue active task: v0.1.18 Walkthrough Test Task" not in response.text


def test_dashboard_task_list_renders_with_primary_agent_column(client):
    create_resp = client.post(
        "/tasks",
        json={"title": "Task for board", "description": "desc"},
        headers=AUTH_HEADERS,
    )
    assert create_resp.status_code == 200

    response = client.get("/dashboard/tasks")
    assert response.status_code == 200
    assert "主責角色" in response.text


def test_dashboard_tasks_hide_archived_by_default_and_can_show_archived(client):
    task_resp = client.post(
        "/tasks",
        json={"title": "Archive visibility task", "description": "desc"},
        headers=AUTH_HEADERS,
    )
    task_id = task_resp.json()["id"]

    client.post(f"/dashboard/tasks/{task_id}/archive", follow_redirects=False)

    hidden = client.get("/dashboard/tasks")
    shown = client.get("/dashboard/tasks?show_archived=1")

    assert hidden.status_code == 200
    assert shown.status_code == 200
    assert "Archive visibility task" not in hidden.text
    assert "Archive visibility task" in shown.text
    assert "show_archived=1 is active" in shown.text
    assert "已封存" in shown.text


def test_dashboard_tasks_empty_active_state_renders(client):
    response = client.get("/dashboard/tasks")

    assert response.status_code == 200
    assert "目前沒有 active tasks" in response.text
    assert "Archived items are hidden by default" in response.text


def test_dashboard_tasks_marks_validation_titles(client):
    client.post(
        "/tasks",
        json={"title": "Archive validation test task", "description": "desc"},
        headers=AUTH_HEADERS,
    )

    response = client.get("/dashboard/tasks")

    assert response.status_code == 200
    assert "validation/test" in response.text


def test_dashboard_archive_task_action_works(client):
    task_resp = client.post(
        "/tasks",
        json={"title": "Archive action task", "description": "desc"},
        headers=AUTH_HEADERS,
    )
    task_id = task_resp.json()["id"]

    response = client.post(f"/dashboard/tasks/{task_id}/archive", follow_redirects=False)
    task_detail = client.get(f"/tasks/{task_id}", headers=AUTH_HEADERS).json()

    assert response.status_code == 303
    assert response.headers["location"] == "/dashboard/tasks?show_archived=1"
    assert task_detail["is_archived"] is True


def test_dashboard_task_detail_renders_v13_fields(client):
    create_resp = client.post(
        "/tasks",
        json={"title": "v13 detail", "description": "desc"},
        headers=AUTH_HEADERS,
    )
    task_id = create_resp.json()["id"]
    task_payload = {
        "contract_version": "ceo_decision.v1.3",
        "task_type": "content",
        "priority": "high",
        "risk_level": "low",
        "suggested_agent_role": "content_agent",
        "primary_agent_role": "content_agent",
        "supporting_agent_roles": ["sales_agent"],
        "task_summary": "summary",
        "ceo_decision": "decision",
        "reasoning_summary": "reason",
        "recommended_steps": ["s1"],
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
        "success_criteria": ["ok"],
        "estimated_complexity": "medium",
        "simulation_only": True,
        "memory_to_save": [],
    }
    update_resp = client.post(
        f"/tasks/{task_id}/review",
        json=task_payload,
        headers=AUTH_HEADERS,
    )
    assert update_resp.status_code == 200

    response = client.get(f"/dashboard/tasks/{task_id}")
    assert response.status_code == 200
    assert "主責角色：" in response.text
    assert "支援角色：" in response.text
    assert "決策評分 Rubric" in response.text
    assert "批准檢查清單 Approval Checklist" in response.text
    assert "objective_clarity" in response.text
    assert "requires_human_review" in response.text


def test_dashboard_task_detail_legacy_safe_does_not_crash(client):
    create_resp = client.post(
        "/tasks",
        json={"title": "legacy detail", "description": "desc"},
        headers=AUTH_HEADERS,
    )
    task_id = create_resp.json()["id"]
    legacy_payload = {
        "contract_version": "ceo_decision.v1.2",
        "task_type": "sales",
        "priority": "medium",
        "risk_level": "low",
        "suggested_agent_role": "sales_agent",
        "task_summary": "legacy",
        "ceo_decision": "legacy decision",
        "reasoning_summary": "legacy reason",
        "recommended_steps": ["step"],
        "requires_human_approval": True,
        "recommended_next_status": "planned",
        "blocked_by": [],
        "success_criteria": ["ok"],
        "estimated_complexity": "simple",
        "simulation_only": True,
        "memory_to_save": [],
    }
    update_resp = client.post(
        f"/tasks/{task_id}/review",
        json=legacy_payload,
        headers=AUTH_HEADERS,
    )
    assert update_resp.status_code == 200

    response = client.get(f"/dashboard/tasks/{task_id}")
    assert response.status_code == 200
    assert "主責角色：" in response.text
    assert "支援角色：" in response.text
    assert "[]" in response.text


def test_dashboard_task_detail_pending_without_ceo_decision_renders(client):
    create_resp = client.post(
        "/tasks",
        json={"title": "pending detail", "description": "no decision yet"},
        headers=AUTH_HEADERS,
    )
    task_id = create_resp.json()["id"]

    response = client.get(f"/dashboard/tasks/{task_id}")
    assert response.status_code == 200
    assert "目前還沒有 CEO 決策。" in response.text
    assert "主責角色：" in response.text
    assert "支援角色：" in response.text


def test_dashboard_task_detail_missing_task_returns_404(client):
    response = client.get("/dashboard/tasks/999999")
    assert response.status_code == 404
    assert "was not found" in response.text


def test_dashboard_task_detail_non_object_decision_json_does_not_crash(client):
    create_resp = client.post(
        "/tasks",
        json={"title": "array decision", "description": "decision json is array"},
        headers=AUTH_HEADERS,
    )
    task_id = create_resp.json()["id"]

    session_local = client.app.state.testing_session_local
    with session_local() as db:
        task = db.get(Task, task_id)
        task.ceo_decision_json = "[]"
        db.commit()

    response = client.get(f"/dashboard/tasks/{task_id}")
    assert response.status_code == 200
    assert "目前還沒有 CEO 決策。" in response.text


def test_no_external_platform_routes_added(client):
    for path in ["/facebook", "/instagram", "/telegram", "/line", "/x", "/n8n"]:
        response = client.get(path)
        assert response.status_code == 404


def test_only_ceo_agent_enabled_in_dashboard_state(client):
    response = client.get("/agents", headers=AUTH_HEADERS)
    assert response.status_code == 200
    agents = response.json()

    enabled = [agent["id"] for agent in agents if agent["is_enabled"]]
    assert enabled == ["ceo_agent"]


def test_dashboard_drafts_page_renders(client):
    response = client.get("/dashboard/drafts")
    assert response.status_code == 200
    assert "內容草稿看板" in response.text


def test_dashboard_drafts_hide_archived_by_default_and_can_show_archived(client):
    task_resp = client.post(
        "/tasks",
        json={"title": "Archive draft visibility task", "description": "desc"},
        headers=AUTH_HEADERS,
    )
    task_id = task_resp.json()["id"]
    draft_resp = client.post(
        "/drafts",
        json={"task_id": task_id, "title": "Archive draft visibility"},
        headers=AUTH_HEADERS,
    )
    draft_id = draft_resp.json()["id"]

    client.post(f"/dashboard/drafts/{draft_id}/archive", follow_redirects=False)

    hidden = client.get("/dashboard/drafts")
    shown = client.get("/dashboard/drafts?show_archived=1")

    assert hidden.status_code == 200
    assert shown.status_code == 200
    assert "Archive draft visibility" not in hidden.text
    assert "Archive draft visibility" in shown.text
    assert "show_archived=1 is active" in shown.text
    assert "已封存" in shown.text


def test_dashboard_drafts_empty_active_state_renders(client):
    response = client.get("/dashboard/drafts")

    assert response.status_code == 200
    assert "目前沒有 active drafts" in response.text
    assert "目前沒有 failed drafts" in response.text


def test_dashboard_drafts_marks_failed_ready_and_retry_count(client):
    task_resp = client.post(
        "/tasks",
        json={"title": "Draft status visibility task", "description": "desc"},
        headers=AUTH_HEADERS,
    )
    task_id = task_resp.json()["id"]
    ready_resp = client.post(
        "/drafts",
        json={"task_id": task_id, "title": "Ready visible draft"},
        headers=AUTH_HEADERS,
    )
    failed_resp = client.post(
        "/drafts",
        json={"task_id": task_id, "title": "Failed state validation draft"},
        headers=AUTH_HEADERS,
    )

    session_local = client.app.state.testing_session_local
    with session_local() as db:
        ready = db.get(ContentDraft, ready_resp.json()["id"])
        failed = db.get(ContentDraft, failed_resp.json()["id"])
        ready.generation_state = "ready"
        failed.generation_state = "failed"
        failed.retry_count = 2
        failed.last_error = "The read operation timed out"
        db.commit()

    response = client.get("/dashboard/drafts")

    assert response.status_code == 200
    assert "Ready visible draft" in response.text
    assert "Failed state validation draft" in response.text
    assert "<span class=\"pill ok\">ready</span>" in response.text
    assert "<span class=\"pill bad\">failed</span>" in response.text
    assert ">2</td>" in response.text
    assert "validation/test" in response.text


def test_dashboard_draft_detail_renders(client):
    task_resp = client.post(
        "/tasks",
        json={"title": "Draft detail task", "description": "desc"},
        headers=AUTH_HEADERS,
    )
    task_id = task_resp.json()["id"]
    draft_resp = client.post(
        "/drafts",
        json={"task_id": task_id, "title": "Draft detail"},
        headers=AUTH_HEADERS,
    )
    draft_id = draft_resp.json()["id"]

    response = client.get(f"/dashboard/drafts/{draft_id}")
    assert response.status_code == 200
    assert "Approved means approved for human use/copying only. This system does not publish externally." in response.text
    assert "目前尚無品質審查結果。" in response.text
    assert "生成狀態：" in response.text
    assert "重試次數：" in response.text


def test_dashboard_draft_detail_ready_hint_renders(client):
    task_resp = client.post(
        "/tasks",
        json={"title": "Ready detail task", "description": "desc"},
        headers=AUTH_HEADERS,
    )
    task_id = task_resp.json()["id"]
    draft_resp = client.post(
        "/drafts",
        json={"task_id": task_id, "title": "Ready detail draft"},
        headers=AUTH_HEADERS,
    )
    draft_id = draft_resp.json()["id"]

    session_local = client.app.state.testing_session_local
    with session_local() as db:
        draft = db.get(ContentDraft, draft_id)
        draft.generation_state = "ready"
        draft.draft_text = "Ready text"
        db.commit()

    response = client.get(f"/dashboard/drafts/{draft_id}")

    assert response.status_code == 200
    assert "generation: ready" in response.text
    assert "Ready drafts are for human review/copying only, not published." in response.text
    assert "Approved means human-use/copying only. It does not mean published." in response.text


def test_dashboard_draft_detail_failed_state_shows_error_retry_and_split(client):
    task_resp = client.post(
        "/tasks",
        json={"title": "Failed detail task", "description": "desc"},
        headers=AUTH_HEADERS,
    )
    task_id = task_resp.json()["id"]
    draft_resp = client.post(
        "/drafts",
        json={"task_id": task_id, "title": "Failed state validation draft"},
        headers=AUTH_HEADERS,
    )
    draft_id = draft_resp.json()["id"]

    session_local = client.app.state.testing_session_local
    with session_local() as db:
        draft = db.get(ContentDraft, draft_id)
        draft.generation_state = "failed"
        draft.retry_count = 2
        draft.last_error = "The read operation timed out"
        db.commit()

    response = client.get(f"/dashboard/drafts/{draft_id}")

    assert response.status_code == 200
    assert "generation: failed" in response.text
    assert "最後錯誤：</strong> The read operation timed out" in response.text
    assert "重試次數：</strong> 2" in response.text
    assert "Failed drafts should be retried or split into smaller drafts." in response.text
    assert "Recommended split: separate into 1) outline 2) section draft 3) CTA draft." in response.text
    assert "validation/test" in response.text


def test_dashboard_archive_draft_action_works(client):
    task_resp = client.post(
        "/tasks",
        json={"title": "Archive draft action task", "description": "desc"},
        headers=AUTH_HEADERS,
    )
    task_id = task_resp.json()["id"]
    draft_resp = client.post(
        "/drafts",
        json={"task_id": task_id, "title": "Archive this draft"},
        headers=AUTH_HEADERS,
    )
    draft_id = draft_resp.json()["id"]

    response = client.post(f"/dashboard/drafts/{draft_id}/archive", follow_redirects=False)
    detail = client.get(f"/drafts/{draft_id}", headers=AUTH_HEADERS).json()

    assert response.status_code == 303
    assert response.headers["location"] == "/dashboard/drafts?show_archived=1"
    assert detail["is_archived"] is True


def test_task_detail_shows_related_drafts(client):
    task_resp = client.post(
        "/tasks",
        json={"title": "Related draft task", "description": "desc"},
        headers=AUTH_HEADERS,
    )
    task_id = task_resp.json()["id"]
    draft_resp = client.post(
        "/drafts",
        json={"task_id": task_id, "title": "Related draft"},
        headers=AUTH_HEADERS,
    )
    draft_id = draft_resp.json()["id"]

    response = client.get(f"/dashboard/tasks/{task_id}")
    assert response.status_code == 200
    assert f"/dashboard/drafts/{draft_id}" in response.text


def test_dashboard_create_draft_from_task_action_works(client):
    task_resp = client.post(
        "/tasks",
        json={"title": "Create draft action task", "description": "desc"},
        headers=AUTH_HEADERS,
    )
    task_id = task_resp.json()["id"]

    response = client.post(
        f"/dashboard/tasks/{task_id}/drafts",
        data={"title": "Dashboard created draft", "channel_hint": "facebook_post", "target_audience": "35-55"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    location = response.headers["location"]
    assert location.startswith("/dashboard/drafts/")

    follow = client.get(location)
    assert follow.status_code == 200
    assert "Dashboard created draft" in follow.text


def test_dashboard_task_drafts_get_not_used_as_page(client):
    task_resp = client.post(
        "/tasks",
        json={"title": "Task draft get method task", "description": "desc"},
        headers=AUTH_HEADERS,
    )
    task_id = task_resp.json()["id"]
    response = client.get(f"/dashboard/tasks/{task_id}/drafts")
    assert response.status_code == 405


def test_dashboard_generate_action_works_with_mocked_service(monkeypatch, client):
    from app.routers import dashboard as dashboard_router

    task_resp = client.post(
        "/tasks",
        json={"title": "Generate action task", "description": "desc"},
        headers=AUTH_HEADERS,
    )
    task_id = task_resp.json()["id"]
    draft_resp = client.post(
        "/drafts",
        json={"task_id": task_id, "title": "Generate me"},
        headers=AUTH_HEADERS,
    )
    draft_id = draft_resp.json()["id"]

    original = dashboard_router.ContentDraftService.generate_draft

    def fake_generate(self, draft_id: int, llm_provider=None, actor="dashboard"):
        draft = self.require_draft(draft_id)
        draft.draft_text = "Mock dashboard generated text"
        self.db.add(draft)
        self.db.commit()
        self.db.refresh(draft)
        return draft

    monkeypatch.setattr(dashboard_router.ContentDraftService, "generate_draft", fake_generate)
    response = client.post(f"/dashboard/drafts/{draft_id}/generate", follow_redirects=True)
    monkeypatch.setattr(dashboard_router.ContentDraftService, "generate_draft", original)

    assert response.status_code == 200
    assert "Mock dashboard generated text" in response.text


def test_dashboard_generate_action_failure_shows_visible_error(monkeypatch, client):
    from app.routers import dashboard as dashboard_router

    task_resp = client.post(
        "/tasks",
        json={"title": "Generate failure task", "description": "desc"},
        headers=AUTH_HEADERS,
    )
    task_id = task_resp.json()["id"]
    draft_resp = client.post(
        "/drafts",
        json={"task_id": task_id, "title": "Generate failure draft"},
        headers=AUTH_HEADERS,
    )
    draft_id = draft_resp.json()["id"]

    original = dashboard_router.ContentDraftService.generate_draft

    def fake_generate(self, draft_id: int, llm_provider=None, actor="dashboard"):
        raise ValueError("The read operation timed out")

    monkeypatch.setattr(dashboard_router.ContentDraftService, "generate_draft", fake_generate)
    response = client.post(f"/dashboard/drafts/{draft_id}/generate", follow_redirects=True)
    monkeypatch.setattr(dashboard_router.ContentDraftService, "generate_draft", original)

    draft_detail = client.get(f"/drafts/{draft_id}", headers=AUTH_HEADERS).json()

    assert response.status_code == 200
    assert "Draft generation failed. Please retry. Reason: The read operation timed out" in response.text
    assert "目前尚未生成草稿內容。" in response.text
    assert draft_detail["draft_text"] is None
    assert draft_detail["status"] == "draft"
    assert "published_at" not in draft_detail


def test_dashboard_generate_action_failure_shows_generation_state_and_retry_recommendation(monkeypatch, client):
    from app.routers import dashboard as dashboard_router

    task_resp = client.post(
        "/tasks",
        json={"title": "Generate retry recommendation task", "description": "desc"},
        headers=AUTH_HEADERS,
    )
    task_id = task_resp.json()["id"]
    draft_resp = client.post(
        "/drafts",
        json={"task_id": task_id, "title": "Retry recommendation draft"},
        headers=AUTH_HEADERS,
    )
    draft_id = draft_resp.json()["id"]

    original = dashboard_router.ContentDraftService.generate_draft

    def fake_generate(self, draft_id: int, llm_provider=None, actor="dashboard"):
        self.mark_generation_failed(draft_id, "The read operation timed out")
        raise ValueError("The read operation timed out")

    monkeypatch.setattr(dashboard_router.ContentDraftService, "generate_draft", fake_generate)
    response = client.post(f"/dashboard/drafts/{draft_id}/generate", follow_redirects=True)
    monkeypatch.setattr(dashboard_router.ContentDraftService, "generate_draft", original)
    detail = client.get(f"/drafts/{draft_id}", headers=AUTH_HEADERS).json()

    assert response.status_code == 200
    assert "最後錯誤：</strong> The read operation timed out" in response.text
    assert "重試建議：</strong>" in response.text
    assert "split this request into a shorter draft or smaller section" in response.text
    assert detail["generation_state"] == "failed"
    assert detail["retry_count"] >= 1
    assert detail["status"] == "draft"


def test_dashboard_generate_action_failure_after_two_retries_shows_stronger_split_recommendation(monkeypatch, client):
    from app.routers import dashboard as dashboard_router

    task_resp = client.post(
        "/tasks",
        json={"title": "Generate strong split task", "description": "desc"},
        headers=AUTH_HEADERS,
    )
    task_id = task_resp.json()["id"]
    draft_resp = client.post(
        "/drafts",
        json={"task_id": task_id, "title": "Strong split draft"},
        headers=AUTH_HEADERS,
    )
    draft_id = draft_resp.json()["id"]

    original = dashboard_router.ContentDraftService.generate_draft

    def fake_generate(self, draft_id: int, llm_provider=None, actor="dashboard"):
        self.mark_generation_failed(draft_id, "The read operation timed out")
        raise ValueError("The read operation timed out")

    monkeypatch.setattr(dashboard_router.ContentDraftService, "generate_draft", fake_generate)
    client.post(f"/dashboard/drafts/{draft_id}/generate", follow_redirects=True)
    response = client.post(f"/dashboard/drafts/{draft_id}/generate", follow_redirects=True)
    monkeypatch.setattr(dashboard_router.ContentDraftService, "generate_draft", original)
    detail = client.get(f"/drafts/{draft_id}", headers=AUTH_HEADERS).json()

    assert response.status_code == 200
    assert "最後錯誤：</strong> The read operation timed out" in response.text
    assert "Recommended split: separate into 1) outline 2) section draft 3) CTA draft." in response.text
    assert detail["retry_count"] >= 2


def test_dashboard_generate_action_empty_content_sets_failed_state_and_shows_error(monkeypatch, client):
    from app.routers import dashboard as dashboard_router
    from app.services.llm_provider import LLMResponse

    task_resp = client.post(
        "/tasks",
        json={"title": "Generate empty content task", "description": "desc"},
        headers=AUTH_HEADERS,
    )
    task_id = task_resp.json()["id"]
    draft_resp = client.post(
        "/drafts",
        json={"task_id": task_id, "title": "Empty content draft"},
        headers=AUTH_HEADERS,
    )
    draft_id = draft_resp.json()["id"]

    original_chat = dashboard_router.DeepSeekLLMProvider.chat

    def fake_chat(self, messages, temperature=0.3, task_id=None, json_mode=False):
        return LLMResponse(
            provider="mock",
            model="mock-model",
            raw_text="   ",
            parsed_json=None,
            latency_ms=1,
            success=True,
            error=None,
        )

    monkeypatch.setattr(dashboard_router.DeepSeekLLMProvider, "chat", fake_chat)
    response = client.post(f"/dashboard/drafts/{draft_id}/generate", follow_redirects=True)
    monkeypatch.setattr(dashboard_router.DeepSeekLLMProvider, "chat", original_chat)
    detail = client.get(f"/drafts/{draft_id}", headers=AUTH_HEADERS).json()
    drafts_page = client.get("/dashboard/drafts")

    assert response.status_code == 200
    assert "Draft generation failed. Please retry. Reason: Draft generation returned empty content." in response.text
    assert "最後錯誤：</strong> Draft generation returned empty content." in response.text
    assert detail["generation_state"] == "failed"
    assert detail["retry_count"] >= 1
    assert detail["draft_text"] is None
    assert detail["status"] == "draft"
    assert "Empty content draft" in drafts_page.text
    assert "<span class=\"pill bad\">failed</span>" in drafts_page.text


def test_dashboard_revise_action_works_with_mocked_service(monkeypatch, client):
    from app.routers import dashboard as dashboard_router

    task_resp = client.post(
        "/tasks",
        json={"title": "Revise action task", "description": "desc"},
        headers=AUTH_HEADERS,
    )
    task_id = task_resp.json()["id"]
    draft_resp = client.post(
        "/drafts",
        json={"task_id": task_id, "title": "Revise me"},
        headers=AUTH_HEADERS,
    )
    draft_id = draft_resp.json()["id"]

    original = dashboard_router.ContentDraftService.revise_draft

    def fake_revise(self, draft_id: int, revision_instruction: str, llm_provider=None, actor="dashboard"):
        draft = self.require_draft(draft_id)
        draft.draft_text = f"Revised: {revision_instruction}"
        draft.version += 1
        draft.status = "draft"
        self.db.add(draft)
        self.db.commit()
        self.db.refresh(draft)
        return draft

    monkeypatch.setattr(dashboard_router.ContentDraftService, "revise_draft", fake_revise)
    response = client.post(
        f"/dashboard/drafts/{draft_id}/revise",
        data={"revision_instruction": "shorter"},
        follow_redirects=True,
    )
    monkeypatch.setattr(dashboard_router.ContentDraftService, "revise_draft", original)

    assert response.status_code == 200
    assert "Revised: shorter" in response.text


def test_dashboard_update_status_action_works(client):
    task_resp = client.post(
        "/tasks",
        json={"title": "Status action task", "description": "desc"},
        headers=AUTH_HEADERS,
    )
    task_id = task_resp.json()["id"]
    draft_resp = client.post(
        "/drafts",
        json={"task_id": task_id, "title": "Status me"},
        headers=AUTH_HEADERS,
    )
    draft_id = draft_resp.json()["id"]

    response = client.post(
        f"/dashboard/drafts/{draft_id}/status",
        data={"status": "approved", "review_notes": "Approved manually"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "Approved means approved for human use/copying only. This system does not publish externally." in response.text


def test_dashboard_draft_detail_renders_latest_quality_review(monkeypatch, client):
    from app.routers import dashboard as dashboard_router
    from app.models.content_draft_review import ContentDraftReview

    task_resp = client.post(
        "/tasks",
        json={"title": "Quality review detail task", "description": "desc"},
        headers=AUTH_HEADERS,
    )
    task_id = task_resp.json()["id"]
    draft_resp = client.post(
        "/drafts",
        json={"task_id": task_id, "title": "Quality review draft"},
        headers=AUTH_HEADERS,
    )
    draft_id = draft_resp.json()["id"]

    original = dashboard_router.ContentQualityReviewService.review_draft

    def fake_review(self, draft_id: int, llm_provider=None, actor="dashboard"):
        record = ContentDraftReview(
            draft_id=draft_id,
            status="needs_revision",
            overall_score=71,
            tone_score=73,
            medical_safety_score=84,
            cta_safety_score=65,
            discipline_score=79,
            risk_flags_json='[{"type":"hard_sell","severity":"medium"}]',
            suggested_rewrites_json='[{"original":"快買","rewrite":"有需要可私訊"}]',
            review_summary="CTA 太強，建議轉柔和。",
            raw_review_json='{"contract_version":"content_review.v1"}',
            reviewed_by=actor,
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    monkeypatch.setattr(dashboard_router.ContentQualityReviewService, "review_draft", fake_review)
    action_resp = client.post(f"/dashboard/drafts/{draft_id}/review-quality", follow_redirects=True)
    monkeypatch.setattr(dashboard_router.ContentQualityReviewService, "review_draft", original)

    assert action_resp.status_code == 200
    assert "最新品質審查結果" in action_resp.text
    assert "overall_score" in action_resp.text
    assert "risk_flags" in action_resp.text
    assert "suggested_rewrites" in action_resp.text
    assert "needs_revision" in action_resp.text


def test_dashboard_quality_review_action_redirects_back_to_draft_detail(monkeypatch, client):
    from app.routers import dashboard as dashboard_router
    from app.models.content_draft_review import ContentDraftReview

    task_resp = client.post(
        "/tasks",
        json={"title": "Quality review redirect task", "description": "desc"},
        headers=AUTH_HEADERS,
    )
    task_id = task_resp.json()["id"]
    draft_resp = client.post(
        "/drafts",
        json={"task_id": task_id, "title": "Redirect review draft"},
        headers=AUTH_HEADERS,
    )
    draft_id = draft_resp.json()["id"]

    original = dashboard_router.ContentQualityReviewService.review_draft

    def fake_review(self, draft_id: int, llm_provider=None, actor="dashboard"):
        record = ContentDraftReview(
            draft_id=draft_id,
            status="needs_revision",
            overall_score=71,
            tone_score=73,
            medical_safety_score=84,
            cta_safety_score=65,
            discipline_score=79,
            risk_flags_json="[]",
            suggested_rewrites_json="[]",
            review_summary="CTA 太強，建議轉柔和。",
            raw_review_json='{"contract_version":"content_review.v1"}',
            reviewed_by=actor,
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    monkeypatch.setattr(dashboard_router.ContentQualityReviewService, "review_draft", fake_review)
    response = client.post(
        f"/dashboard/drafts/{draft_id}/review-quality",
        follow_redirects=False,
    )
    monkeypatch.setattr(dashboard_router.ContentQualityReviewService, "review_draft", original)

    assert response.status_code == 303
    assert response.headers["location"] == f"/dashboard/drafts/{draft_id}"


def test_dashboard_quality_review_get_is_not_a_normal_page(client):
    task_resp = client.post(
        "/tasks",
        json={"title": "Quality review GET guard", "description": "desc"},
        headers=AUTH_HEADERS,
    )
    task_id = task_resp.json()["id"]
    draft_resp = client.post(
        "/drafts",
        json={"task_id": task_id, "title": "GET guard draft"},
        headers=AUTH_HEADERS,
    )
    draft_id = draft_resp.json()["id"]

    response = client.get(f"/dashboard/drafts/{draft_id}/review-quality")
    assert response.status_code == 405


def test_dashboard_quality_review_action_does_not_change_draft_status(client):
    task_resp = client.post(
        "/tasks",
        json={"title": "Quality review status guard", "description": "desc"},
        headers=AUTH_HEADERS,
    )
    task_id = task_resp.json()["id"]
    draft_resp = client.post(
        "/drafts",
        json={"task_id": task_id, "title": "Status guard draft"},
        headers=AUTH_HEADERS,
    )
    draft_id = draft_resp.json()["id"]

    client.post(f"/dashboard/drafts/{draft_id}/generate", follow_redirects=True)
    before = client.get(f"/dashboard/drafts/{draft_id}").text
    response = client.post(f"/dashboard/drafts/{draft_id}/review-quality", follow_redirects=True)
    after_detail = client.get(f"/drafts/{draft_id}", headers=AUTH_HEADERS).json()

    assert response.status_code == 200
    assert "Quality review is advisory only." in response.text
    assert "草稿 / draft" in before
    assert after_detail["status"] == "draft"
    assert "published_at" not in after_detail
