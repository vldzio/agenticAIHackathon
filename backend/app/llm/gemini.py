"""Live Gemini client (bring-your-own-key). Uses the supported ``google-genai`` SDK.

* per-request key, kept only in this object; never logged (all messages are redacted);
* timeout, exponential back-off retries on 429/5xx/network errors;
* native structured output (``response_schema``) with Pydantic validation and one automatic repair attempt.
"""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Any

from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from pydantic import ValidationError

from app.llm.base import (
    LLMAuthError,
    LLMError,
    LLMInvalidResponseError,
    LLMRateLimitError,
    LLMUnavailableError,
    T,
)

logger = logging.getLogger(__name__)

_JSON_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


def extract_json(text: str) -> Any:
    """Parse a JSON object from model text, tolerating markdown fences and surrounding prose."""
    candidates = [text.strip()]
    candidates += [m.strip() for m in _JSON_FENCE.findall(text)]
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        candidates.append(text[start : end + 1])
    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    raise ValueError("No valid JSON object found in the model response")


class GeminiClient:
    simulated = False

    def __init__(
        self,
        api_key: str,
        model: str,
        timeout_seconds: float = 45.0,
        max_retries: int = 3,
        backoff_seconds: float = 1.0,
        client: Any | None = None,
    ) -> None:
        if not api_key or not api_key.strip():
            raise LLMAuthError("A Gemini API key is required for live mode.")
        self._key = api_key.strip()
        self.model = model
        self.max_retries = max_retries
        self.backoff_seconds = backoff_seconds
        self._use_native_schema = True
        self._client = client or genai.Client(
            api_key=self._key, http_options=types.HttpOptions(timeout=int(timeout_seconds * 1000))
        )

    # -- helpers ---------------------------------------------------------------------------
    def _redact(self, text: str) -> str:
        return text.replace(self._key, "[redacted]")

    def _classify(self, exc: Exception) -> LLMError:
        if isinstance(exc, genai_errors.APIError):
            code = int(exc.code or 0)
            detail = self._redact(str(exc.message or "")).lower()
            if code in (401, 403) or (code == 400 and ("api key" in detail or "api_key" in detail)):
                return LLMAuthError("Gemini rejected the API key. Check that the key is valid and enabled.")
            if code == 429:
                return LLMRateLimitError("Gemini rate limit or quota reached for this API key. Try again shortly.")
            if code >= 500:
                return LLMUnavailableError("Gemini is temporarily unavailable.")
            if code == 404:
                return LLMError(f"Gemini model '{self.model}' was not found or is not available to this key.")
            return LLMError(f"Gemini rejected the request ({code}).")
        return LLMUnavailableError("Could not reach Gemini (network error or timeout).")

    def _call(self, prompt: str, schema: type[T]) -> str:
        config = types.GenerateContentConfig(
            temperature=0.4,
            max_output_tokens=4096,
            response_mime_type="application/json",
            response_schema=schema if self._use_native_schema else None,
        )
        response = self._client.models.generate_content(model=self.model, contents=prompt, config=config)
        text = getattr(response, "text", None)
        if not text:
            raise LLMInvalidResponseError("Gemini returned an empty response.")
        return text

    def _call_with_retries(self, prompt: str, schema: type[T]) -> str:
        last: LLMError | None = None
        for attempt in range(self.max_retries + 1):
            try:
                return self._call(prompt, schema)
            except LLMError as exc:
                error = exc
            except Exception as exc:
                error = self._classify(exc)
                if error.code == "llm_error" and self._use_native_schema and "schema" in self._redact(str(exc)).lower():
                    logger.warning("Gemini rejected the response schema; retrying without native schema")
                    self._use_native_schema = False
                    continue
                logger.warning("Gemini call failed (%s): %s", error.code, type(exc).__name__)
            last = error
            if not error.retryable or error.fatal or attempt == self.max_retries:
                break
            time.sleep(self.backoff_seconds * (2**attempt))
        assert last is not None
        raise last

    # -- public ----------------------------------------------------------------------------
    def generate(self, task: str, prompt: str, schema: type[T], context: dict[str, Any]) -> T:
        del context
        text = self._call_with_retries(prompt, schema)
        try:
            return schema.model_validate(extract_json(text))
        except (ValueError, ValidationError) as first_error:
            logger.info("Gemini output for '%s' failed validation; attempting one repair", task)
            repair_prompt = (
                f"{prompt}\n\nYour previous answer was invalid: {str(first_error)[:800]}\n"
                "Return ONLY corrected JSON that satisfies the schema."
            )
            text = self._call_with_retries(repair_prompt, schema)
            try:
                return schema.model_validate(extract_json(text))
            except (ValueError, ValidationError) as exc:
                raise LLMInvalidResponseError(f"Gemini returned malformed output for '{task}' twice: {str(exc)[:200]}") from exc
