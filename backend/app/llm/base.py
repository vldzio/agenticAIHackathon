from __future__ import annotations

from typing import Any, Protocol, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class LLMError(Exception):
    """Base class. ``code`` is a stable machine-readable identifier; ``message`` is safe to show to users."""

    code = "llm_error"
    retryable = False
    fatal = False  # fatal => no point trying the remaining LLM steps

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class LLMAuthError(LLMError):
    code = "llm_auth"
    fatal = True


class LLMRateLimitError(LLMError):
    code = "llm_rate_limited"
    retryable = True
    fatal = True  # quota exhausted for this key: the next steps would fail identically


class LLMUnavailableError(LLMError):
    code = "llm_unavailable"
    retryable = True


class LLMInvalidResponseError(LLMError):
    code = "llm_invalid_response"
    retryable = True


class LLMClient(Protocol):
    simulated: bool

    def generate(self, task: str, prompt: str, schema: type[T], context: dict[str, Any]) -> T:
        """Return a validated ``schema`` instance. ``context`` carries structured facts (used by the mock)."""
        ...
