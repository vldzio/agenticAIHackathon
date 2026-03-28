from typing import Dict, Any

class WorkoutPlanGeneratorLLMAgent:
    """Generate personalized workout plans using LLM."""

    def __init__(self, client):
        """Initialize with LLM client."""
        if client is None:
          raise ValueError("Provide valid LLM client")
        self.client=client

    def generate_workout_plan(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """Generate customized workout plan."""
        fitness_level_class = profile.get("fitness_level_class")
        injury_risk_class = profile.get("injury_risk_class")
        fitness_goal = profile.get("fitness_goal")
        available_hours_per_week = profile.get("available_hours_per_week") 
        health_conditions = profile.get("health_conditions")

        preferred_days = profile.get("preferred_days",[])
        preferred_times = profile.get("preferred_times",[])

        prompt = f"""
        You are a certified strength and conditioning coach.

        Generate a structured workout plan in VALID JSON.

        User Profile
        ------------
        Fitness Level: {fitness_level_class}
        Injury Risk Level: {injury_risk_class}
        Fitness Goal: {fitness_goal}
        Available Hours Per Week: {available_hours_per_week}
        Health Conditions: {health_conditions}

        Schedule Preferences
        --------------
        Preferred Days: {preferred_days}
        Preferred Times: {preferred_times}

        Workout Plan Requirements
        ------------------
            1. Weekly workout schedule.
        
        Format:
        {{day: [{{exercise_name, sets, reps, rest_period}}]}}

        Example:

        "Monday": [
          {{
            "exercise_name": "Push-ups",
            "sets": 3,
            "reps": 12,
            "rest_period": "60 sec"
          }}
        ]

            2.Workout intensity level
            Choose from: Light, Moderate, Vigorous

            3. Duration per session (minutes)

            4. Frequency per week (number)

            5. Workout progression timeline
            Example : 6 weeks or 12 weeks

            6. Safety notes considering:
            - injury risk
            - health conditions

            7. Equipment needed
            (empty list if bodyweight exercises only)

        Return ONLY JSON in this format:
        
        {{
          "weekly_schedule": {{}},
          "workout_intensity_level": "",
          "workout_frequency_per_week": number,
          "workout_duration_per_session": number,
          "workout_progression_timeline": "",
          "workout_safety_notes": [],
          "workout_equipment_needed": []
        }}
        """
        required_fields = [
          "weekly_schedule",
          "workout_intensity_level",
          "workout_frequency_per_week",
          "workout_duration_per_session",
          "workout_progression_timeline",
          "workout_safety_notes",
          "workout_equipment_needed"
        ]
        result = self.client.generate_structured_json(
          prompt = prompt,
          required_fields = required_fields
        )

        return result
