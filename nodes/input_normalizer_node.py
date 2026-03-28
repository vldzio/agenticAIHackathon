from typing import Any, Dict

from agents.input_normalizer_llm import InputNormalizerLLMAgent
from state import FitnessAssessmentState


def input_normalizer_node(state: FitnessAssessmentState, client) -> Dict[str, Any]:
    try:
        response = InputNormalizerLLMAgent(client=client).normalize_inputs(
            fitness_experience=state.get("fitness_experience", ""),
            health_conditions=state.get("health_conditions", ""),
            available_hours_per_week=state.get("available_hours_per_week", ""),
        )
        return {
            "normalized_fitness_experience": response.get("normalized_fitness_experience", {}),
            "normalized_health_conditions": response.get("normalized_health_conditions", {}),
            "normalized_schedule": response.get("normalized_schedule", {}),
        }
    except Exception as exc:
        print("Input normalization error:", str(exc))
        return {
            "normalized_fitness_experience": {},
            "normalized_health_conditions": {},
            "normalized_schedule": {},
            "error_messages": [str(exc)],
        }
