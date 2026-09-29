from __future__ import annotations

from typing import Any

from app.llm.base import LLMInvalidResponseError, T
from app.llm.mock_generators import GENERATORS


class MockLLMClient:
    """Simulated generation. Always labelled ``simulated`` in API responses and the UI."""

    simulated = True

    def generate(self, task: str, prompt: str, schema: type[T], context: dict[str, Any]) -> T:
        del prompt
        generator = GENERATORS.get(task)
        if generator is None:
            raise LLMInvalidResponseError(f"Mock generator has no task '{task}'")
        return schema.model_validate(generator(context))
