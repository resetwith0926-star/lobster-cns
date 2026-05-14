from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.main as main_module
from app.database import Base, get_db
from app.main import app
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
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)


def _create_task(client: TestClient, title: str = "Draft source task") -> int:
    response = client.post(
        "/tasks",
        json={"title": title, "description": "desc"},
        headers=AUTH_HEADERS,
    )
    assert response.status_code == 200
    return response.json()["id"]


def _create_draft(client: TestClient, task_id: int, title: str = "Draft title") -> int:
    response = client.post(
        "/drafts",
        json={"task_id": task_id, "title": title},
        headers=AUTH_HEADERS,
    )
    assert response.status_code == 200
    return response.json()["id"]


def test_post_drafts_requires_admin_secret(client):
    task_id = _create_task(client)
    response = client.post("/drafts", json={"task_id": task_id, "title": "No auth"})
    assert response.status_code == 401


def test_post_drafts_creates_draft_without_generating_text(client):
    task_id = _create_task(client)
    response = client.post(
        "/drafts",
        json={"task_id": task_id, "title": "New draft"},
        headers=AUTH_HEADERS,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["task_id"] == task_id
    assert payload["draft_text"] is None
    assert payload["status"] == "draft"


def test_get_drafts_lists_and_filters_by_status(client):
    task_id = _create_task(client)
    draft_a = _create_draft(client, task_id, "A")
    draft_b = _create_draft(client, task_id, "B")
    assert draft_a != draft_b

    response = client.post(
        f"/drafts/{draft_b}/status",
        json={"status": "approved", "review_notes": "ok"},
        headers=AUTH_HEADERS,
    )
    assert response.status_code == 200

    all_resp = client.get("/drafts", headers=AUTH_HEADERS)
    assert all_resp.status_code == 200
    assert len(all_resp.json()) >= 2

    filtered = client.get("/drafts?status=draft", headers=AUTH_HEADERS)
    assert filtered.status_code == 200
    assert all(item["status"] == "draft" for item in filtered.json())


def test_get_draft_detail_returns_record(client):
    task_id = _create_task(client)
    draft_id = _create_draft(client, task_id, "Detail draft")
    response = client.get(f"/drafts/{draft_id}", headers=AUTH_HEADERS)
    assert response.status_code == 200
    assert response.json()["id"] == draft_id


def test_generate_endpoint_requires_admin_secret(client):
    task_id = _create_task(client)
    draft_id = _create_draft(client, task_id, "Generate auth")
    response = client.post(f"/drafts/{draft_id}/generate")
    assert response.status_code == 401


def test_generate_endpoint_writes_text_keeps_draft_status(monkeypatch, client):
    from app.routers import drafts as drafts_router

    task_id = _create_task(client)
    draft_id = _create_draft(client, task_id, "Generate draft")

    original = drafts_router.ContentDraftService.generate_draft

    def fake_generate(self, draft_id: int, llm_provider=None, actor="ceo_agent"):
        draft = self.require_draft(draft_id)
        draft.draft_text = "Mock generated draft text"
        draft.status = "draft"
        self.db.add(draft)
        self.db.commit()
        self.db.refresh(draft)
        return draft

    monkeypatch.setattr(drafts_router.ContentDraftService, "generate_draft", fake_generate)
    response = client.post(f"/drafts/{draft_id}/generate", headers=AUTH_HEADERS)
    monkeypatch.setattr(drafts_router.ContentDraftService, "generate_draft", original)

    assert response.status_code == 200
    payload = response.json()
    assert payload["draft_text"] == "Mock generated draft text"
    assert payload["status"] == "draft"
    assert payload["status"] != "approved"


def test_revise_endpoint_updates_text_and_increments_version(monkeypatch, client):
    from app.routers import drafts as drafts_router

    task_id = _create_task(client)
    draft_id = _create_draft(client, task_id, "Revise draft")

    original = drafts_router.ContentDraftService.revise_draft

    def fake_revise(self, draft_id: int, revision_instruction: str, llm_provider=None, actor="admin"):
        draft = self.require_draft(draft_id)
        draft.draft_text = f"Revised: {revision_instruction}"
        draft.version = draft.version + 1
        draft.status = "draft"
        self.db.add(draft)
        self.db.commit()
        self.db.refresh(draft)
        return draft

    monkeypatch.setattr(drafts_router.ContentDraftService, "revise_draft", fake_revise)
    response = client.post(
        f"/drafts/{draft_id}/revise",
        json={"revision_instruction": "make it warmer and concise"},
        headers=AUTH_HEADERS,
    )
    monkeypatch.setattr(drafts_router.ContentDraftService, "revise_draft", original)

    assert response.status_code == 200
    payload = response.json()
    assert payload["draft_text"].startswith("Revised:")
    assert payload["version"] == 2
    assert payload["status"] == "draft"


def test_status_endpoint_sets_approved_without_external_action(client):
    task_id = _create_task(client)
    draft_id = _create_draft(client, task_id, "Approval draft")
    response = client.post(
        f"/drafts/{draft_id}/status",
        json={"status": "approved", "review_notes": "Approved for manual use only."},
        headers=AUTH_HEADERS,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "approved"
    assert "published_at" not in payload


def test_status_endpoint_rejects_invalid_status(client):
    task_id = _create_task(client)
    draft_id = _create_draft(client, task_id, "Invalid status draft")
    response = client.post(
        f"/drafts/{draft_id}/status",
        json={"status": "published"},
        headers=AUTH_HEADERS,
    )
    assert response.status_code == 422


def test_missing_draft_returns_404(client):
    response = client.get("/drafts/999999", headers=AUTH_HEADERS)
    assert response.status_code == 404


def test_no_external_integration_routes_added(client):
    for path in ["/facebook", "/instagram", "/telegram", "/line", "/x", "/n8n"]:
        response = client.get(path)
        assert response.status_code == 404


def test_only_ceo_agent_enabled(client):
    response = client.get("/agents", headers=AUTH_HEADERS)
    assert response.status_code == 200
    agents = response.json()
    enabled = [agent["id"] for agent in agents if agent["is_enabled"]]
    assert enabled == ["ceo_agent"]
