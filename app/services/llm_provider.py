from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class LLMResponse:
    provider: str
    model: str
    raw_text: str
    parsed_json: Optional[Dict[str, Any]]
    latency_ms: int
    success: bool
    error: Optional[str] = None


class LLMProvider(ABC):
    @abstractmethod
    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        task_id: Optional[int] = None,
        json_mode: bool = True,
    ) -> LLMResponse:
        raise NotImplementedError
