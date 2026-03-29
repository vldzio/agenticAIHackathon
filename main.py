import json
from datetime import datetime, timezone

import streamlit as st

from graph import assess_fitness
from ml.evaluation.evaluate_models import evaluate_all_models
from utils.gemini_client import build_gemini_client


def initialize_session_state():
    if "assessment_result" not in st.session_state:
        st.session_state.assessment_result = None
    if "client" not in st.session_state:
        st.session_state.client = None
    if "eval_results" not in st.session_state:
        st.session_state.eval_results = None
    if "generation_mode" not in st.session_state:
        st.session_state.generation_mode = "Mock Demo"
    if "user_gemini_api_key" not in st.session_state:
        st.session_state.user_gemini_api_key = ""
    if "client_signature" not in st.session_state:
        st.session_state.client_signature = None


def setup_api_client():
    try:
        mode = st.session_state.generation_mode
        use_mock = mode == "Mock Demo"
        api_key = st.session_state.user_gemini_api_key.strip()
        client_signature = ("mock", None) if use_mock else ("byok", api_key)

        if not use_mock and not api_key:
            st.error("Enter your Gemini API key to use live generation.")
            return False

        if st.session_state.client is None or st.session_state.client_signature != client_signature:
            st.session_state.client = build_gemini_client(api_key=api_key, use_mock=use_mock)
            st.session_state.client_signature = client_signature
        return True
    except Exception as exc:
        st.session_state.client = None
        st.session_state.client_signature = None
        st.error(f"Client setup error: {exc}")
        return False


def reset_runtime_client():
    st.session_state.client = None
    st.session_state.client_signature = None


def clear_api_key():
    st.session_state.user_gemini_api_key = ""
    reset_runtime_client()


def display_overview_tab(assessment):
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Fitness Level", assessment.get("fitness_level_class", "Unknown"), f"{assessment.get('fitness_confidence', 0):.2f}% confidence")
    with col2:
        st.metric("Injury Risk", assessment.get("injury_risk_class", "Unknown"), f"{assessment.get('injury_confidence', 0):.2f}% confidence")
    with col3:
        st.metric("BMI", assessment.get("bmi", "N/A"))

    st.subheader("Personal Info")
    st.write(f"Name: {assessment.get('user_name') or 'N/A'}")
    st.write(f"Age: {assessment.get('age')}")
    st.write(f"Gender: {assessment.get('gender')}")
    st.write(f"Height: {assessment.get('height_cm')} cm")
    st.write(f"Weight: {assessment.get('weight_kg')} kg")
    st.write(f"Fitness Goal: {assessment.get('fitness_goal')}")
    st.write(f"Available Hours: {assessment.get('available_hours_per_week')}")

    if assessment.get("injury_risk_factors"):
        st.subheader("Risk Factors")
        for factor in assessment["injury_risk_factors"]:
            st.write(f"- {factor}")


def display_workout_tab(assessment):
    st.subheader("Workout Plan")
    st.write("Frequency:", assessment.get("workout_frequency_per_week"))
    st.write("Intensity:", assessment.get("workout_intensity_level"))
    st.write("Session Duration:", assessment.get("workout_duration_per_session"))
    st.write("Progression:", assessment.get("workout_progression_timeline"))

    for note in assessment.get("workout_safety_notes", []):
        st.write(f"- {note}")

    equipment = assessment.get("workout_equipment_needed", [])
    if equipment:
        st.write("Equipment Needed:", ", ".join(equipment))

    schedule = assessment.get("weekly_schedule") or assessment.get("workout_plan", {}).get("weekly_schedule", {})
    for day, exercises in schedule.items():
        with st.expander(day):
            st.write(exercises)


def display_nutrition_tab(assessment):
    st.subheader("Nutrition Plan")
    st.metric("Daily Calories", assessment.get("daily_calorie_target", "N/A"))
    macros = assessment.get("macro_targets", {})
    st.write("Protein:", macros.get("protein_g", "N/A"))
    st.write("Carbs:", macros.get("carbs_g", "N/A"))
    st.write("Fat:", macros.get("fat_g", "N/A"))
    st.write("Hydration:", assessment.get("hydration_recommendation", "N/A"))
    st.write("Timing Guidance:", assessment.get("nutrition_timing_guidance", "N/A"))

    for meal in assessment.get("meal_suggestions", []):
        with st.expander(meal.get("meal_name", "Meal")):
            st.write(meal)


