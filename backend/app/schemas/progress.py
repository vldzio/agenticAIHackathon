from __future__ import annotations

import datetime as dt
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ProgressLogIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["session", "weight"]
    logged_on: dt.date = Field(default_factory=dt.date.today)
    planned_day: str | None = Field(default=None, max_length=20)
    completed: bool = True
    duration_minutes: int | None = Field(default=None, ge=1, le=600)
    rpe: int | None = Field(default=None, ge=1, le=10, description="Rate of perceived exertion, 1-10")
    weight_kg: float | None = Field(default=None, ge=30, le=300)
    notes: str | None = Field(default=None, max_length=500)


class ProgressLogOut(ProgressLogIn):
    model_config = ConfigDict(from_attributes=True)

    id: int
    assessment_id: str


class WeekAdherence(BaseModel):
    week_start: dt.date
    sessions: int
    planned: int


class ProgressSummary(BaseModel):
    assessment_id: str
    planned_sessions_per_week: int
    sessions_last_28_days: int
    adherence_pct: float | None
    average_rpe: float | None
    latest_weight_kg: float | None
    weight_change_kg: float | None
    weeks_on_plan: float
    deload_due: bool
    weekly: list[WeekAdherence]
    weights: list[tuple[dt.date, float]]
    notes: list[str]
