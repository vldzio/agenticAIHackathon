from typing import Dict, Any

class NutritionPlanGeneratorLLMAgent:
    """Generate personalized nutrition plans using LLM."""

    def __init__(self, client):
        """Initialize with LLM client."""
        if client is None:
          raise ValueError("LLM client cannot be None")
        
        self.client = client

    def generate_nutrition_plan(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """Generate customized nutrition plan."""
        
        age = profile.get("age")
        weight = profile.get("weight_kg", profile.get("weight"))
        height = profile.get("height_cm", profile.get("height"))
        gender = profile.get("gender")
        goal = profile.get("fitness_goal")
        fitness_level = profile.get("fitness_level_class")
        bmi = profile.get("bmi")
        workout_frequency = profile.get("workout_frequency_per_week", 3)

        prompt = f"""

You are a professional sports nutritionist.


Generate a personalized nutrition plan in VALID JSON.


User Profile
------------
Age: {age}
Weight (kg): {weight}
Height (cm): {height}
Gender: {gender}
BMI: {bmi}
Fitness Goal: {goal}
Fitness Level: {fitness_level}
Workout Frequency per week: {workout_frequency}


Instructions
------------

1. User Harris-Benedict equation to estimate BMR.
2. Apply appropriate activity multiplier.
3. Calculate daily calorie target.

4. Provide macro targets:
   - protein_g
   - carbs_g
   - fat_g

5. Suggest 3 to 5 meals using Indian cuisine.

Each meal must contain:
- meal_name
- foods
- protein_g
- carbs_g
- fat_g
- calories

6. Provide hydration recommendation (daily water intake).

7. Provide pre and post workout nutrition timing guidance.

Return ONLY JSON in this format:

{{
  "daily_calorie_target": number,
  "macro_targets": {{
    "protein_g": number,
    "carbs_g": number,
    "fat_g": number
  }},
  "meal_suggestions": [
    {{
      "meal_name": "",
      "foods": [],
      "protein_g": number,
      "carbs_g": number,
      "fat_g": number,
      "calories": number
    }}
  ],
  "hydration_recommendation": "",
  "nutrition_timing_guidance": ""
}}
"""
          
        required_fields = [

          "daily_calorie_target",
          "macro_targets",
          "meal_suggestions",
          "hydration_recommendation",
          "nutrition_timing_guidance"
          ]
        result = self.client.generate_structured_json(
          prompt = prompt,
          required_fields=required_fields
        )

        return result
