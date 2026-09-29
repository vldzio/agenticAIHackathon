import os

# Configure BEFORE the app is imported.
os.environ["AETHERFIT_DATABASE_URL"] = "sqlite:///:memory:"
os.environ["AETHERFIT_RATE_LIMIT_PER_MINUTE"] = "100000"
os.environ["AETHERFIT_ASSESSMENT_RATE_LIMIT_PER_MINUTE"] = "100000"
os.environ["AETHERFIT_ENV"] = "test"

import pytest
from fastapi.testclient import TestClient

from app.graph.nodes import Deps
from app.graph.workflow import build_graph
from app.llm.mock import MockLLMClient
from app.main import create_app
from app.ml.predictors import FitnessPredictor, InjuryPredictor

DEVICE = {"X-Device-Id": "device-test-0001"}
OTHER_DEVICE = {"X-Device-Id": "device-test-0002"}

BASE_PROFILE = {
    "user_name": "Alex",
    "age": 30,
    "height_cm": 170,
    "weight_kg": 70,
    "gender": "Male",
    "fitness_goal": "Weight Loss",
    "fitness_experience": "Beginner, training 3 times per week",
    "health_conditions": "None",
    "available_hours_per_week": "4-5 hours, weekday mornings preferred",
    "previous_injury": False,
}


@pytest.fixture()
def profile() -> dict:
    return dict(BASE_PROFILE)


@pytest.fixture(scope="session")
def predictors():
    return FitnessPredictor(), InjuryPredictor()


@pytest.fixture()
def run_graph(predictors):
    def _run(profile: dict, llm=None, progress: dict | None = None) -> dict:
        deps = Deps(llm=llm or MockLLMClient(), fitness=predictors[0], injury=predictors[1])
        state = {"raw_profile": profile, "progress_context": progress, "sections": {}, "errors": [], "warnings": []}
        return build_graph(deps).invoke(state)

    return _run


@pytest.fixture()
def client():
    from app.db.session import reset_engine_for_tests

    reset_engine_for_tests()
    with TestClient(create_app()) as c:
        yield c
    reset_engine_for_tests()