def display_recovery_tab(assessment):
    st.subheader("Recovery & Lifestyle")
    sleep = assessment.get("sleep_recommendations", {})
    st.write("Sleep:", sleep.get("hours_per_night", "N/A"), "hours")
    for tip in sleep.get("sleep_quality_tips", []):
        st.write(f"- {tip}")

    sections = {
        "Rest Day Activities": assessment.get("rest_day_activities", []),
        "Mobility Work": assessment.get("mobility_work", []),
        "Stress Management": assessment.get("stress_management_techniques", []),
        "Recovery Techniques": assessment.get("recovery_techniques", []),
        "Time Management Tips": assessment.get("time_management_tips", []),
        "Habit Formation Strategies": assessment.get("habit_formation_strategies", []),
        "Adherence Tips": assessment.get("adherence_tips", []),
    }
    for label, values in sections.items():
        st.write(f"{label}:")
        if values:
            for value in values:
                st.write(f"- {value}")
        else:
            st.write("No recommendations available.")

    if assessment.get("deload_strategy"):
        st.write("Deload Strategy:", assessment["deload_strategy"])
    if assessment.get("schedule_integration"):
        st.write("Schedule Integration:", assessment["schedule_integration"])


def export_assessment(assessment):
    return json.dumps(
        {
            "plan_id": assessment.get("plan_id"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "assessment": assessment,
        },
        indent=2,
    )


def display_model_evaluation_section(eval_results):
    if not eval_results:
        return

    st.subheader("Model Evaluation")
    for label, key in [("Fitness", "fitness_evaluation"), ("Injury Risk", "injury_evaluation")]:
        result = eval_results.get(key, {})
        if "error" in result:
            st.error(f"{label} evaluation error: {result['error']}")
            continue
        st.write(f"{label} Model Accuracy:", result.get("eval_accuracy"))
        st.write(f"{label} Confusion Matrix")
        st.write(result.get("confusion_matrix"))


def main():
    st.set_page_config(page_title="AetherFit AI", layout="wide")
    initialize_session_state()

    st.title("AetherFit AI")
    st.write("Personalized Fitness Assessment System")
    if st.session_state.generation_mode == "Mock Demo":
        st.warning("Mock Demo is active. Results are simulated and no API key is required.")

    with st.sidebar:
        st.header("User Input")
        previous_mode = st.session_state.generation_mode
        previous_api_key = st.session_state.user_gemini_api_key
        generation_mode = st.radio(
            "Generation Mode",
            ["Mock Demo", "Use My Gemini API Key"],
            key="generation_mode",
        )
        if generation_mode == "Use My Gemini API Key":
            st.text_input(
                "Gemini API Key",
                type="password",
                key="user_gemini_api_key",
                help="Used only for this session and not stored.",
            )
            st.caption("Your API key is used only for this session and is not stored.")
            st.button("Clear API Key", on_click=clear_api_key)

        if (
            st.session_state.generation_mode != previous_mode
            or st.session_state.user_gemini_api_key != previous_api_key
        ):
            reset_runtime_client()

        name = st.text_input("Name", value="Alex")
        age = st.slider("Age", 18, 100, 30)
        height = st.number_input("Height (cm)", min_value=100, max_value=250, value=170)
        weight = st.number_input("Weight (kg)", min_value=30, max_value=300, value=70)
        gender = st.selectbox("Gender", ["Male", "Female", "Other"])
        fitness_goal = st.selectbox("Fitness Goal", ["Weight Loss", "Muscle Building", "Endurance/Cardio", "General Fitness"])
        fitness_experience = st.text_area("Fitness Experience", value="Beginner, training 3 times per week")
        health_conditions = st.text_area("Health Conditions", value="None")
        available_hours = st.text_area("Available Hours Per Week", value="4-5 hours, weekday mornings preferred")
        generate = st.button("Generate Assessment")
        run_evaluation = st.button("Run Model Evaluation")

    if generate and setup_api_client():
        with st.spinner("Generating fitness plan..."):
            st.session_state.assessment_result = assess_fitness(
                age=age,
                height_cm=height,
                weight_kg=weight,
                gender=gender,
                fitness_goal=fitness_goal,
                fitness_experience=fitness_experience,
                health_conditions=health_conditions,
                available_hours_per_week=available_hours,
                client=st.session_state.client,
                user_name=name,
            )

    if run_evaluation:
        st.session_state.eval_results = evaluate_all_models()

    assessment = st.session_state.assessment_result
    if assessment:
        if assessment.get("error"):
            st.error(assessment.get("error_message", "Assessment failed"))
        else:
            st.success("Assessment generated")
            st.download_button("Download JSON", export_assessment(assessment), file_name="fitness_assessment.json", mime="application/json")
            tab1, tab2, tab3, tab4 = st.tabs(["Overview", "Workout", "Nutrition", "Recovery"])
            with tab1:
                display_overview_tab(assessment)
            with tab2:
                display_workout_tab(assessment)
            with tab3:
                display_nutrition_tab(assessment)
            with tab4:
                display_recovery_tab(assessment)

    display_model_evaluation_section(st.session_state.eval_results)


if __name__ == "__main__":
    main()
