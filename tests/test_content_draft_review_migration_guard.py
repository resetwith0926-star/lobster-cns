from __future__ import annotations

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

import app.database as database_module


def _run_guard_with_engine(test_engine):
    original_engine = database_module.engine
    try:
        database_module.engine = test_engine
        database_module._apply_sqlite_startup_migration_guard()
    finally:
        database_module.engine = original_engine


def test_migration_guard_creates_missing_content_draft_reviews_table(tmp_path):
    db_path = tmp_path / "create_review_table.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE tasks (id INTEGER NOT NULL PRIMARY KEY, title VARCHAR(255) NOT NULL)"))
        conn.execute(text("CREATE TABLE content_drafts (id INTEGER NOT NULL PRIMARY KEY, task_id INTEGER NOT NULL, title VARCHAR(255) NOT NULL)"))

    _run_guard_with_engine(engine)
    inspector = inspect(engine)
    assert "content_draft_reviews" in inspector.get_table_names()


def test_migration_guard_for_reviews_runs_twice_without_error(tmp_path):
    db_path = tmp_path / "review_idempotent.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE tasks (id INTEGER NOT NULL PRIMARY KEY, title VARCHAR(255) NOT NULL)"))
        conn.execute(text("CREATE TABLE content_drafts (id INTEGER NOT NULL PRIMARY KEY, task_id INTEGER NOT NULL, title VARCHAR(255) NOT NULL)"))

    _run_guard_with_engine(engine)
    _run_guard_with_engine(engine)

    inspector = inspect(engine)
    columns = {col["name"] for col in inspector.get_columns("content_draft_reviews")}
    assert {"id", "draft_id", "status", "overall_score", "reviewed_by"}.issubset(columns)


def test_migration_guard_for_reviews_patches_missing_columns_and_preserves_data(tmp_path):
    db_path = tmp_path / "review_patch_columns.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE tasks (id INTEGER NOT NULL PRIMARY KEY, title VARCHAR(255) NOT NULL)"))
        conn.execute(text("CREATE TABLE content_drafts (id INTEGER NOT NULL PRIMARY KEY, task_id INTEGER NOT NULL, title VARCHAR(255) NOT NULL)"))
        conn.execute(
            text(
                """
                CREATE TABLE content_draft_reviews (
                    id INTEGER NOT NULL PRIMARY KEY,
                    draft_id INTEGER NOT NULL,
                    status VARCHAR(50) NOT NULL,
                    overall_score INTEGER NOT NULL
                )
                """
            )
        )
        conn.execute(text("INSERT INTO tasks (id, title) VALUES (1, 'Task')"))
        conn.execute(text("INSERT INTO content_drafts (id, task_id, title) VALUES (1, 1, 'Seed draft')"))
        conn.execute(text("INSERT INTO content_draft_reviews (id, draft_id, status, overall_score) VALUES (1, 1, 'pass', 90)"))

    _run_guard_with_engine(engine)

    inspector = inspect(engine)
    columns = {col["name"] for col in inspector.get_columns("content_draft_reviews")}
    assert "tone_score" in columns
    assert "medical_safety_score" in columns
    assert "cta_safety_score" in columns
    assert "discipline_score" in columns
    assert "created_at" in columns
    assert "updated_at" in columns

    Session = sessionmaker(bind=engine)
    with Session() as session:
        row = session.execute(text("SELECT id, draft_id, status, overall_score FROM content_draft_reviews WHERE id = 1")).fetchone()
        assert row is not None
        assert row[0] == 1
        assert row[1] == 1
        assert row[2] == "pass"
        assert row[3] == 90
