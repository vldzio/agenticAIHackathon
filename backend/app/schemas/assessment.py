from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.llm import NormalizedInputs, NutritionPlan, RecoveryPlan, WorkoutPlan
from app.schemas.profile import Mode, ProfileIn

SectionStatus = Literal["ok", "partial", "failed", "skipped"]
OverallStatus = Literal["complete", "partial", "failed"]


class NodeError(BaseModel):
    node: str
    code: str
    message: str
    retryable: bool = False


class Driver(BaseModel):
    feature: str
    value: Any
    effect_pct_points: float = Field(description="Change in the predicted class's probability vs a baseline profile")


class FitnessResult(BaseModel):
    level: str
    confidence: float = Field(description="Probability of the predicted class, in percent (0-100).")
    probabilities: dict[str, float] = Field(description="Probability of each class as a fraction (0-1); they sum to 1.")
    drivers: list[Driver] = []
    notes: list[str] = []


class InjuryResult(BaseModel):
    risk: str
    confidence: float = Field(description="Probability of the predicted class, in percent (0-100).")
    probabilities: dict[str, float] = Field(description="Probability of each class as a fraction (0-1); they sum to 1.")
    risk_factors: list[str] = []
    drivers: list[Driver] = []
    notes: list[str] = []


class SafetyResult(BaseModel):
    level: Literal["standard", "conservative", "clinician_first"]
    requires_clearance: bool
    max_intensity: str
    max_sessions_per_week: int
    reasons: list[str] = []
    constraints: list[str] = []
    disclaimer: str


class Metrics(BaseModel):
    bmi: float
    bmi_category: str
    age_category: str


class ProgressContext(BaseModel):
    weeks_on_plan: float = 0
    sessions_last_28_days: int = 0
    planned_sessions_per_week: int = 0
    adherence_pct: float | None = None
    average_rpe: float | None = None
    latest_weight_kg: float | None = None
    weight_change_kg: float | None = None
    deload_due: bool = False
    notes: list[str] = []


class Assessment(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    parent_id: str | None = None
    mode: Mode
    simulated: bool = Field(description="True when produced by the mock generator rather than a live model")
    status: OverallStatus
    profile: ProfileIn
    metrics: Metrics | None = None
    normalized: NormalizedInputs | None = None
    fitness: FitnessResult | None = None
    injury: InjuryResult | None = None
    safety: SafetyResult | None = None
    workout: WorkoutPlan | None = None
    nutrition: NutritionPlan | None = None
    recovery: RecoveryPlan | None = None
    sections: dict[str, SectionStatus] = {}
    errors: list[NodeError] = []
    warnings: list[str] = []
    progress_context: ProgressContext | None = None


class AssessmentSummary(BaseModel):
    id: str
    created_at: datetime
    parent_id: str | None
    mode: Mode
    simulated: bool
    status: OverallStatus
    user_name: str | None
    fitness_goal: str
    fitness_level: str | None
    injury_risk: str | None
    safety_level: str | None
    daily_calorie_target: int | None
    sessions_per_week: int | None
