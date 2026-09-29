"""Opt-in smoke test against the real Gemini API:  GEMINI_API_KEY=... pytest -m live"""

import os

import pytest

from app.llm.gemini import GeminiClient
from app.schemas.llm import NormalizedInputs

pytestmark = pytest.mark.live


@pytest.mark.skipif(not os.getenv("GEMINI_API_KEY"), reason="GEMINI_API_KEY not set")
def test_live_normalisation():
    from app.config import get_settings
    from app.llm.prompt_loader import render

    client = GeminiClient(os.environ["GEMINI_API_KEY"], get_settings().gemini_model)
    prompt = render(
        "normalize",
        NormalizedInputs,
        fitness_experience="I've lifted for 3 years",
        health_conditions="mild asthma",
        available_hours_per_week="5 hours, weekday evenings",
    )
    out = client.generate("normalize", prompt, NormalizedInputs, {})
    assert out.experience.experience_level == "Some Experience"
    assert out.health.conditions
