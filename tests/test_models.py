from __future__ import annotations

from sqlalchemy import inspect

from app.database import Base


def test_phase_one_database_tables_exist(db_session):
    tables = set(inspect(db_session.bind).get_table_names())

    assert {
        "tasks",
        "agents",
        "events",
        "memories",
        "llm_calls",
    }.issubset(tables)


def test_task_model_has_governance_fields():
    columns = set(Base.metadata.tables["tasks"].columns.keys())

    assert {
        "task_type",
        "priority",
        "risk_level",
        "suggested_agent_role",
        "primary_agent_role",
        "supporting_agent_roles_json",
        "ceo_decision_json",
        "ceo_decision_text",
        "reasoning_summary",
        "reviewed_at",
        "is_archived",
        "archived_at",
    }.issubset(columns)


def test_llm_call_model_uses_safe_log_fields():
    columns = set(Base.metadata.tables["llm_calls"].columns.keys())

    assert "prompt_preview" in columns
    assert "raw_response" in columns
    assert "parsed_json" in columns
    assert "prompt" not in columns


def test_content_draft_model_has_archive_and_generation_failure_fields():
    columns = set(Base.metadata.tables["content_drafts"].columns.keys())

    assert {
        "generation_state",
        "retry_count",
        "last_error",
        "last_error_at",
        "is_archived",
        "archived_at",
    }.issubset(columns)
