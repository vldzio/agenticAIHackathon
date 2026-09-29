"""Single source of truth for model features (shared by training and serving).

Design notes (see docs/MODEL_CARD.md):
* `Activity_Score` was removed from the fitness model: in the bundled dataset it is banded by the
  label (a leak), and the app computed it with a different formula (train/serve skew).
* `Flexibility_Score` and `Strength_Imbalance_Score` were removed from the injury model: the app
  never measures them, so serving values were guesses. Only observable inputs are used.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.profile_metrics import (
    EXPERIENCE_LEVELS,
    FITNESS_CLASSES,
    FITNESS_GOALS,
    GENDERS,
    INJURY_CLASSES,
)


@dataclass(frozen=True)
class ModelSpec:
    name: str
    target: str
    classes: list[str]
    numeric: list[str]
    categorical: list[str]
    allowed: dict[str, list[str]]

    @property
    def features(self) -> list[str]:
        return [*self.numeric, *self.categorical]


FITNESS_SPEC = ModelSpec(
    name="fitness_level",
    target="Fitness_Level_Class",
    classes=FITNESS_CLASSES,
    numeric=["Age", "BMI", "Weight_KG", "Available_Hours_Per_Week"],
    categorical=["Gender", "Fitness_Experience", "Fitness_Goal"],
    allowed={
        "Gender": GENDERS,
        "Fitness_Experience": EXPERIENCE_LEVELS,
        "Fitness_Goal": FITNESS_GOALS,
    },
)

INJURY_SPEC = ModelSpec(
    name="injury_risk",
    target="Injury_Risk_Class",
    classes=INJURY_CLASSES,
    numeric=["Age", "BMI", "Has_Health_Conditions", "Previous_Injury", "Training_Frequency_Hours"],
    categorical=["Gender", "Fitness_Level", "Fitness_Experience"],
    allowed={
        "Gender": GENDERS,
        "Fitness_Level": FITNESS_CLASSES,
        "Fitness_Experience": EXPERIENCE_LEVELS,
    },
)

SPECS = {FITNESS_SPEC.name: FITNESS_SPEC, INJURY_SPEC.name: INJURY_SPEC}
