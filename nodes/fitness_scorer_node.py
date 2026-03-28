from typing import Any, Dict

from agents.fitness_scorer_ml import FitnessScorerMLAgent
from state import FitnessAssessmentState


def fitness_scorer_node(state: FitnessAssessmentState, client=None) -> Dict[str, Any]:
    del client
    try:
        user_profile = dict(state.get("parsed_profile") or {})
        user_profile.update(
            {
                "bmi": state.get("bmi"),
                "age": state.get("age"),
                "weight_kg": state.get("weight_kg"),
                "gender": state.get("gender"),
                "fitness_goal": state.get("fitness_goal"),
                "age_category": state.get("age_category"),
                "bmi_category": state.get("bmi_category"),
            }
        )
        experience_level = state.get("normalized_fitness_experience", {}).get("experience_level")
        if experience_level:
            user_profile["fitness_experience_level"] = experience_level.title()
        estimated_hours = state.get("normalized_schedule", {}).get("estimated_hours_per_week")
        user_profile["available_hours_per_week"] = estimated_hours if estimated_hours is not None else 3

        prediction = FitnessScorerMLAgent().predict_fitness_level(user_profile)
        return {
            "fitness_level_score": prediction.get("fitness_level_score"),
            "fitness_level_class": prediction.get("fitness_level_class"),
            "fitness_confidence": prediction.get("fitness_confidence"),
            "fitness_analysis_complete": True,
        }
    except Exception as exc:
        return {
            "fitness_level_score": 0.0,
            "fitness_level_class": "Beginner",
            "fitness_confidence": 0.0,
            "fitness_analysis_complete": False,
            "error_messages": [str(exc)],
        }
