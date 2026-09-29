"""Deterministic calorie / macro targets. The LLM is only asked for meals that fit these numbers."""

from __future__ import annotations

from typing import Any

CALORIE_FLOOR = {"Male": 1500, "Female": 1200, "Other": 1350}


def activity_multiplier(sessions_per_week: int) -> float:
    if sessions_per_week <= 1:
        return 1.2
    if sessions_per_week <= 3:
        return 1.375
    if sessions_per_week <= 5:
        return 1.55
    return 1.725


def bmr_mifflin_st_jeor(age: int, weight_kg: float, height_cm: float, gender: str) -> float:
    base = 10 * weight_kg + 6.25 * height_cm - 5 * age
    return base + {"Male": 5, "Female": -161}.get(gender, -78)


def calorie_target(maintenance: int, goal: str, gender: str, bmi: float) -> tuple[int, list[str]]:
    notes: list[str] = []
    goal_l = goal.lower()
    if "weight loss" in goal_l:
        if bmi < 18.5:
            target = maintenance
            notes.append("Weight-loss deficit not applied because BMI is in the underweight range.")
        else:
            target = maintenance - 300
    elif "muscle" in goal_l:
        target = maintenance + 250
    elif "endurance" in goal_l or "cardio" in goal_l:
        target = maintenance + 150
    else:
        target = maintenance
    floor = CALORIE_FLOOR.get(gender, 1350)
    if target < floor:
        notes.append(f"Calorie target raised to the {floor} kcal safety floor.")
        target = floor
    return int(target), notes


def macro_targets(weight_kg: float, calories: int, goal: str) -> dict[str, int]:
    goal_l = goal.lower()
    protein_per_kg = 2.0 if "muscle" in goal_l else 1.8 if "weight loss" in goal_l else 1.6
    protein = round(weight_kg * protein_per_kg)
    fat = round(weight_kg * 0.8)
    carbs = round((calories - protein * 4 - fat * 9) / 4)
    if carbs < round(0.2 * calories / 4):  # very heavy users / low calories: rebalance to a sane split
        fat = round(0.28 * calories / 9)
        protein = round(0.27 * calories / 4)
        carbs = round((calories - protein * 4 - fat * 9) / 4)
    return {"protein_g": int(protein), "carbs_g": int(carbs), "fat_g": int(fat)}


def build_targets(
    *, age: int, weight_kg: float, height_cm: float, gender: str, goal: str, bmi: float, sessions_per_week: int
) -> dict[str, Any]:
    bmr = bmr_mifflin_st_jeor(age, weight_kg, height_cm, gender)
    maintenance = round(bmr * activity_multiplier(sessions_per_week))
    target, notes = calorie_target(maintenance, goal, gender, bmi)
    return {
        "maintenance_calories": maintenance,
        "daily_calorie_target": target,
        "macro_targets": macro_targets(weight_kg, target, goal),
        "notes": notes,
    }
