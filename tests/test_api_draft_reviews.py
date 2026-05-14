from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.main as main_module
from app.database import Base, get_db
from app.main import app
from app.models.content_draft_review import ContentDraftReview
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


def _create_task(client: TestClient, title: str = "Review source task") -> int:
    response = client.post(
        "/tasks",
        json={"title": title, "description": "desc"},
        headers=AUTH_HEADERS,
    )
    assert response.status_code == 200
    return response.json()["id"]


def _create_draft(client: TestClient, task_id: int, title: str = "Review draft") -> int:
    response = client.post(
        "/drafts",
        json={"task_id": task_id, "title": title},
        headers=AUTH_HEADERS,
    )
    assert response.status_code == 200
    return response.json()["id"]


def test_review_quality_requires_admin_secret(client):
    task_id = _create_task(client)
    draft_id = _create_draft(client, task_id)
    response = client.post(f"/drafts/{draft_id}/review-quality")
    assert response.status_code == 401


def test_review_quality_creates_review_with_mocked_service(monkeypatch, client):
    from app.routers import draft_reviews as router_module

    task_id = _create_task(client)
    draft_id = _create_draft(client, task_id)

    client.post(
        f"/drafts/{draft_id}/generate",
        headers=AUTH_HEADERS,
    )

    original = router_module.ContentQualityReviewService.review_draft

    def fake_review(self, draft_id: int, llm_provider=None, actor="quality_reviewer"):
        record = ContentDraftReview(
            draft_id=draft_id,
            status="needs_revision",
            overall_score=70,
            tone_score=75,
            medical_safety_score=80,
            cta_safety_score=68,
            discipline_score=72,
            risk_flags_json="[]",
            suggested_rewrites_json="[]",
            review_summary="Please soften CTA language.",
            raw_review_json='{"contract_version":"content_review.v1"}',
            reviewed_by=actor,
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    monkeypatch.setattr(router_module.ContentQualityReviewService, "review_draft", fake_review)
    response = client.post(f"/drafts/{draft_id}/review-quality", headers=AUTH_HEADERS)
    monkeypatch.setattr(router_module.ContentQualityReviewService, "review_draft", original)

    assert response.status_code == 200
    payload = response.json()
    assert payload["draft_id"] == draft_id
    assert payload["status"] == "needs_revision"


def test_review_quality_does_not_change_draft_status_or_publish(client):
    from app.routers import draft_reviews as router_module

    task_id = _create_task(client)
    draft_id = _create_draft(client, task_id)
    original = router_module.ContentQualityReviewService.review_draft

    def fake_review(self, draft_id: int, llm_provider=None, actor="quality_reviewer"):
        record = ContentDraftReview(
            draft_id=draft_id,
            status="needs_revision",
            overall_score=70,
            tone_score=75,
            medical_safety_score=80,
            cta_safety_score=68,
            discipline_score=72,
            risk_flags_json="[]",
            suggested_rewrites_json="[]",
            review_summary="Please soften CTA language.",
            raw_review_json='{"contract_version":"content_review.v1"}',
            reviewed_by=actor,
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(router_module.ContentQualityReviewService, "review_draft", fake_review)
    before = client.get(f"/drafts/{draft_id}", headers=AUTH_HEADERS).json()
    response = client.post(f"/drafts/{draft_id}/review-quality", headers=AUTH_HEADERS)
    monkeypatch.setattr(router_module.ContentQualityReviewService, "review_draft", original)
    monkeypatch.undo()
    assert response.status_code == 200
    after = client.get(f"/drafts/{draft_id}", headers=AUTH_HEADERS).json()
    assert before["status"] == after["status"] == "draft"
    assert "published_at" not in after
    assert after["status"] != "approved"


def test_list_reviews_returns_reviews_for_draft(client):
    from app.routers import draft_reviews as router_module

    task_id = _create_task(client)
    draft_id = _create_draft(client, task_id)
    original = router_module.ContentQualityReviewService.review_draft

    def fake_review(self, draft_id: int, llm_provider=None, actor="quality_reviewer"):
        record = ContentDraftReview(
            draft_id=draft_id,
            status="needs_revision",
            overall_score=70,
            tone_score=75,
            medical_safety_score=80,
            cta_safety_score=68,
            discipline_score=72,
            risk_flags_json="[]",
            suggested_rewrites_json="[]",
            review_summary="Please soften CTA language.",
            raw_review_json='{"contract_version":"content_review.v1"}',
            reviewed_by=actor,
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(router_module.ContentQualityReviewService, "review_draft", fake_review)
    client.post(f"/drafts/{draft_id}/review-quality", headers=AUTH_HEADERS)
    monkeypatch.setattr(router_module.ContentQualityReviewService, "review_draft", original)
    monkeypatch.undo()
    response = client.get(f"/drafts/{draft_id}/reviews", headers=AUTH_HEADERS)
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) >= 1
    assert all(item["draft_id"] == draft_id for item in payload)


def test_get_review_detail_returns_record(client):
    from app.routers import draft_reviews as router_module

    task_id = _create_task(client)
    draft_id = _create_draft(client, task_id)
    original = router_module.ContentQualityReviewService.review_draft

    def fake_review(self, draft_id: int, llm_provider=None, actor="quality_reviewer"):
        record = ContentDraftReview(
            draft_id=draft_id,
            status="needs_revision",
            overall_score=70,
            tone_score=75,
            medical_safety_score=80,
            cta_safety_score=68,
            discipline_score=72,
            risk_flags_json="[]",
            suggested_rewrites_json="[]",
            review_summary="Please soften CTA language.",
            raw_review_json='{"contract_version":"content_review.v1"}',
            reviewed_by=actor,
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(router_module.ContentQualityReviewService, "review_draft", fake_review)
    review = client.post(f"/drafts/{draft_id}/review-quality", headers=AUTH_HEADERS).json()
    monkeypatch.setattr(router_module.ContentQualityReviewService, "review_draft", original)
    monkeypatch.undo()
    response = client.get(f"/draft-reviews/{review['id']}", headers=AUTH_HEADERS)
    assert response.status_code == 200
    assert response.json()["id"] == review["id"]


def test_missing_draft_or_review_returns_clear_error(client):
    missing_draft = client.post("/drafts/999999/review-quality", headers=AUTH_HEADERS)
    assert missing_draft.status_code in (400, 404)

    missing_review = client.get("/draft-reviews/999999", headers=AUTH_HEADERS)
    assert missing_review.status_code == 404


def test_no_external_integration_routes_added(client):
    for path in ["/facebook", "/instagram", "/telegram", "/line", "/x", "/n8n"]:
        response = client.get(path)
        assert response.status_code == 404


def test_no_agents_enabled(client):
    response = client.get("/agents", headers=AUTH_HEADERS)
    assert response.status_code == 200
    agents = response.json()
    enabled = [agent["id"] for agent in agents if agent["is_enabled"]]
    assert enabled == ["ceo_agent"]
