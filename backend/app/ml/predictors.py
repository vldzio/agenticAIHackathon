"""Fitness-level and injury-risk predictors (calibrated random forests + rule-based guardrails)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from app.domain.profile_metrics import EXPERIENCE_LEVELS, FITNESS_CLASSES
from app.ml.features import FITNESS_SPEC, INJURY_SPEC, ModelSpec
from app.ml.registry import LoadedModel, ModelRegistry, get_registry

# Rule-based sanity ceilings: a fitness class may not exceed the level implied by the user's stated
# training history (Never Exercised -> Beginner, Beginner -> Intermediate, Some Experience -> Advanced).
# In the bundled (synthetic) data ~35% of "Beginner" and ~20% of "Never Exercised" rows carry higher labels,
# and age dominates the label; without this the app tells self-declared beginners they are Advanced.
EXPERIENCE_CEILING = {
    "Never Exercised": "Beginner",
    "Beginner": "Intermediate",
    "Some Experience": "Advanced",
    "Advanced": "Athlete",
}
LOW_HOURS_CEILING = ("Advanced", 2.0)  # <= 2 h/week can't be "Athlete"


@dataclass
class Prediction:
    label: str
    index: int
    confidence: float  # percent
    probabilities: dict[str, float]
    drivers: list[dict[str, Any]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def _ood_warnings(row: dict[str, Any], meta: dict[str, Any]) -> list[str]:
    notes = []
    for col, rng in meta.get("training_ranges", {}).items():
        value = row.get(col)
        if isinstance(value, (int, float)) and not (rng["min"] - 1e-9 <= value <= rng["max"] + 1e-9):
            notes.append(
                f"{col.replace('_', ' ')} ({value:g}) is outside the model's training range "
                f"({rng['min']:g}-{rng['max']:g}); treat this prediction as an extrapolation."
            )
    return notes


def _probabilities_batch(loaded: LoadedModel, spec: ModelSpec, rows: list[dict[str, Any]]) -> np.ndarray:
    """Class probabilities (columns in canonical ordinal order) for several rows in one model call."""
    proba = loaded.pipeline.predict_proba(pd.DataFrame(rows)[spec.features])
    classes = list(loaded.pipeline.classes_)
    return proba[:, [classes.index(c) for c in spec.classes]]


def _probabilities(loaded: LoadedModel, spec: ModelSpec, row: dict[str, Any]) -> np.ndarray:
    return _probabilities_batch(loaded, spec, [row])[0]


def explain(loaded: LoadedModel, spec: ModelSpec, row: dict[str, Any], class_idx: int, top: int = 3) -> list[dict[str, Any]]:
    """Occlusion-based local explanation: how much does each input move the predicted class's probability
    compared with the training-set baseline (median / mode)? Positive = pushes towards the prediction."""
    baseline = loaded.meta["baseline"]
    rows = [row] + [{**row, feature: baseline[feature]} for feature in spec.features]
    p = _probabilities_batch(loaded, spec, rows)[:, class_idx]
    drivers = [
        {"feature": f, "value": row[f], "effect_pct_points": round(float(p[0] - p[i + 1]) * 100, 1)}
        for i, f in enumerate(spec.features)
    ]
    drivers.sort(key=lambda d: -abs(d["effect_pct_points"]))
    return drivers[:top]


class FitnessPredictor:
    def __init__(self, registry: ModelRegistry | None = None) -> None:
        self.registry = registry or get_registry()

    def predict(self, profile: dict[str, Any]) -> Prediction:
        loaded = self.registry.get(FITNESS_SPEC.name)
        experience = profile["experience"]
        if experience not in EXPERIENCE_LEVELS:
            raise ValueError(f"Unknown experience level: {experience}")
        hours = float(profile["hours"])
        row = {
            "Age": float(profile["age"]),
            "BMI": float(profile["bmi"]),
            "Weight_KG": float(profile["weight_kg"]),
            "Available_Hours_Per_Week": hours,
            "Gender": profile["gender"],
            "Fitness_Experience": experience,
            "Fitness_Goal": profile["goal"],
        }
        proba = _probabilities(loaded, FITNESS_SPEC, row)
        notes = _ood_warnings(row, loaded.meta)

        ceiling = FITNESS_CLASSES.index(EXPERIENCE_CEILING[experience])
        if hours <= LOW_HOURS_CEILING[1]:
            ceiling = min(ceiling, FITNESS_CLASSES.index(LOW_HOURS_CEILING[0]))
        raw_idx = int(np.argmax(proba))
        if raw_idx > ceiling:
            masked = proba.copy()
            masked[ceiling + 1 :] = 0.0
            proba = masked / masked.sum()
            notes.append(
                f"Model output '{FITNESS_CLASSES[raw_idx]}' was capped at '{FITNESS_CLASSES[ceiling]}' "
                "because it is inconsistent with the stated training history."
            )
        idx = int(np.argmax(proba))
        return Prediction(
            label=FITNESS_CLASSES[idx],
            index=idx,
            confidence=float(proba[idx] * 100),
            probabilities={c: float(p) for c, p in zip(FITNESS_SPEC.classes, proba, strict=True)},
            drivers=explain(loaded, FITNESS_SPEC, row, idx),
            notes=notes,
        )


class InjuryPredictor:
    def __init__(self, registry: ModelRegistry | None = None) -> None:
        self.registry = registry or get_registry()

    def predict(self, profile: dict[str, Any]) -> Prediction:
        loaded = self.registry.get(INJURY_SPEC.name)
        row = {
            "Age": float(profile["age"]),
            "BMI": float(profile["bmi"]),
            "Has_Health_Conditions": int(bool(profile["has_health_conditions"])),
            "Previous_Injury": int(bool(profile["previous_injury"])),
            "Training_Frequency_Hours": float(np.clip(profile["hours"], 1, 20)),
            "Gender": profile["gender"],
            "Fitness_Level": profile["fitness_level"],
            "Fitness_Experience": profile["experience"],
        }
        proba = _probabilities(loaded, INJURY_SPEC, row)
        idx = int(np.argmax(proba))
        return Prediction(
            label=INJURY_SPEC.classes[idx],
            index=idx,
            confidence=float(proba[idx] * 100),
            probabilities={c: float(p) for c, p in zip(INJURY_SPEC.classes, proba, strict=True)},
            drivers=explain(loaded, INJURY_SPEC, row, idx),
            notes=_ood_warnings(row, loaded.meta),
        )
