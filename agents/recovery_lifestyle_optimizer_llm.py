from typing import Dict, Any

class RecoveryLifestyleOptimizerLLMAgent:
    """Generate recovery and lifestyle integration plans using LLM."""

    def __init__(self, client):
        """Initialize with LLM client."""

        if client is None:
          raise ValueError("LLM client cannot be None")

        self.client = client

    def generate_recovery_lifestyle_plan(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """Generate recovery and lifestyle integration plan."""

        age = profile.get("age")
        fitness_level = profile.get("fitness_level_class")
        injury_risk = profile.get("injury_risk_class")
        health_conditions = profile.get("health_conditions")
        goal = profile.get("fitness_goal")
        workout_frequency = profile.get("workout_frequency_per_week")
        available_hours = profile.get("available_hours_per_week")

        preferred_days = profile.get("preferred_days", [])
        preferred_times = profile.get("preferred_times", [])

        prompt = f"""
          You are an expert sports recovery and lifestyle optimization coach.
          Generate a recovery and lifestyle integration plan in VALID JSON.

          User Profile
          ------------
          Age: {age}
          Fitness Level: {fitness_level}
          Injury Risk: {injury_risk}
          Health Conditions: {health_conditions}
          Fitness Goal: {goal}
          Workout Frequency Per Week: {workout_frequency}
          Available Hours Per Week: {available_hours}

          Schedule Preferences
          --------------------
          Preferred Workout Days: {preferred_days}
          Preferred Workout Times: {preferred_times}

          Create recommendations covering:

            1. Sleep recommendations
              - hours_per_night
              - sleep_quality_tips[]

            2. Rest day activities
              - active recovery suggestions

            3. Mobility work
              - stretching and mobility routines

            4. Stress management techniques

            5. Recovery techniques
              - foam rolling
              - massage
              - contrast showers 
              - breathing exercises

            6. Deoad strategy
              - when to reduce training intensity
              - how to deload safely

            7. Schedule integration
              - best_days[]
              - best_times[]
              - weekly_schedule_tips

            8. Time management tips for available hours

            9. Habit formation strategies

            10. Adherence tips
              - staying motivated
              - overcoming obstacles

          Return ONLY JSON in this format:

          {{
            "sleep_recommendations": {{
              "hours_per_night": number,
              "sleep_quality_tips": []
            }},
            "rest_day_activities": [],
            "mobility_work": [],
            "stress_management_techniques": [],
            "recovery_techniques": [],
            "deload_strategy": "",
            "schedule_integration": {{
              "best_days": [],
              "best_times": [],
              "weekly_schedule_tips": ""
            }},
            "time_management_tips": [],
            "habit_formation_strategies": [],
            "adherence_tips": [] 
          }}
          """

        required_fields = [
          "sleep_recommendations",
          "rest_day_activities",
          "mobility_work",
          "stress_management_techniques",
          "recovery_techniques",
          "deload_strategy",
          "schedule_integration",
          "time_management_tips",
          "habit_formation_strategies",
          "adherence_tips"
        ]

        result = self.client.generate_structured_json(
          prompt=prompt,
          required_fields=required_fields
        )

        return result