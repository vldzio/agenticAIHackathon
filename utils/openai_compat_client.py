#!/usr/bin/env python3
"""OpenAI-compatible LLM client with the same interface as ``GeminiClient``.

Used for the free public demo (a private FreeLLMAPI gateway) and for visitors who bring their own
OpenAI-compatible key. LangGraph node runs are traced to LangSmith when ``LANGSMITH_TRACING=true``;
this client additionally wraps the OpenAI SDK so every model call appears as a child run.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict, List, Optional

from utils.gemini_client import extract_json

logger = logging.getLogger(__name__)


# Free-demo model chain, tried in order; "name@effort" sets reasoning_effort for a reasoning model.
# The gateway's own "auto" route is last on purpose: it often picks slow or rate-limited free models,
# which made one assessment take minutes. The first entries are fast models on different providers,
# so a rate limit on one provider falls through to another.
DEFAULT_FREE_MODELS = "gemini-3.1-flash-lite,qwen3.8-27b,gpt-oss-120b@low,gemini-3.5-flash-lite,gpt-oss-20b@low,auto"
COOLDOWN_SECONDS = 60.0
_cooldown_until: Dict[str, float] = {}  # model -> time before which it is skipped after a failure


def free_demo_models() -> List[str]:
    raw = os.getenv("LLM_MODELS") or DEFAULT_FREE_MODELS
    return [m.strip() for m in raw.split(",") if m.strip()] or ["auto"]


class OpenAICompatClient:
    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: Optional[str] = None,
        timeout: Optional[float] = None,
        models: Optional[List[str]] = None,
    ):
        """``models`` is a fallback chain (free demo); without it a single ``model`` is used (own key)."""
        if not base_url:
            raise ValueError("An LLM base URL is required.")
        from openai import OpenAI

        self.models = list(models) if models else [model or os.getenv("LLM_MODEL_ID", "auto")]
        self.model = self.models[0]
        chain = len(self.models) > 1
        # With a chain, fail fast and move on: a stuck or cooling-down model must not hold the request.
        client = OpenAI(
            api_key=api_key or "not-needed",
            base_url=base_url,
            timeout=timeout or (float(os.getenv("LLM_TIMEOUT_S", "25")) if chain else 90.0),
            max_retries=0 if chain else 1,
        )
        if os.getenv("LANGSMITH_TRACING", "").lower() == "true" and os.getenv("LANGSMITH_API_KEY"):
            try:
                from langsmith.wrappers import wrap_openai

                client = wrap_openai(client)
            except Exception as exc:  # tracing must never break the app
                logger.warning("LangSmith wrap failed: %s", exc)
        self.client = client

    def _complete(self, spec: str, json_mode: bool, kwargs: Dict[str, Any]) -> str:
        from openai import APIStatusError

        model, _, effort = spec.partition("@")
        kwargs = dict(kwargs, model=model)
        if effort:
            kwargs["reasoning_effort"] = effort
        if json_mode:
            try:
                resp = self.client.chat.completions.create(response_format={"type": "json_object"}, **kwargs)
            except APIStatusError as exc:
                if exc.status_code not in (400, 422):
                    raise
                # the model rejected response_format or failed its own JSON check: ask plainly
                resp = self.client.chat.completions.create(**kwargs)
        else:
            resp = self.client.chat.completions.create(**kwargs)
        text = (resp.choices[0].message.content or "") if resp.choices else ""
        if not text.strip():
            raise ValueError("Empty response from LLM")
        return text

    def generate_content(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        response_mime_type: Optional[str] = None,
    ) -> str:
        kwargs: Dict[str, Any] = dict(
            messages=[
                {"role": "system", "content": "You are a careful fitness-planning assistant. Reply with valid JSON only when asked for JSON."},
                {"role": "user", "content": prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        now = time.monotonic()
        ready = [m for m in self.models if _cooldown_until.get(m, 0) <= now] or self.models
        last_error: Optional[Exception] = None
        for spec in ready:
            try:
                return self._complete(spec, response_mime_type == "application/json", kwargs)
            except Exception as exc:
                last_error = exc
                if len(self.models) > 1:
                    _cooldown_until[spec] = time.monotonic() + COOLDOWN_SECONDS
                    logger.warning("Model %s failed (%s); trying the next one", spec, type(exc).__name__)
        raise ValueError(f"Failed to generate content from LLM: {last_error}") from last_error

    def extract_json_from_response(self, response_text: str) -> Dict[str, Any]:
        return extract_json(response_text)

    def validate_response_fields(self, response: Dict[str, Any], required_fields: List[str]) -> None:
        missing = [f for f in required_fields if f not in response]
        if missing:
            raise ValueError(f"LLM response missing required fields: {missing}")

    def generate_structured_json(
        self,
        prompt: str,
        required_fields: List[str],
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> Dict[str, Any]:
        """One corrective retry: free models occasionally omit fields or wrap JSON in prose."""
        last_error: Optional[Exception] = None
        current = prompt
        for attempt in range(2):
            text = self.generate_content(
                current, temperature=temperature, max_tokens=max_tokens, response_mime_type="application/json"
            )
            try:
                result = self.extract_json_from_response(text)
                self.validate_response_fields(result, required_fields)
                return result
            except ValueError as exc:
                last_error = exc
                logger.warning("Structured JSON attempt %s failed: %s", attempt + 1, exc)
                current = (
                    prompt
                    + f"\n\nYour previous reply was invalid ({exc}). Reply again with ONLY one JSON object "
                    + f"containing at least these keys: {', '.join(required_fields)}."
                )
        raise ValueError(f"LLM did not return valid structured JSON: {last_error}")
