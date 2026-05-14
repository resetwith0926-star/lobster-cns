from __future__ import annotations

import json
import re
import time
from typing import Any, Dict, List, Optional

import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.models.llm_call import LLMCall
from app.services.event_log import EventLog
from app.services.llm_provider import LLMProvider, LLMResponse


MAX_PROMPT_PREVIEW_CHARS = 4000


def extract_json_candidate(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`").strip()
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start >= 0 and end > start:
        return cleaned[start : end + 1]
    return cleaned


def parse_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    candidate = extract_json_candidate(text)
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def sanitize_secret_text(text: Optional[str]) -> Optional[str]:
    if text is None:
        return None
    sanitized = text
    if settings.deepseek_api_key:
        sanitized = sanitized.replace(settings.deepseek_api_key, "[REDACTED_API_KEY]")
    return re.sub(r"sk-[A-Za-z0-9_\-]{8,}", "sk-[REDACTED]", sanitized)


class DeepSeekLLMProvider(LLMProvider):
    def __init__(self, db: Session):
        self.db = db
        self.events = EventLog(db)

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        task_id: Optional[int] = None,
        json_mode: bool = True,
    ) -> LLMResponse:
        self.events.log(
            "llm_call_started",
            actor="llm_provider",
            task_id=task_id,
            message="DeepSeek LLM call started.",
            metadata={"provider": "deepseek", "model": settings.deepseek_model},
        )
        started_at = time.perf_counter()
        raw_text = ""
        parsed_json: Optional[Dict[str, Any]] = None
        error: Optional[str] = None

        for attempt in range(settings.llm_max_retries + 1):
            try:
                raw_text = self._request(messages, temperature=temperature, json_mode=json_mode)
                parsed_json = parse_json_from_text(raw_text)
                latency_ms = int((time.perf_counter() - started_at) * 1000)
                call = self._save_call(
                    task_id=task_id,
                    messages=messages,
                    raw_response=raw_text,
                    parsed_json=parsed_json,
                    latency_ms=latency_ms,
                    success=True,
                    error=None,
                )
                self.events.log(
                    "llm_call_completed",
                    actor="llm_provider",
                    task_id=task_id,
                    message="DeepSeek LLM call completed.",
                    metadata={"llm_call_id": call.id, "latency_ms": latency_ms},
                )
                return LLMResponse(
                    provider="deepseek",
                    model=settings.deepseek_model,
                    raw_text=raw_text,
                    parsed_json=parsed_json,
                    latency_ms=latency_ms,
                    success=True,
                )
            except (httpx.HTTPError, RuntimeError) as exc:
                error = sanitize_secret_text(str(exc))
                if attempt >= settings.llm_max_retries:
                    break
                time.sleep(0.5 * (attempt + 1))

        latency_ms = int((time.perf_counter() - started_at) * 1000)
        call = self._save_call(
            task_id=task_id,
            messages=messages,
            raw_response=raw_text,
            parsed_json=parsed_json,
            latency_ms=latency_ms,
            success=False,
            error=error,
        )
        self.events.log(
            "llm_call_failed",
            actor="llm_provider",
            task_id=task_id,
            message="DeepSeek LLM call failed.",
            metadata={"llm_call_id": call.id, "error": error},
        )
        return LLMResponse(
            provider="deepseek",
            model=settings.deepseek_model,
            raw_text=raw_text,
            parsed_json=parsed_json,
            latency_ms=latency_ms,
            success=False,
            error=error or "DeepSeek request failed.",
        )

    def _request(self, messages: List[Dict[str, str]], temperature: float, json_mode: bool = True) -> str:
        if settings.llm_provider != "deepseek":
            raise RuntimeError(f"Unsupported LLM provider: {settings.llm_provider}")
        if not settings.deepseek_api_key:
            raise RuntimeError("DEEPSEEK_API_KEY is not configured.")

        payload = {
            "model": settings.deepseek_model,
            "messages": messages,
            "temperature": temperature,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        headers = {
            "Authorization": f"Bearer {settings.deepseek_api_key}",
            "Content-Type": "application/json",
        }
        url = f"{settings.deepseek_base_url.rstrip('/')}/chat/completions"

        with httpx.Client(timeout=settings.llm_timeout_seconds) as client:
            response = client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("Unexpected DeepSeek response shape.") from exc

    def _save_call(
        self,
        task_id: Optional[int],
        messages: List[Dict[str, str]],
        raw_response: str,
        parsed_json: Optional[Dict[str, Any]],
        latency_ms: int,
        success: bool,
        error: Optional[str],
    ) -> LLMCall:
        prompt_preview = json.dumps(messages, ensure_ascii=False)
        prompt_preview = sanitize_secret_text(prompt_preview) or ""
        prompt_preview = prompt_preview[:MAX_PROMPT_PREVIEW_CHARS]

        call = LLMCall(
            provider="deepseek",
            model=settings.deepseek_model,
            task_id=task_id,
            prompt_preview=prompt_preview,
            raw_response=sanitize_secret_text(raw_response),
            parsed_json=json.dumps(parsed_json, ensure_ascii=False) if parsed_json else None,
            latency_ms=latency_ms,
            success=success,
            error=sanitize_secret_text(error),
        )
        self.db.add(call)
        self.db.commit()
        self.db.refresh(call)
        return call
