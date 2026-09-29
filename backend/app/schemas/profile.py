from __future__ import annotations

import re
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

Gender = Literal["Male", "Female", "Other"]
FitnessGoal = Literal["Weight Loss", "Muscle Building", "Endurance/Cardio", "General Fitness"]
Mode = Literal["mock", "live"]

_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def _clean(value: str) -> str:
    return _CONTROL.sub("", value).strip()


class ProfileIn(BaseModel):
    """User profile as submitted by the frontend. Free-text fields are length-limited and sanitised."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    user_name: Annotated[str, StringConstraints(max_length=60)] | None = None
    age: int = Field(ge=18, le=100)
    height_cm: float = Field(ge=100, le=250)
    weight_kg: float = Field(ge=30, le=300)
    gender: Gender
    fitness_goal: FitnessGoal
    fitness_experience: str = Field(min_length=1, max_length=500, description="Free text, e.g. '2 years of gym training'")
    health_conditions: str = Field(default="None", min_length=1, max_length=500)
    available_hours_per_week: str = Field(
        min_length=1, max_length=300, description="Free text, e.g. '4-5 hours, weekday mornings'"
    )
    previous_injury: bool = False

    @field_validator("user_name", "fitness_experience", "health_conditions", "available_hours_per_week", mode="before")
    @classmethod
    def _sanitise(cls, value: object) -> object:
        return _clean(value) if isinstance(value, str) else value

    @field_validator("user_name")
    @classmethod
    def _empty_name(cls, value: str | None) -> str | None:
        return value or None


class AssessmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile: ProfileIn
    mode: Mode = "mock"
