from datetime import datetime, timezone
from typing import Any, Dict
from uuid import uuid4

from state import FitnessAssessmentState, get_initial_state
from workflow import build_fitness_assessment_graph, get_workflow_structure


def assess_fitness(
    age: int,
    height_cm: float,
    weight_kg: float,
    gender: str,
    fitness_goal: str,
    fitness_experience: str,
    health_conditions: str,
    available_hours_per_week: str,
    client=None,
    user_name: str = None,
) -> Dict[str, Any]:
    """Run the complete fitness assessment workflow."""
    try:
        form_data = {
            "age": age,
            "height_cm": height_cm,
            "weight_kg": weight_kg,
            "gender": gender,
            "fitness_goal": fitness_goal,
            "fitness_experience": fitness_experience,
            "health_conditions": health_conditions,
            "available_hours_per_week": available_hours_per_week,
            "user_name": user_name,
        }

        state: FitnessAssessmentState = get_initial_state(form_data)
        state["plan_id"] = str(uuid4())
        state["analysis_timestamp"] = datetime.now(timezone.utc).isoformat()

        result_state = build_fitness_assessment_graph(client).invoke(state)

        assessment = {
            "plan_id": state["plan_id"],
            "analysis_timestamp": state["analysis_timestamp"],
            "user_name": user_name,
            "age": age,
            "height_cm": height_cm,
            "weight_kg": weight_kg,
            "gender": gender,
            "fitness_goal": fitness_goal,
            "fitness_experience": fitness_experience,
            "health_conditions": health_conditions,
            "available_hours_per_week": available_hours_per_week,
            "parsing_complete": True,
            "fitness_analysis_complete": result_state.get("fitness_analysis_complete", False),
            "injury_assessment_complete": result_state.get("injury_assessment_complete", False),
            "workout_analysis_complete": result_state.get("workout_analysis_complete", False),
            "nutrition_analysis_complete": result_state.get("nutrition_analysis_complete", False),
            "recovery_lifestyle_analysis_complete": result_state.get("recovery_lifestyle_analysis_complete", False),
            "bmi": result_state.get("bmi"),
            "age_category": result_state.get("age_category"),
            "bmi_category": result_state.get("bmi_category"),
            "fitness_level_score": result_state.get("fitness_level_score"),
            "fitness_level_class": result_state.get("fitness_level_class"),
            "fitness_confidence": result_state.get("fitness_confidence"),
            "injury_risk_score": result_state.get("injury_risk_score"),
            "injury_risk_class": result_state.get("injury_risk_class"),
            "injury_confidence": result_state.get("injury_confidence"),
            "injury_risk_factors": result_state.get("injury_risk_factors", []),
            "workout_plan": result_state.get("workout_plan", {}),
            "weekly_schedule": result_state.get("weekly_schedule", {}),
            "workout_intensity_level": result_state.get("workout_intensity_level"),
            "workout_duration_per_session": result_state.get("workout_duration_per_session"),
            "workout_frequency_per_week": result_state.get("workout_frequency_per_week"),
            "workout_progression_timeline": result_state.get("workout_progression_timeline"),
            "workout_safety_notes": result_state.get("workout_safety_notes", []),
            "workout_equipment_needed": result_state.get("workout_equipment_needed", []),
            "nutrition_plan": result_state.get("nutrition_plan", {}),
            "daily_calorie_target": result_state.get("daily_calorie_target"),
            "macro_targets": result_state.get("macro_targets", {}),
            "meal_suggestions": result_state.get("meal_suggestions", []),
            "hydration_recommendation": result_state.get("hydration_recommendation"),
            "nutrition_timing_guidance": result_state.get("nutrition_timing_guidance"),
            "sleep_recommendations": result_state.get("sleep_recommendations", {}),
            "rest_day_activities": result_state.get("rest_day_activities", []),
            "mobility_work": result_state.get("mobility_work", []),
            "stress_management_techniques": result_state.get("stress_management_techniques", []),
            "recovery_techniques": result_state.get("recovery_techniques", []),
            "deload_strategy": result_state.get("deload_strategy"),
            "schedule_integration": result_state.get("schedule_integration", {}),
            "time_management_tips": result_state.get("time_management_tips", []),
            "habit_formation_strategies": result_state.get("habit_formation_strategies", []),
            "adherence_tips": result_state.get("adherence_tips", []),
            "error": False,
            "error_messages": result_state.get("error_messages", []),
        }
        assessment["plan_generated"] = (
            assessment["fitness_analysis_complete"]
            and assessment["injury_assessment_complete"]
            and assessment["workout_analysis_complete"]
            and assessment["nutrition_analysis_complete"]
            and assessment["recovery_lifestyle_analysis_complete"]
        )
        return assessment
    except Exception as exc:
        return {"error": True, "error_message": str(exc), "analysis_complete": False}


def get_assessment_summary(assessment_result: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "user_profile": {
            "age": assessment_result.get("age"),
            "height_cm": assessment_result.get("height_cm"),
            "weight_kg": assessment_result.get("weight_kg"),
            "gender": assessment_result.get("gender"),
            "fitness_goal": assessment_result.get("fitness_goal"),
        },
        "derived_metrics": {"bmi": assessment_result.get("bmi")},
        "assessments": {
            "fitness_level": assessment_result.get("fitness_level_class"),
            "fitness_confidence": assessment_result.get("fitness_confidence"),
            "injury_risk": assessment_result.get("injury_risk_class"),
            "injury_confidence": assessment_result.get("injury_confidence"),
        },
        "metadata": {
            "plan_id": assessment_result.get("plan_id"),
            "analysis_timestamp": assessment_result.get("analysis_timestamp"),
        },
    }


def get_workout_plan_details(assessment_result: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "weekly_schedule": assessment_result.get("weekly_schedule"),
        "intensity_level": assessment_result.get("workout_intensity_level"),
        "duration_per_session": assessment_result.get("workout_duration_per_session"),
        "frequency_per_week": assessment_result.get("workout_frequency_per_week"),
        "progression_timeline": assessment_result.get("workout_progression_timeline"),
        "safety_notes": assessment_result.get("workout_safety_notes"),
        "equipment_needed": assessment_result.get("workout_equipment_needed"),
    }


def get_nutrition_plan_details(assessment_result: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "daily_calorie_target": assessment_result.get("daily_calorie_target"),
        "macro_targets": assessment_result.get("macro_targets"),
        "meal_suggestions": assessment_result.get("meal_suggestions"),
        "hydration_recommendation": assessment_result.get("hydration_recommendation"),
        "nutrition_timing_guidance": assessment_result.get("nutrition_timing_guidance"),
    }


def get_recovery_lifestyle_details(assessment_result: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "sleep_recommendations": assessment_result.get("sleep_recommendations"),
        "rest_day_activities": assessment_result.get("rest_day_activities"),
        "mobility_work": assessment_result.get("mobility_work"),
        "stress_management_techniques": assessment_result.get("stress_management_techniques"),
        "recovery_techniques": assessment_result.get("recovery_techniques"),
        "deload_strategy": assessment_result.get("deload_strategy"),
        "schedule_integration": assessment_result.get("schedule_integration"),
        "time_management_tips": assessment_result.get("time_management_tips"),
        "habit_formation_strategies": assessment_result.get("habit_formation_strategies"),
        "adherence_tips": assessment_result.get("adherence_tips"),
    }


def get_workflow_info() -> Dict[str, Any]:
    return get_workflow_structure()
