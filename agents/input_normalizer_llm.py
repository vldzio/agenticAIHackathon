from typing import Dict, Any

class InputNormalizerLLMAgent:
    """Parse natural language inputs using LLM to extract structured information."""

    def __init__(self, client=None):
        """Initialize with LLM client."""
        if client is None:
          raise ValueError("LLM Client cannot be None")
        self.client = client

    def normalize_inputs(self, fitness_experience: str, health_conditions: str, available_hours_per_week: str) -> Dict[str, Any]:
        """Parse natural language inputs and extract structured normalized information."""
        prompt = f"""
        You are a fitness data normalization assisstant.

        Convert the following user inputs into structured JSON.

        USER INPUTS:

        fitness_experience:
        {fitness_experience}

        health_conditions:
        {health_conditions}

        available_hours_per_week:
        {available_hours_per_week}

        Return JSON with the following structure ONLY:

        {{
          "normalized_fitness_experience": {{
            "experience_level": "beginner | intermediate | advanced",
            "years_active": int,
            "activity_description": string
          }},
          "normalized_health_conditions":{{
            "condtions": [string],
            "severity_assessment": "none | mild | moderate | severe",
            "exercise_limitations": [string],
            "cleared_for_exercise": boolean
          }},
          "normalized_schedule": {{
            "estimated_hours_per_week": float,
            "preferred_days": [string],
            "preferred_times": [string],
            "schedule_constraints": [string]
          }}
        }}
        """

        required_fields = [
          "normalized_fitness_experience",
          "normalized_health_conditions",
          "normalized_schedule"
        ]

        result = self.client.generate_structured_json(prompt=prompt,required_fields=required_fields)
        return result
