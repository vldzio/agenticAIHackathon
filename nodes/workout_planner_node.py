from typing import Dict, Any

from agents.workout_plan_generator_llm import WorkoutPlanGeneratorLLMAgent
from state import FitnessAssessmentState


def workout_planner_node(state: FitnessAssessmentState, client) -> Dict[str, Any]:
    try:
      fitness_level_class = state.get("fitness_level_class")
      injury_risk_class = state.get("injury_risk_class")

      fitness_goal = state.get("fitness_goal")
      available_hours = state.get("available_hours_per_week")
      health_conditions = state.get("health_conditions")
      gender = state.get("gender")
      age = state.get("age")

      normalized_schedule =state.get("normalized_schedule", {})
      preferred_days = normalized_schedule.get("preferred_days", [])
      preferred_times = normalized_schedule.get("preferred_times", [])

      profile = {
        "fitness_level_class": fitness_level_class,
        "injury_risk_class": injury_risk_class,
        "fitness_goal": fitness_goal,
        "available_hours_per_week": available_hours,
        "health_conditions": health_conditions,
        "gender": gender,
        "age": age,
        "preferred_days": preferred_days,
        "preferred_times": preferred_times
      }

      agent = WorkoutPlanGeneratorLLMAgent(client)

      workout_plan = agent.generate_workout_plan(profile)

      weekly_schedule = workout_plan.get("weekly_schedule", {})
      workout_intensity_level = workout_plan.get("workout_intensity_level")
      workout_duration_per_session = workout_plan.get("workout_duration_per_session")
      workout_frequency_per_week = workout_plan.get("workout_frequency_per_week")
      workout_progression_timeline = workout_plan.get("workout_progression_timeline")
      workout_safety_notes = workout_plan.get("workout_safety_notes", [])
      workout_equipment_needed = workout_plan.get("workout_equipment_needed", [])

      return {
        "workout_plan": workout_plan,
        "weekly_schedule": weekly_schedule,
        "workout_intensity_level": workout_intensity_level,
        "workout_duration_per_session": workout_duration_per_session,
        "workout_frequency_per_week": workout_frequency_per_week,
        "workout_progression_timeline": workout_progression_timeline,
        "workout_safety_notes": workout_safety_notes,
        "workout_equipment_needed": workout_equipment_needed,
        "workout_analysis_complete": True
      }
    
    except Exception as e:
      print("Workout planner error:", str(e))

      return {
        "workout_plan": None,
        "weekly_schedule": {},
        "workout_intensity_level": None,
        "workout_duration_per_session": None,
        "workout_frequency_per_week": None,
        "workout_progression_timeline": None,
        "workout_safety_notes": [],
        "workout_equipment_needed": [],
        "workout_analysis_complete": False
      }