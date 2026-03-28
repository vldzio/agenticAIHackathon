from typing import Any, Dict

from agents.injury_assessor_ml import InjuryAssessorMLAgent
from state import FitnessAssessmentState


def injury_assessor_node(state: FitnessAssessmentState, client=None) -> Dict[str, Any]:
    del client
    try:
        user_profile = dict(state.get("parsed_profile") or {})
        user_profile.update(
            {
                "age": state.get("age"),
                "bmi": state.get("bmi"),
                "health_conditions": state.get("health_conditions"),
                "gender": state.get("gender"),
                "fitness_goal": state.get("fitness_goal"),
                "age_category": state.get("age_category"),
                "bmi_category": state.get("bmi_category"),
                "fitness_level_class": state.get("fitness_level_class", "Beginner"),
            }
        )
        experience_level = state.get("normalized_fitness_experience", {}).get("experience_level")
        if experience_level:
            user_profile["fitness_experience_level"] = experience_level.title()
        estimated_hours = state.get("normalized_schedule", {}).get("estimated_hours_per_week")
        user_profile["available_hours_per_week"] = estimated_hours if estimated_hours is not None else 3

        prediction = InjuryAssessorMLAgent().predict_injury_risk(user_profile)
        return {
            "injury_risk_score": prediction.get("injury_risk_score"),
            "injury_risk_class": prediction.get("injury_risk_class"),
            "injury_confidence": prediction.get("injury_confidence"),
            "injury_risk_factors": prediction.get("injury_risk_factors", []),
            "injury_assessment_complete": True,
        }
    except Exception as exc:
        return {
            "injury_risk_score": 0.0,
            "injury_risk_class": "Low Risk",
            "injury_confidence": 0.0,
            "injury_risk_factors": [],
            "injury_assessment_complete": False,
            "error_messages": [str(exc)],
        }
