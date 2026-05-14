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


def test_migration_guard_creates_missing_content_drafts_table(tmp_path):
    db_path = tmp_path / "create_table.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE tasks (
                    id INTEGER NOT NULL PRIMARY KEY,
                    title VARCHAR(255) NOT NULL
                )
                """
            )
        )

    _run_guard_with_engine(engine)
    inspector = inspect(engine)
    assert "content_drafts" in inspector.get_table_names()


def test_migration_guard_runs_twice_without_error(tmp_path):
    db_path = tmp_path / "idempotent.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE tasks (
                    id INTEGER NOT NULL PRIMARY KEY,
                    title VARCHAR(255) NOT NULL
                )
                """
            )
        )

    _run_guard_with_engine(engine)
    _run_guard_with_engine(engine)

    inspector = inspect(engine)
    columns = {col["name"] for col in inspector.get_columns("content_drafts")}
    assert {"id", "task_id", "title", "status", "version", "created_by"}.issubset(columns)


def test_migration_guard_patches_missing_columns_and_preserves_data(tmp_path):
    db_path = tmp_path / "patch_columns.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE tasks (
                    id INTEGER NOT NULL PRIMARY KEY,
                    title VARCHAR(255) NOT NULL
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE content_drafts (
                    id INTEGER NOT NULL PRIMARY KEY,
                    task_id INTEGER NOT NULL,
                    title VARCHAR(255) NOT NULL
                )
                """
            )
        )
        conn.execute(text("INSERT INTO tasks (id, title) VALUES (1, 'Task')"))
        conn.execute(text("INSERT INTO content_drafts (id, task_id, title) VALUES (1, 1, 'Seed draft')"))

    _run_guard_with_engine(engine)

    inspector = inspect(engine)
    columns = {col["name"] for col in inspector.get_columns("content_drafts")}
    assert "status" in columns
    assert "generation_state" in columns
    assert "retry_count" in columns
    assert "last_error" in columns
    assert "last_error_at" in columns
    assert "is_archived" in columns
    assert "archived_at" in columns
    assert "review_notes" in columns
    assert "reviewed_at" in columns

    Session = sessionmaker(bind=engine)
    with Session() as session:
        row = session.execute(text("SELECT id, task_id, title FROM content_drafts WHERE id = 1")).fetchone()
        assert row is not None
        assert row[0] == 1
        assert row[1] == 1
        assert row[2] == "Seed draft"


def test_migration_guard_patches_missing_task_archive_columns(tmp_path):
    db_path = tmp_path / "patch_task_columns.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE tasks (
                    id INTEGER NOT NULL PRIMARY KEY,
                    title VARCHAR(255) NOT NULL,
                    primary_agent_role VARCHAR(80)
                )
                """
            )
        )
        conn.execute(text("INSERT INTO tasks (id, title, primary_agent_role) VALUES (1, 'Task', 'ceo_agent')"))

    _run_guard_with_engine(engine)

    inspector = inspect(engine)
    columns = {col["name"] for col in inspector.get_columns("tasks")}
    assert "is_archived" in columns
    assert "archived_at" in columns

    Session = sessionmaker(bind=engine)
    with Session() as session:
        row = session.execute(text("SELECT id, title, primary_agent_role FROM tasks WHERE id = 1")).fetchone()
        assert row is not None
        assert row[0] == 1
        assert row[1] == "Task"
        assert row[2] == "ceo_agent"
