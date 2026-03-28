from typing import Any, Dict

from agents.form_parser_agent import FormParserAgent
from state import FitnessAssessmentState


def form_parser_node(state: FitnessAssessmentState, client=None) -> Dict[str, Any]:
    del client
    try:
        result = FormParserAgent().validate_and_parse(
            {
                "age": state.get("age"),
                "height_cm": state.get("height_cm"),
                "weight_kg": state.get("weight_kg"),
                "gender": state.get("gender"),
                "fitness_experience": state.get("fitness_experience"),
                "health_conditions": state.get("health_conditions"),
                "fitness_goal": state.get("fitness_goal"),
                "available_hours_per_week": state.get("available_hours_per_week"),
                "user_name": state.get("user_name"),
            }
        )
        return {
            "parsed_profile": result.get("parsed_profile") or {},
            "bmi": result.get("bmi"),
            "age_category": result.get("age_category"),
            "bmi_category": result.get("bmi_category"),
            "validation_errors": result.get("validation_errors", []),
            "parsing_complete": result.get("parsing_complete", False),
            "error_occurred": result.get("error_occurred", False),
        }
    except Exception as exc:
        return {
            "parsed_profile": {},
            "bmi": None,
            "age_category": None,
            "bmi_category": None,
            "validation_errors": [str(exc)],
            "parsing_complete": False,
            "error_occurred": True,
        }
