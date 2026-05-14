from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    app_env: str = os.getenv("APP_ENV", "local")
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./lobster_cns.db")
    admin_secret: str = os.getenv("ADMIN_SECRET", "change-me")
    llm_provider: str = os.getenv("LLM_PROVIDER", "deepseek")
    deepseek_api_key: str = os.getenv("DEEPSEEK_API_KEY", "")
    deepseek_model: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    deepseek_base_url: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    llm_timeout_seconds: float = float(os.getenv("LLM_TIMEOUT_SECONDS", "30"))
    llm_max_retries: int = int(os.getenv("LLM_MAX_RETRIES", "2"))


settings = Settings()
