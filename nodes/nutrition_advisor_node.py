from typing import Any, Dict

from agents.nutrition_plan_generator_llm import NutritionPlanGeneratorLLMAgent
from state import FitnessAssessmentState


def nutrition_advisor_node(state: FitnessAssessmentState, client) -> Dict[str, Any]:
    try:
        nutrition_plan = NutritionPlanGeneratorLLMAgent(client=client).generate_nutrition_plan(
            {
                "age": state.get("age"),
                "weight_kg": state.get("weight_kg"),
                "height_cm": state.get("height_cm"),
                "gender": state.get("gender"),
                "fitness_goal": state.get("fitness_goal"),
                "fitness_level_class": state.get("fitness_level_class"),
                "bmi": state.get("bmi"),
                "workout_frequency_per_week": state.get("workout_frequency_per_week"),
            }
        )
        return {
            "nutrition_plan": nutrition_plan,
            "daily_calorie_target": nutrition_plan.get("daily_calorie_target"),
            "macro_targets": nutrition_plan.get("macro_targets", {}),
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
