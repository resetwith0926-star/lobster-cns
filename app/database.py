from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings


connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from app.models import agent, content_draft, content_draft_review, event, llm_call, memory, task  # noqa: F401
    from app.services.agent_registry import AgentRegistry
    from app.services.memory_service import MemoryService

    Base.metadata.create_all(bind=engine)
    _apply_sqlite_startup_migration_guard()
    db = SessionLocal()
    try:
        AgentRegistry(db).ensure_default_agents()
        MemoryService(db).seed_core_memories()
    finally:
        db.close()


def _apply_sqlite_startup_migration_guard() -> None:
    if engine.dialect.name != "sqlite":
        return

    inspector = inspect(engine)
    if "tasks" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("tasks")}
    statements = []
    if "primary_agent_role" not in existing_columns:
        statements.append("ALTER TABLE tasks ADD COLUMN primary_agent_role VARCHAR(80)")
    if "supporting_agent_roles_json" not in existing_columns:
        statements.append("ALTER TABLE tasks ADD COLUMN supporting_agent_roles_json TEXT")
    if "is_archived" not in existing_columns:
        statements.append("ALTER TABLE tasks ADD COLUMN is_archived BOOLEAN NOT NULL DEFAULT 0")
    if "archived_at" not in existing_columns:
        statements.append("ALTER TABLE tasks ADD COLUMN archived_at DATETIME")

    if not statements:
        _ensure_content_drafts_table_sqlite(inspector)
        _ensure_content_draft_reviews_table_sqlite(inspector)
        return

    with engine.begin() as conn:
        for statement in statements:
            conn.execute(text(statement))
    _ensure_content_drafts_table_sqlite(inspector)
    _ensure_content_draft_reviews_table_sqlite(inspector)


