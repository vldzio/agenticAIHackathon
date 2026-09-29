import json
import shutil

import pytest

from app.domain.profile_metrics import EXPERIENCE_LEVELS, FITNESS_CLASSES, INJURY_CLASSES
from app.ml.registry import ModelLoadError, ModelRegistry, get_registry

FIT = dict(age=30, bmi=24, weight_kg=70, hours=4, gender="Male", goal="Weight Loss", experience="Beginner")
INJ = dict(
    age=40,
    bmi=25,
    has_health_conditions=0,
    previous_injury=0,
    hours=4,
    gender="Male",
    experience="Beginner",
    fitness_level="Beginner",
)


def test_metadata_records_versions_and_hashes():
    meta = get_registry().metadata
    assert {"scikit_learn", "numpy", "pandas"} <= set(meta["environment"])
    for m in meta["models"].values():
        assert len(m["artifact_sha256"]) == 64
        assert "Activity_Score" not in m["features"]["numeric"] + m["features"]["categorical"]
        assert "Flexibility_Score" not in m["features"]["numeric"]


def test_reported_metrics_meet_thresholds():
    meta = get_registry().metadata["models"]
    assert meta["fitness_level"]["evaluation"]["accuracy"] >= 0.70
    assert meta["injury_risk"]["evaluation"]["accuracy"] >= 0.60
    assert meta["fitness_level"]["evaluation"]["within_one_class_accuracy"] >= 0.95


def test_integrity_check_rejects_tampered_artifact(tmp_path):
    src = get_registry().artifact_dir
    for f in src.iterdir():
        shutil.copy(f, tmp_path / f.name)
    (tmp_path / "injury_risk.joblib").write_bytes(b"not a model")
    with pytest.raises(ModelLoadError, match="Integrity"):
        ModelRegistry(tmp_path).get("injury_risk")


def test_missing_metadata(tmp_path):
    with pytest.raises(ModelLoadError):
        ModelRegistry(tmp_path).get("fitness_level")


def test_predictions_are_valid_and_normalised(predictors):
    fit, inj = predictors
    f = fit.predict(FIT)
    assert f.label in FITNESS_CLASSES and abs(sum(f.probabilities.values()) - 1) < 1e-6
    assert 0 < f.confidence <= 100 and len(f.drivers) == 3
    i = inj.predict(INJ)
    assert i.label in INJURY_CLASSES and abs(sum(i.probabilities.values()) - 1) < 1e-6


@pytest.mark.parametrize("hours", [1, 3, 8, 15])
@pytest.mark.parametrize("experience", EXPERIENCE_LEVELS)
def test_persona_guardrail_never_exceeds_stated_history(predictors, experience, hours):
    ceiling = {"Never Exercised": 0, "Beginner": 1, "Some Experience": 2, "Advanced": 3}[experience]
    label = predictors[0].predict({**FIT, "experience": experience, "hours": hours, "age": 25}).label
    assert FITNESS_CLASSES.index(label) <= ceiling


def test_low_hours_cannot_be_athlete(predictors):
    assert predictors[0].predict({**FIT, "experience": "Advanced", "hours": 1.5, "age": 22}).label != "Athlete"


def test_out_of_range_inputs_are_flagged(predictors):
    p = predictors[0].predict({**FIT, "age": 85})
    assert any("training range" in n for n in p.notes)


def test_risk_direction_is_sensible(predictors):
    low = predictors[1].predict(
        {
            **INJ,
            "age": 25,
            "bmi": 22,
            "previous_injury": 0,
            "has_health_conditions": 0,
            "fitness_level": "Advanced",
            "experience": "Advanced",
        }
    )
    high = predictors[1].predict(
        {
            **INJ,
            "age": 62,
            "bmi": 33,
            "previous_injury": 1,
            "has_health_conditions": 1,
            "fitness_level": "Beginner",
            "experience": "Never Exercised",
        }
    )
    assert INJURY_CLASSES.index(high.label) > INJURY_CLASSES.index(low.label)


def test_unknown_experience_rejected(predictors):
    with pytest.raises(ValueError):
        predictors[0].predict({**FIT, "experience": "Wizard"})


def test_evaluation_matches_stored_metrics():
    from app.services import evaluation_service

    live = evaluation_service.evaluate(force=True)
    stored = json.loads((get_registry().artifact_dir / "metadata.json").read_text())["models"]
    for name in ("fitness_level", "injury_risk"):
        assert live["models"][name]["accuracy"] == pytest.approx(stored[name]["evaluation"]["accuracy"], abs=0.01)
        assert len(live["models"][name]["confusion_matrix"]) == 4
