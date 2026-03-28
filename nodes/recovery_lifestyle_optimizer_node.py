from typing import Dict, Any

from agents.recovery_lifestyle_optimizer_llm import RecoveryLifestyleOptimizerLLMAgent
from state import FitnessAssessmentState


def recovery_lifestyle_optimizer_node(state: FitnessAssessmentState, client) -> Dict[str, Any]:
    try:
      age = state.get("age")
      fitness_level_class = state.get("fitness_level_class")
      injury_risk_class = state.get("injury_risk_class")
      health_conditions = state.get("health_conditions")
      fitness_goal = state.get("fitness_goal")
      workout_frequency = state.get("workout_frequency_per_week")
      available_hours = state.get("available_hours_per_week")

      normalized_schedule = state.get("normalized_schedule", {})
      preferred_days= normalized_schedule.get("preferred_days", [])
      preferred_times = normalized_schedule.get("preferred_times", [])

      profile = {
        "age": age,
        "fitness_level_class": fitness_level_class,
        "injury_risk_class": injury_risk_class,
        "health_conditions": health_conditions,
        "fitness_goal": fitness_goal,
        "workout_frequency_per_week": workout_frequency,
        "available_hours_per_week": available_hours,
        "preferred_days": preferred_days,
        "preferred_times": preferred_times 
      }

      agent = RecoveryLifestyleOptimizerLLMAgent(client=client)

      plan = agent.generate_recovery_lifestyle_plan(profile) or {}

      sleep_recommendations = plan.get("sleep_recommendations")
      rest_day_activities = plan.get("rest_day_activities", [])
      mobility_work = plan.get("mobility_work", [])
      stress_management_techniques = plan.get("stress_management_techniques", [])
      recovery_techniques = plan.get("recovery_techniques", [])
      deload_strategy = plan.get("deload_strategy")
      schedule_integration = plan.get("schedule_integration")
      time_management_tips = plan.get("time_management_tips", [])
      habit_formation_strategies = plan.get("habit_formation_strategies", [])
      adherence_tips = plan.get("adherence_tips", [])

      return {
        "sleep_recommendations": sleep_recommendations,
        "rest_day_activities": rest_day_activities,
        "mobility_work": mobility_work,
        "stress_management_techniques": stress_management_techniques,
        "recovery_techniques": recovery_techniques,
        "deload_strategy": deload_strategy,
        "schedule_integration": schedule_integration,
        "time_management_tips": time_management_tips,
        "habit_formation_strategies": habit_formation_strategies,
        "adherence_tips": adherence_tips,
        "recovery_lifestyle_analysis_complete": True
      }

    except Exception as e:
      print("Recovery lifestyle optimize error:", str(e))

      return {
        "sleep_recommendations": None,
        "rest_day_activities": [],
        "mobility_work": [],
        "stress_management_techniques": [],
        "recovery_techniques": [],
        "deload_strategy":None,
        "schedule_integration": None,
        "time_management_tips": [],
        "habit_formation_strategies": [],
        "adherence_tips": [],
        "recovery_lifestyle_analysis_complete": False
      }