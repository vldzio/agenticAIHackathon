"""Checks on the two shipped classifiers: honest inputs, correct labels, and a quality floor.

Everything here runs the real pickled models on the bundled evaluation CSVs.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from streamlit.testing.v1 import AppTest  # noqa: E402

from agents.fitness_scorer_ml import FitnessScorerMLAgent  # noqa: E402
from agents.injury_assessor_ml import InjuryAssessorMLAgent  # noqa: E402
from ml.evaluation.evaluate_models import evaluate_all_models  # noqa: E402

EVAL_DIR = ROOT / "data" / "evaluation_dataset"
# Columns the app cannot measure; a model that needs them looks good offline and fails in the app.
NOT_COLLECTED = {"Activity_Score", "Flexibility_Score", "Strength_Imbalance_Score", "Overtraining_Risk_Score"}


@pytest.fixture(scope="module")
def results():
    return evaluate_all_models(str(ROOT))


@pytest.fixture(scope="module")
def fitness():
    return FitnessScorerMLAgent()


@pytest.fixture(scope="module")
def injury():
    return InjuryAssessorMLAgent()


def test_models_use_only_inputs_the_app_collects(fitness, injury):
    assert not NOT_COLLECTED & set(fitness.encoder["feature_columns"])
    assert not NOT_COLLECTED & set(injury.feature_columns)


def test_held_out_quality_floor(results):
    fit, inj = results["fitness_evaluation"], results["injury_evaluation"]
    assert "error" not in fit and "error" not in inj
    assert fit["eval_accuracy"] > 0.79 and fit["macro_f1"] > 0.78
    assert inj["eval_accuracy"] > 0.66 and inj["macro_f1"] > 0.66
    for result in (fit, inj):
        assert result["eval_accuracy"] > result["majority_baseline_accuracy"] + 0.3
        assert result["within_one_class_accuracy"] > 0.99  # mistakes are never more than one class off
        assert result["quadratic_weighted_kappa"] > 0.8
        assert result["accuracy_ci95"][0] <= result["eval_accuracy"] <= result["accuracy_ci95"][1]
        assert sum(map(sum, result["confusion_matrix"])) == result["total_samples"] == 8000


def test_agents_match_the_offline_evaluation(results, fitness, injury):
    """The app's own prediction path must score like the offline report (it once scored 17%)."""
    rows = pd.read_csv(EVAL_DIR / "fitness_level_evaluation.csv").sample(400, random_state=0)
    hits = [
        fitness.predict_fitness_level(
            {"age": r.Age, "bmi": r.BMI, "weight_kg": r.Weight_KG, "gender": r.Gender, "fitness_goal": r.Fitness_Goal,
             "available_hours_per_week": r.Available_Hours_Per_Week, "fitness_experience_level": r.Fitness_Experience}
        )["fitness_level_class"] == r.Fitness_Level_Class
        for r in rows.itertuples()
    ]
    assert abs(sum(hits) / len(hits) - results["fitness_evaluation"]["eval_accuracy"]) < 0.06

    rows = pd.read_csv(EVAL_DIR / "injury_risk_evaluation.csv").sample(400, random_state=0)
    hits = [
        injury.predict_injury_risk(
            {"age": r.Age, "bmi": r.BMI, "gender": r.Gender,
             "fitness_experience_level": r.Fitness_Experience, "available_hours_per_week": r.Training_Frequency_Hours,
             "health_conditions": "asthma" if r.Has_Health_Conditions else "None",
             "injury_history": "knee" if r.Previous_Injury else ""}
        )["injury_risk_class"] == r.Injury_Risk_Class
        for r in rows.itertuples()
    ]
    assert abs(sum(hits) / len(hits) - results["injury_evaluation"]["eval_accuracy"]) < 0.06


def test_fitness_labels_follow_the_inputs(fitness):
    base = {"age": 30, "bmi": 24, "weight_kg": 70, "gender": "Male", "fitness_goal": "Weight Loss"}
    low = fitness.predict_fitness_level({**base, "available_hours_per_week": 1, "fitness_experience_level": "Never Exercised"})
    high = fitness.predict_fitness_level(
        {**base, "available_hours_per_week": 14, "fitness_experience_level": "Advanced", "fitness_years_active": 8}
    )
    assert (low["fitness_level_class"], low["fitness_level_score"]) == ("Beginner", 0.0)
    assert (high["fitness_level_class"], high["fitness_level_score"]) == ("Athlete", 3.0)


def test_injury_risk_follows_the_health_answers(injury):
    base = {"age": 30, "bmi": 24, "gender": "Male", "fitness_experience_level": "Some Experience", "available_hours_per_week": 5}
    score = lambda **extra: injury.predict_injury_risk({**base, **extra})["injury_risk_score"]  # noqa: E731

    assert injury._health_flags({"health_conditions": "None"}) == (0, 0)
    assert injury._health_flags({"health_conditions": "No injuries or conditions"}) == (0, 0)
    assert injury._health_flags({"health_conditions": "Asthma"}) == (1, 0)
    assert injury._health_flags({"health_conditions": "Old knee injury"}) == (0, 1)
    assert injury._health_flags({"health_conditions": "Asthma, torn ACL in 2020"}) == (1, 1)
    # the LLM normalizer's list wins over the raw text (its key is spelled "condtions" in the prompt)
    assert injury._health_flags({"health_conditions": "I feel great", "normalized_health_conditions": {"condtions": []}}) == (0, 0)

    healthy, one, both = score(health_conditions="None"), score(health_conditions="Asthma"), score(health_conditions="Asthma, torn ACL")
    assert healthy < one < both == 3  # 3 = Very High Risk


def test_model_evaluation_button_renders(monkeypatch):
    monkeypatch.setenv("LLM_BASE_URL", "http://127.0.0.1:9/v1")
    monkeypatch.setenv("LLM_API_KEY", "unused")
    at = AppTest.from_file(str(ROOT / "main.py"), default_timeout=120).run()
    next(b for b in at.sidebar.button if b.label == "Run Model Evaluation").click().run()
    assert not at.exception
    labels = [m.label for m in at.metric]
    assert labels.count("Accuracy") == 2 and labels.count("Within one class") == 2
