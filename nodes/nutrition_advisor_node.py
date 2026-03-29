from typing import Any, Dict

from agents.nutrition_plan_generator_llm import NutritionPlanGeneratorLLMAgent
from state import FitnessAssessmentState


def _activity_multiplier(workout_frequency_per_week: int) -> float:
    if workout_frequency_per_week <= 1:
        return 1.2
    if workout_frequency_per_week <= 3:
        return 1.375
    if workout_frequency_per_week <= 5:
        return 1.55
    return 1.725


def _calculate_bmr(age: int, weight_kg: float, height_cm: float, gender: str) -> float:
    gender_normalized = str(gender or "").strip().lower()
    if gender_normalized == "male":
        return 88.362 + (13.397 * weight_kg) + (4.799 * height_cm) - (5.677 * age)
    if gender_normalized == "female":
        return 447.593 + (9.247 * weight_kg) + (3.098 * height_cm) - (4.330 * age)
    return 10 * weight_kg + 6.25 * height_cm - 5 * age + 5


def _calculate_daily_calorie_target(maintenance_calories: int, fitness_goal: str) -> int:
    goal = str(fitness_goal or "").strip().lower()
    if "weight loss" in goal:
        return max(1200, maintenance_calories - 300)
    if "muscle" in goal:
        return maintenance_calories + 250
    if "endurance" in goal or "cardio" in goal:
        return maintenance_calories + 150
    return maintenance_calories


def _calculate_macro_targets(weight_kg: float, daily_calorie_target: int, fitness_goal: str) -> Dict[str, int]:
    goal = str(fitness_goal or "").strip().lower()
    protein_per_kg = 2.0 if "muscle" in goal else 1.8 if "weight loss" in goal else 1.6
    fat_per_kg = 0.8

    protein_g = round(weight_kg * protein_per_kg)
    fat_g = round(weight_kg * fat_per_kg)
    remaining_calories = daily_calorie_target - ((protein_g * 4) + (fat_g * 9))
    carbs_g = max(0, round(remaining_calories / 4))

    return {
        "protein_g": protein_g,
        "carbs_g": carbs_g,
        "fat_g": fat_g,
    }


def nutrition_advisor_node(state: FitnessAssessmentState, client) -> Dict[str, Any]:
    try:
        age = int(state.get("age"))
        weight_kg = float(state.get("weight_kg"))
        height_cm = float(state.get("height_cm"))
        gender = state.get("gender")
        fitness_goal = state.get("fitness_goal")
        workout_frequency = int(state.get("workout_frequency_per_week") or 3)

        bmr = _calculate_bmr(age=age, weight_kg=weight_kg, height_cm=height_cm, gender=gender)
        maintenance_calories = round(bmr * _activity_multiplier(workout_frequency))
        daily_calorie_target = _calculate_daily_calorie_target(maintenance_calories, fitness_goal)
        macro_targets = _calculate_macro_targets(weight_kg, daily_calorie_target, fitness_goal)

        nutrition_plan = NutritionPlanGeneratorLLMAgent(client=client).generate_nutrition_plan(
            {
                "age": age,
                "weight_kg": weight_kg,
                "height_cm": height_cm,
                "gender": gender,
                "fitness_goal": fitness_goal,
                "fitness_level_class": state.get("fitness_level_class"),
                "bmi": state.get("bmi"),
                "workout_frequency_per_week": workout_frequency,
                "maintenance_calories": maintenance_calories,
                "daily_calorie_target": daily_calorie_target,
                "macro_targets": macro_targets,
            }
        )
        nutrition_plan["maintenance_calories"] = maintenance_calories
        nutrition_plan["daily_calorie_target"] = daily_calorie_target
        nutrition_plan["macro_targets"] = macro_targets
        return {
            "nutrition_plan": nutrition_plan,
            "daily_calorie_target": daily_calorie_target,
            "macro_targets": macro_targets,
            "meal_suggestions": nutrition_plan.get("meal_suggestions", []),
            "hydration_recommendation": nutrition_plan.get("hydration_recommendation"),
            "nutrition_timing_guidance": nutrition_plan.get("nutrition_timing_guidance"),
            "nutrition_analysis_complete": True,
        }
    except Exception as exc:
        print("Nutrition advisor error:", str(exc))
        return {
            "nutrition_plan": {},
            "daily_calorie_target": None,
            "macro_targets": {},
            "meal_suggestions": [],
            "hydration_recommendation": None,
            "nutrition_timing_guidance": None,
            "nutrition_analysis_complete": False,
            "error_messages": [str(exc)],
        }
