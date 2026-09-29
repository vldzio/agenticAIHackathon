"""Schemas for everything the LLM (or the mock) must return. They double as the JSON schema given to Gemini."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field

ExperienceLevel = Literal["Never Exercised", "Beginner", "Some Experience", "Advanced"]
Severity = Literal["none", "mild", "moderate", "severe"]
Intensity = Literal["Light", "Moderate", "Vigorous"]
Weekday = Literal["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def _to_str(value: object) -> object:
    return str(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else value


LooseStr = Annotated[str, BeforeValidator(_to_str)]


class _Base(BaseModel):
    model_config = ConfigDict(extra="ignore")


# --- input normalisation -----------------------------------------------------------------
class NormalizedExperience(_Base):
    experience_level: ExperienceLevel
    years_active: float = Field(ge=0, le=80)
    activity_description: str = ""


class NormalizedHealth(_Base):
    conditions: list[str] = Field(default_factory=list, max_length=15)
    severity_assessment: Severity = "none"
    exercise_limitations: list[str] = Field(default_factory=list, max_length=15)
    cleared_for_exercise: bool = True


class NormalizedSchedule(_Base):
    estimated_hours_per_week: float = Field(ge=0, le=40)
    preferred_days: list[Weekday] = Field(default_factory=list)
    preferred_times: list[str] = Field(default_factory=list)
    schedule_constraints: list[str] = Field(default_factory=list)


class NormalizedInputs(_Base):
    experience: NormalizedExperience
    health: NormalizedHealth
    schedule: NormalizedSchedule


# --- workout -----------------------------------------------------------------------------
class Exercise(_Base):
    exercise_name: str = Field(min_length=1, max_length=120)
    sets: int = Field(ge=1, le=10)
    reps: LooseStr = Field(min_length=1, max_length=40)
    rest_period: LooseStr = "60 sec"
    notes: str | None = None


class WorkoutDay(_Base):
    day: Weekday
    focus: str = Field(default="", max_length=80)
    exercises: list[Exercise] = Field(min_length=1, max_length=14)


class WorkoutPlan(_Base):
    weekly_schedule: list[WorkoutDay] = Field(min_length=1, max_length=7)
    workout_intensity_level: Intensity
    workout_frequency_per_week: int = Field(ge=1, le=7)
    workout_duration_per_session: int = Field(ge=10, le=180)
    workout_progression_timeline: str = ""
    workout_safety_notes: list[str] = Field(default_factory=list)
    workout_equipment_needed: list[str] = Field(default_factory=list)


# --- nutrition ---------------------------------------------------------------------------
class Meal(_Base):
    meal_name: str
    foods: list[str] = Field(min_length=1)
    protein_g: float = Field(ge=0, le=300)
    carbs_g: float = Field(ge=0, le=600)
    fat_g: float = Field(ge=0, le=300)
    calories: float = Field(ge=0, le=3000)


class NutritionMeals(_Base):
    """What the LLM produces; calorie and macro targets are computed deterministically elsewhere."""

    meal_suggestions: list[Meal] = Field(min_length=1, max_length=6)
    hydration_recommendation: str
    nutrition_timing_guidance: str


class MacroTargets(_Base):
    protein_g: int
    carbs_g: int
    fat_g: int


class NutritionPlan(_Base):
    maintenance_calories: int
    daily_calorie_target: int
    macro_targets: MacroTargets
    meal_suggestions: list[Meal] = Field(default_factory=list)
    hydration_recommendation: str = ""
    nutrition_timing_guidance: str = ""
    meal_totals: dict[str, float] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)


# --- recovery ----------------------------------------------------------------------------
class SleepRecommendations(_Base):
    hours_per_night: float = Field(ge=5, le=12)
    sleep_quality_tips: list[str] = Field(default_factory=list)


class ScheduleIntegration(_Base):
    best_days: list[str] = Field(default_factory=list)
    best_times: list[str] = Field(default_factory=list)
    weekly_schedule_tips: str = ""


class RecoveryPlan(_Base):
    sleep_recommendations: SleepRecommendations
    rest_day_activities: list[str] = Field(default_factory=list)
    mobility_work: list[str] = Field(default_factory=list)
    stress_management_techniques: list[str] = Field(default_factory=list)
    recovery_techniques: list[str] = Field(default_factory=list)
    deload_strategy: str = ""
    schedule_integration: ScheduleIntegration
    time_management_tips: list[str] = Field(default_factory=list)
    habit_formation_strategies: list[str] = Field(default_factory=list)
    adherence_tips: list[str] = Field(default_factory=list)
