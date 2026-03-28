from typing import Any, Dict, List, Optional, TypedDict


class FitnessAssessmentState(TypedDict, total=False):
    age: int
    height_cm: float
    weight_kg: float
    gender: str
    fitness_experience: str
    health_conditions: str
    fitness_goal: str
    available_hours_per_week: str
    user_name: Optional[str]
    plan_id: Optional[str]
    analysis_timestamp: Optional[str]
    bmi: Optional[float]
    age_category: Optional[str]
    bmi_category: Optional[str]
    parsed_profile: Dict[str, Any]
    validation_errors: List[str]
    parsing_complete: bool
    error_occurred: bool
    error_messages: List[str]
    normalized_fitness_experience: Dict[str, Any]
    normalized_health_conditions: Dict[str, Any]
    normalized_schedule: Dict[str, Any]
    fitness_level_score: Optional[float]
    fitness_level_class: Optional[str]
    fitness_confidence: Optional[float]
    fitness_analysis_complete: bool
    injury_risk_score: Optional[float]
    injury_risk_class: Optional[str]
    injury_confidence: Optional[float]
    injury_risk_factors: List[str]
    injury_assessment_complete: bool
    workout_plan: Dict[str, Any]
    weekly_schedule: Dict[str, Any]
    workout_intensity_level: Optional[str]
    workout_duration_per_session: Optional[int]
    workout_frequency_per_week: Optional[int]
    workout_progression_timeline: Optional[str]
    workout_safety_notes: List[str]
    workout_equipment_needed: List[str]
    workout_analysis_complete: bool
    nutrition_plan: Dict[str, Any]
    daily_calorie_target: Optional[int]
    macro_targets: Dict[str, Any]
    meal_suggestions: List[Dict[str, Any]]
    hydration_recommendation: Optional[str]
    nutrition_timing_guidance: Optional[str]
    nutrition_analysis_complete: bool
    sleep_recommendations: Dict[str, Any]
    rest_day_activities: List[str]
    mobility_work: List[str]
    stress_management_techniques: List[str]
    recovery_techniques: List[str]
    deload_strategy: Optional[str]
    schedule_integration: Dict[str, Any]
    time_management_tips: List[str]
    habit_formation_strategies: List[str]
    adherence_tips: List[str]
    recovery_lifestyle_analysis_complete: bool
    plan_generated: bool


def get_initial_state(form_data: Dict[str, Any]) -> FitnessAssessmentState:
    return {
        "age": form_data.get("age"),
        "height_cm": form_data.get("height_cm"),
        "weight_kg": form_data.get("weight_kg"),
        "gender": form_data.get("gender"),
        "fitness_experience": form_data.get("fitness_experience"),
        "health_conditions": form_data.get("health_conditions"),
        "fitness_goal": form_data.get("fitness_goal"),
        "available_hours_per_week": form_data.get("available_hours_per_week"),
        "user_name": form_data.get("user_name"),
        "plan_id": None,
        "analysis_timestamp": None,
        "bmi": None,
        "age_category": None,
        "bmi_category": None,
        "parsed_profile": {},
        "validation_errors": [],
        "parsing_complete": False,
        "error_occurred": False,
        "error_messages": [],
        "normalized_fitness_experience": {},
        "normalized_health_conditions": {},
        "normalized_schedule": {},
        "fitness_level_score": None,
        "fitness_level_class": None,
        "fitness_confidence": None,
        "fitness_analysis_complete": False,
        "injury_risk_score": None,
        "injury_risk_class": None,
        "injury_confidence": None,
        "injury_risk_factors": [],
        "injury_assessment_complete": False,
        "workout_plan": {},
        "weekly_schedule": {},
        "workout_intensity_level": None,
        "workout_duration_per_session": None,
        "workout_frequency_per_week": None,
        "workout_progression_timeline": None,
        "workout_safety_notes": [],
        "workout_equipment_needed": [],
        "workout_analysis_complete": False,
        "nutrition_plan": {},
        "daily_calorie_target": None,
        "macro_targets": {},
        "meal_suggestions": [],
        "hydration_recommendation": None,
        "nutrition_timing_guidance": None,
        "nutrition_analysis_complete": False,
        "sleep_recommendations": {},
        "rest_day_activities": [],
        "mobility_work": [],
        "stress_management_techniques": [],
        "recovery_techniques": [],
        "deload_strategy": None,
        "schedule_integration": {},
        "time_management_tips": [],
        "habit_formation_strategies": [],
        "adherence_tips": [],
        "recovery_lifestyle_analysis_complete": False,
        "plan_generated": False,
    }
