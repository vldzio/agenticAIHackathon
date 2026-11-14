#!/usr/bin/env python3
"""OpenAI-compatible LLM client with the same interface as ``GeminiClient``.

Used for the free public demo (a private FreeLLMAPI gateway) and for visitors who bring their own
OpenAI-compatible key. LangGraph node runs are traced to LangSmith when ``LANGSMITH_TRACING=true``;
this client additionally wraps the OpenAI SDK so every model call appears as a child run.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

from utils.gemini_client import extract_json

logger = logging.getLogger(__name__)


class OpenAICompatClient:
    def __init__(self, api_key: str, base_url: str, model: Optional[str] = None, timeout: float = 90.0):
        if not base_url:
            raise ValueError("An LLM base URL is required.")
        from openai import OpenAI

        self.model = model or os.getenv("LLM_MODEL_ID", "auto")
        client = OpenAI(api_key=api_key or "not-needed", base_url=base_url, timeout=timeout, max_retries=1)
        if os.getenv("LANGSMITH_TRACING", "").lower() == "true" and os.getenv("LANGSMITH_API_KEY"):
            try:
                from langsmith.wrappers import wrap_openai

                client = wrap_openai(client)
            except Exception as exc:  # tracing must never break the app
                logger.warning("LangSmith wrap failed: %s", exc)
        self.client = client

    def generate_content(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        response_mime_type: Optional[str] = None,
    ) -> str:
        kwargs: Dict[str, Any] = dict(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a careful fitness-planning assistant. Reply with valid JSON only when asked for JSON."},
                {"role": "user", "content": prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        try:
            if response_mime_type == "application/json":
                try:
                    resp = self.client.chat.completions.create(response_format={"type": "json_object"}, **kwargs)
                except Exception:
                    # some free models reject response_format; retry plainly
                    resp = self.client.chat.completions.create(**kwargs)
            else:
                resp = self.client.chat.completions.create(**kwargs)
        except Exception as exc:
            raise ValueError(f"Failed to generate content from LLM: {exc}") from exc
        text = (resp.choices[0].message.content or "") if resp.choices else ""
        if not text.strip():
            raise ValueError("Empty response from LLM")
        return text

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
