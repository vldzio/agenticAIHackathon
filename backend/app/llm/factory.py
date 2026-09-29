from __future__ import annotations

from app.config import get_settings
from app.llm.base import LLMClient
from app.llm.gemini import GeminiClient
from app.llm.mock import MockLLMClient


def build_llm_client(mode: str, api_key: str | None = None) -> LLMClient:
    if mode == "mock":
        return MockLLMClient()
    settings = get_settings()
    return GeminiClient(
        api_key=api_key or "",
        model=settings.gemini_model,
        timeout_seconds=settings.llm_timeout_seconds,
        max_retries=settings.llm_max_retries,
    )
