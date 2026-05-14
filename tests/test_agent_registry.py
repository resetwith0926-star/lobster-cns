from __future__ import annotations

import pytest

from app.services.agent_registry import AgentRegistry


def test_agent_registry_seeds_ten_placeholder_agents(db_session):
    registry = AgentRegistry(db_session)
    registry.ensure_default_agents()

    agents = registry.list_agents()

    assert len(agents) == 10
    assert {agent.id for agent in agents} == {
        "ceo_agent",
        "content_agent",
        "sales_agent",
        "dev_agent",
        "facebook_page_agent",
        "facebook_personal_agent",
        "instagram_agent",
        "x_agent",
        "line_agent",
        "telegram_agent",
    }


def test_only_ceo_agent_is_enabled_by_default(db_session):
    registry = AgentRegistry(db_session)
    registry.ensure_default_agents()

    enabled_agents = [agent.id for agent in registry.list_agents() if agent.is_enabled]

    assert enabled_agents == ["ceo_agent"]
    assert registry.can_execute("ceo_agent") is True
    assert registry.can_execute("facebook_page_agent") is False


def test_disabled_agents_cannot_execute_tasks(db_session):
    registry = AgentRegistry(db_session)
    registry.ensure_default_agents()

    with pytest.raises(PermissionError):
        registry.ensure_can_execute("telegram_agent")

