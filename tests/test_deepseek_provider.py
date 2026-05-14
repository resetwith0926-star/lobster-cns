from __future__ import annotations

from sqlalchemy import select

from app.models.llm_call import LLMCall
from app.services.event_log import EventLog
from app.services.deepseek_provider import (
    DeepSeekLLMProvider,
    parse_json_from_text,
    sanitize_secret_text,
)


class FakeSuccessDeepSeekProvider(DeepSeekLLMProvider):
    def _request(self, messages, temperature, json_mode=True):
        self.last_json_mode = json_mode
        return '{"contract_version":"ceo_decision.v1","ok":true}'


class FakeFailingDeepSeekProvider(DeepSeekLLMProvider):
    def _request(self, messages, temperature, json_mode=True):
        raise RuntimeError("boom sk-test-secret-1234567890")


def test_parse_json_from_plain_or_fenced_text():
    assert parse_json_from_text('{"ok": true}') == {"ok": True}
    assert parse_json_from_text('```json\n{"ok": true}\n```') == {"ok": True}
    assert parse_json_from_text("not json") is None


def test_deepseek_provider_saves_successful_llm_call(db_session):
    provider = FakeSuccessDeepSeekProvider(db_session)

    response = provider.chat([{"role": "user", "content": "hello"}], task_id=7, json_mode=True)
    call = db_session.scalars(select(LLMCall)).one()

    assert response.success is True
    assert response.parsed_json == {"contract_version": "ceo_decision.v1", "ok": True}
    assert call.provider == "deepseek"
    assert call.task_id == 7
    assert call.success is True
    assert call.parsed_json is not None
    assert provider.last_json_mode is True
    event_types = [event.event_type for event in EventLog(db_session).list_for_task(7)]
    assert "llm_call_completed" in event_types


def test_deepseek_provider_saves_failed_llm_call_without_leaking_key(db_session):
    provider = FakeFailingDeepSeekProvider(db_session)

    response = provider.chat([{"role": "user", "content": "hello"}], task_id=9)
    call = db_session.scalars(select(LLMCall)).one()

    assert response.success is False
    assert call.success is False
    assert "sk-test-secret" not in (call.error or "")
    assert "sk-[REDACTED]" in (call.error or "")
    event_types = [event.event_type for event in EventLog(db_session).list_for_task(9)]
    assert "llm_call_failed" in event_types


def test_deepseek_provider_text_mode_skips_json_response_format(db_session):
    provider = FakeSuccessDeepSeekProvider(db_session)

    response = provider.chat([{"role": "user", "content": "write plain text"}], task_id=11, json_mode=False)

    assert response.success is True
    assert provider.last_json_mode is False


def test_sanitize_secret_text_masks_openai_style_keys():
    text = "bad key sk-test-secret-1234567890 appeared"

    sanitized = sanitize_secret_text(text)

    assert "sk-test-secret" not in sanitized
    assert "sk-[REDACTED]" in sanitized
