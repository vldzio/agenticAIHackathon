"""Derived profile metrics. Used by BOTH serving and training so the two cannot drift."""

from __future__ import annotations

EXPERIENCE_LEVELS = ["Never Exercised", "Beginner", "Some Experience", "Advanced"]
FITNESS_CLASSES = ["Beginner", "Intermediate", "Advanced", "Athlete"]
INJURY_CLASSES = ["Low Risk", "Moderate Risk", "High Risk", "Very High Risk"]
GENDERS = ["Male", "Female", "Other"]
FITNESS_GOALS = ["Weight Loss", "Muscle Building", "Endurance/Cardio", "General Fitness"]


def calculate_bmi(weight_kg: float, height_cm: float) -> float:
    height_m = height_cm / 100.0
    return round(weight_kg / (height_m**2), 2)


def age_category(age: float) -> str:
    if age < 30:
        return "Young Adult"
    if age < 45:
        return "Adult"
    if age < 60:
        return "Middle Aged"
    return "Senior"


def bmi_category(bmi: float) -> str:
    if bmi < 18.5:
        return "Underweight"
    if bmi < 25:
        return "Normal"
    if bmi < 30:
        return "Overweight"
    return "Obese"


def hours_category(hours: float) -> str:
    if hours < 3:
        return "Minimal"
    if hours < 6:
        return "Moderate"
    if hours < 10:
        return "High"
    return "Athletic"


def experience_from_years(years: float | None, stated: str | None = None) -> str:
    """Map years of consistent training (preferred) or a stated label to a canonical level."""
    if years is not None:
        if years >= 5:
            return "Advanced"
        if years >= 1:
            return "Some Experience"
        if years > 0:
            return "Beginner"
        return "Never Exercised"  # an explicit "0 years" outweighs any self-description
    label = (stated or "").strip().lower()
    if label in {"advanced", "athlete", "expert"}:
        return "Advanced"
    if label in {"intermediate", "some experience"}:
        return "Some Experience"
    if label == "beginner":
        return "Beginner"
    return "Never Exercised"