def _ensure_content_drafts_table_sqlite(inspector) -> None:
    table_names = set(inspector.get_table_names())
    if "content_drafts" not in table_names:
        create_stmt = """
        CREATE TABLE content_drafts (
            id INTEGER NOT NULL PRIMARY KEY,
            task_id INTEGER NOT NULL,
            title VARCHAR(255) NOT NULL,
            channel_hint VARCHAR(80),
            target_audience VARCHAR(255),
            source_decision_json TEXT,
            draft_text TEXT,
            status VARCHAR(50) NOT NULL DEFAULT 'draft',
            generation_state VARCHAR(50) NOT NULL DEFAULT 'idle',
            retry_count INTEGER NOT NULL DEFAULT 0,
            last_error TEXT,
            last_error_at DATETIME,
            is_archived BOOLEAN NOT NULL DEFAULT 0,
            archived_at DATETIME,
            review_notes TEXT,
            version INTEGER NOT NULL DEFAULT 1,
            created_by VARCHAR(100) NOT NULL DEFAULT 'ceo_agent',
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL,
            reviewed_at DATETIME,
            FOREIGN KEY(task_id) REFERENCES tasks (id)
        )
        """
        with engine.begin() as conn:
            conn.execute(text(create_stmt))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_content_drafts_id ON content_drafts (id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_content_drafts_task_id ON content_drafts (task_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_content_drafts_status ON content_drafts (status)"))
        return

    required_columns = {
        "id": "ALTER TABLE content_drafts ADD COLUMN id INTEGER",
        "task_id": "ALTER TABLE content_drafts ADD COLUMN task_id INTEGER",
        "title": "ALTER TABLE content_drafts ADD COLUMN title VARCHAR(255)",
        "channel_hint": "ALTER TABLE content_drafts ADD COLUMN channel_hint VARCHAR(80)",
        "target_audience": "ALTER TABLE content_drafts ADD COLUMN target_audience VARCHAR(255)",
        "source_decision_json": "ALTER TABLE content_drafts ADD COLUMN source_decision_json TEXT",
        "draft_text": "ALTER TABLE content_drafts ADD COLUMN draft_text TEXT",
        "status": "ALTER TABLE content_drafts ADD COLUMN status VARCHAR(50)",
        "generation_state": "ALTER TABLE content_drafts ADD COLUMN generation_state VARCHAR(50) NOT NULL DEFAULT 'idle'",
        "retry_count": "ALTER TABLE content_drafts ADD COLUMN retry_count INTEGER NOT NULL DEFAULT 0",
        "last_error": "ALTER TABLE content_drafts ADD COLUMN last_error TEXT",
        "last_error_at": "ALTER TABLE content_drafts ADD COLUMN last_error_at DATETIME",
        "is_archived": "ALTER TABLE content_drafts ADD COLUMN is_archived BOOLEAN NOT NULL DEFAULT 0",
        "archived_at": "ALTER TABLE content_drafts ADD COLUMN archived_at DATETIME",
        "review_notes": "ALTER TABLE content_drafts ADD COLUMN review_notes TEXT",
        "version": "ALTER TABLE content_drafts ADD COLUMN version INTEGER",
        "created_by": "ALTER TABLE content_drafts ADD COLUMN created_by VARCHAR(100)",
        "created_at": "ALTER TABLE content_drafts ADD COLUMN created_at DATETIME",
        "updated_at": "ALTER TABLE content_drafts ADD COLUMN updated_at DATETIME",
        "reviewed_at": "ALTER TABLE content_drafts ADD COLUMN reviewed_at DATETIME",
    }
    existing_columns = {column["name"] for column in inspector.get_columns("content_drafts")}
    missing = [statement for column, statement in required_columns.items() if column not in existing_columns]
    if not missing:
        return

    with engine.begin() as conn:
        for statement in missing:
            conn.execute(text(statement))


def _ensure_content_draft_reviews_table_sqlite(inspector) -> None:
    table_names = set(inspector.get_table_names())
    if "content_draft_reviews" not in table_names:
        create_stmt = """
        CREATE TABLE content_draft_reviews (
            id INTEGER NOT NULL PRIMARY KEY,
            draft_id INTEGER NOT NULL,
            status VARCHAR(50) NOT NULL DEFAULT 'needs_revision',
            overall_score INTEGER NOT NULL,
            tone_score INTEGER NOT NULL,
            medical_safety_score INTEGER NOT NULL,
            cta_safety_score INTEGER NOT NULL,
            discipline_score INTEGER NOT NULL,
            risk_flags_json TEXT,
            suggested_rewrites_json TEXT,
            review_summary TEXT,
            raw_review_json TEXT,
            reviewed_by VARCHAR(100) NOT NULL DEFAULT 'quality_reviewer',
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL,
            FOREIGN KEY(draft_id) REFERENCES content_drafts (id)
        )
        """
        with engine.begin() as conn:
            conn.execute(text(create_stmt))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_content_draft_reviews_id ON content_draft_reviews (id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_content_draft_reviews_draft_id ON content_draft_reviews (draft_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_content_draft_reviews_status ON content_draft_reviews (status)"))
        return

    required_columns = {
        "id": "ALTER TABLE content_draft_reviews ADD COLUMN id INTEGER",
        "draft_id": "ALTER TABLE content_draft_reviews ADD COLUMN draft_id INTEGER",
        "status": "ALTER TABLE content_draft_reviews ADD COLUMN status VARCHAR(50)",
        "overall_score": "ALTER TABLE content_draft_reviews ADD COLUMN overall_score INTEGER",
        "tone_score": "ALTER TABLE content_draft_reviews ADD COLUMN tone_score INTEGER",
        "medical_safety_score": "ALTER TABLE content_draft_reviews ADD COLUMN medical_safety_score INTEGER",
        "cta_safety_score": "ALTER TABLE content_draft_reviews ADD COLUMN cta_safety_score INTEGER",
        "discipline_score": "ALTER TABLE content_draft_reviews ADD COLUMN discipline_score INTEGER",
        "risk_flags_json": "ALTER TABLE content_draft_reviews ADD COLUMN risk_flags_json TEXT",
        "suggested_rewrites_json": "ALTER TABLE content_draft_reviews ADD COLUMN suggested_rewrites_json TEXT",
        "review_summary": "ALTER TABLE content_draft_reviews ADD COLUMN review_summary TEXT",
        "raw_review_json": "ALTER TABLE content_draft_reviews ADD COLUMN raw_review_json TEXT",
        "reviewed_by": "ALTER TABLE content_draft_reviews ADD COLUMN reviewed_by VARCHAR(100)",
        "created_at": "ALTER TABLE content_draft_reviews ADD COLUMN created_at DATETIME",
        "updated_at": "ALTER TABLE content_draft_reviews ADD COLUMN updated_at DATETIME",
    }
    existing_columns = {column["name"] for column in inspector.get_columns("content_draft_reviews")}
    missing = [statement for column, statement in required_columns.items() if column not in existing_columns]
    if not missing:
        return

    with engine.begin() as conn:
        for statement in missing:
            conn.execute(text(statement))
