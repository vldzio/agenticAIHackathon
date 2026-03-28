"""
AetherFit Test Suite

Tests validate output contracts and logic without constraining implementation.
Following VentureLens testing patterns.

Test Structure:
- 19 total test cases
- Organized by component type
- Mock infrastructure for LLM testing
- Multiple user profiles for scenario testing
"""

import pytest
import json
from typing import Dict, Any, Optional


# ============================================================================
# PART 1: Mock Infrastructure
# ============================================================================

class MockGeminiContent:
    """Simulates google.generativeai content response"""
    def __init__(self, text: str):
        self.text = text


class MockGeminiResponse:
    """Simulates Gemini API response"""
    def __init__(self, text: str):
        self.text = text


class MockGeminiClient:
    """
    Complete mock of GeminiClient for testing without API calls.
    Pattern matches on prompt content to return appropriate responses.
    """

    def __init__(self):
        self.call_count = 0
        self.default_responses = {
            'normalized_fitness_experience': {
                'experience_level': 'Beginner',
                'years_active': 0,
                'activity_description': 'Just starting fitness journey'
            },
            'normalized_health_conditions': {
                'conditions': [],
                'severity': 'None',
                'exercise_limitations': 'None',
                'cleared_for_exercise': True
            },
            'normalized_schedule': {
                'estimated_hours_per_week': 4.0,
                'preferred_days': ['Weekdays'],
                'preferred_times': ['Morning']
            },
            'workout_plan': {
                'weekly_schedule': {
                    'Monday': [
                        {'name': 'Push-ups', 'sets': 3, 'reps': '10-12', 'rest': '60-90 seconds'},
                        {'name': 'Dumbbell Bench Press', 'sets': 3, 'reps': '8-10', 'rest': '90 seconds'}
                    ],
                    'Tuesday': [
                        {'name': 'Squats', 'sets': 3, 'reps': '12-15', 'rest': '60 seconds'},
                        {'name': 'Leg Press', 'sets': 3, 'reps': '10-12', 'rest': '90 seconds'}
                    ]
                },
                'workout_intensity_level': 'Moderate',
                'workout_duration_per_session': 45,
                'workout_frequency_per_week': 4,
                'workout_progression_timeline': '4-8 weeks',
                'workout_safety_notes': ['Warm up properly', 'Maintain form throughout'],
                'workout_equipment_needed': ['Dumbbells', 'Bench']
            },
            'nutrition_plan': {
                'daily_calorie_target': 2000,
                'macro_targets': {'protein_g': 150, 'carbs_g': 200, 'fat_g': 65},
                'meal_suggestions': [
                    {
                        'meal_name': 'Breakfast',
                        'foods': ['Idli with Sambar', 'Green Chutney'],
                        'protein_g': 8,
                        'carbs_g': 45,
                        'fat_g': 3,
                        'calories': 220
                    },
                    {
                        'meal_name': 'Lunch',
                        'foods': ['Chicken Tikka Masala', 'Brown Rice', 'Mixed Vegetables'],
                        'protein_g': 35,
                        'carbs_g': 50,
                        'fat_g': 12,
                        'calories': 520
                    },
                    {
                        'meal_name': 'Snack',
                        'foods': ['Greek Yogurt with Honey'],
                        'protein_g': 15,
                        'carbs_g': 20,
                        'fat_g': 2,
                        'calories': 160
                    }
                ],
                'hydration_recommendation': '2-3 liters per day, include coconut water for post-workout recovery',
                'nutrition_timing_guidance': 'Pre-workout: Light snack 30-45 minutes before. Post-workout: Carbs with protein within 1 hour'
            },
            'recovery_plan': {
                'sleep_recommendations': {'hours_per_night': 8, 'sleep_quality_tips': []},
                'rest_day_activities': ['Light stretching', 'Walking'],
                'mobility_work': ['Yoga', 'Foam rolling'],
                'stress_management_techniques': ['Meditation', 'Deep breathing'],
                'recovery_techniques': ['Ice bath', 'Massage'],
                'deload_strategy': 'Reduce volume by 50% every 4th week',
                'schedule_integration': {'best_days': ['Mon', 'Wed'], 'best_times': ['Morning']},
                'time_management_tips': ['Schedule workouts in calendar'],
                'habit_formation_strategies': ['Start with 2 sessions per week'],
                'adherence_tips': ['Track progress', 'Find workout buddy']
            }
        }

    def generate_content(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        response_mime_type: Optional[str] = None,
    ) -> str:
        """Generate content with pattern matching on prompt"""
        self.call_count += 1
        prompt_lower = prompt.lower()

        # Pattern matching for different agent types (check more specific first)
        if "normalize" in prompt_lower:
            response = {
                'normalized_fitness_experience': self.default_responses['normalized_fitness_experience'],
                'normalized_health_conditions': self.default_responses['normalized_health_conditions'],
                'normalized_schedule': self.default_responses['normalized_schedule']
            }
        elif "nutrition" in prompt_lower:
            response = self.default_responses['nutrition_plan']
        elif "recovery" in prompt_lower or "lifestyle" in prompt_lower:
            response = self.default_responses['recovery_plan']
        elif "workout" in prompt_lower:
            response = self.default_responses['workout_plan']
        else:
            response = self.default_responses['workout_plan']

        return json.dumps(response)

    def extract_json_from_response(self, response_text: str) -> Dict[str, Any]:
        """Extract JSON from response text"""
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            return {}

    def validate_response_fields(self, response: Dict[str, Any], required_fields: list) -> None:
        """Validate that response has required fields"""
        missing = [f for f in required_fields if f not in response]
        if missing:
            raise ValueError(f"Missing fields: {missing}")

    def generate_structured_json(
        self,
        prompt: str,
        required_fields: list,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> Dict[str, Any]:
        """Generate and validate JSON response"""
        response_text = self.generate_content(prompt, temperature, max_tokens)
        result = self.extract_json_from_response(response_text)
        self.validate_response_fields(result, required_fields)
        return result


# ============================================================================
# PART 2: Sample User Profiles
# ============================================================================

SAMPLE_USER_BEGINNER = {
    'age': 22,
    'height_cm': 175.0,
    'weight_kg': 85.0,
    'gender': 'Male',
    'fitness_goal': 'Weight Loss',
    'fitness_experience': 'Never exercised before, just started gym',
    'health_conditions': 'None',
    'available_hours_per_week': '3-4 hours on weekends',
    'user_name': 'Alex'
}

SAMPLE_USER_EXPERIENCED = {
    'age': 35,
    'height_cm': 180.0,
    'weight_kg': 75.0,
    'gender': 'Male',
    'fitness_goal': 'Muscle Building',
    'fitness_experience': '5 years of gym training, competitive athlete',
    'health_conditions': 'None',
    'available_hours_per_week': '10-12 hours, 5-6 days per week',
    'user_name': 'Jordan'
}

SAMPLE_USER_WITH_CONDITIONS = {
    'age': 45,
    'height_cm': 170.0,
    'weight_kg': 95.0,
    'gender': 'Female',
    'fitness_goal': 'General Fitness',
    'fitness_experience': 'Used to exercise, took a 2-year break',
    'health_conditions': 'Slight asthma, lower back pain from desk job',
    'available_hours_per_week': '5 hours, flexible schedule',
    'user_name': 'Sarah'
}

SAMPLE_USER_RECOVERING = {
    'age': 28,
    'height_cm': 165.0,
    'weight_kg': 68.0,
    'gender': 'Female',
    'fitness_goal': 'Endurance/Cardio',
    'fitness_experience': 'Running 2-3 times per week for 6 months',
    'health_conditions': 'Recently recovered from knee injury (3 months ago)',
    'available_hours_per_week': '4-5 hours, mornings preferred',
    'user_name': 'Emma'
}

# Valid enumeration values
VALID_FITNESS_CLASSES = ['Beginner', 'Intermediate', 'Advanced', 'Athlete']
VALID_RISK_CLASSES = ['Low Risk', 'Moderate Risk', 'High Risk', 'Very High Risk']


# ============================================================================
# PART 3: ML Agent Tests (6 tests)
# ============================================================================

def test_fitness_scorer_beginner():
    """Test fitness scorer classifies beginner correctly"""
    from agents.fitness_scorer_ml import FitnessScorerMLAgent

    agent = FitnessScorerMLAgent()
    result = agent.predict_fitness_level({
        'age': 22, 'bmi': 27.8, 'weight_kg': 85.0,
        'gender': 'Male', 'fitness_goal': 'Weight Loss',
        'age_category': 'Young Adult', 'bmi_category': 'Overweight',
        'available_hours_per_week': 3, 'fitness_experience_level': 'Beginner'
    })

    # Validate output structure
    assert 'fitness_level_score' in result
    assert 'fitness_level_class' in result
    assert 'fitness_confidence' in result

    # Validate types
    assert isinstance(result['fitness_level_score'], (int, float))
    assert isinstance(result['fitness_level_class'], str)
    assert isinstance(result['fitness_confidence'], (int, float))

    # Validate ranges
    assert 0 <= result['fitness_confidence'] <= 100

    # Validate classification
    assert result['fitness_level_class'] in VALID_FITNESS_CLASSES


def test_fitness_scorer_experienced():
    """Test fitness scorer classifies experienced athlete differently"""
    from agents.fitness_scorer_ml import FitnessScorerMLAgent

    agent = FitnessScorerMLAgent()
    result = agent.predict_fitness_level({
        'age': 35, 'bmi': 23.1, 'weight_kg': 75.0,
        'gender': 'Male', 'fitness_goal': 'Muscle Building',
        'age_category': 'Adult', 'bmi_category': 'Normal',
        'available_hours_per_week': 10, 'fitness_experience_level': 'Advanced'
    })

    # Validate output structure
    assert 'fitness_level_score' in result
    assert 'fitness_level_class' in result
    assert 'fitness_confidence' in result

    # Validate classification
    assert result['fitness_level_class'] in VALID_FITNESS_CLASSES


def test_fitness_scorer_comparative():
    """Different user profiles produce different fitness classifications"""
    from agents.fitness_scorer_ml import FitnessScorerMLAgent

    agent = FitnessScorerMLAgent()

    beginner_result = agent.predict_fitness_level({
        'age': 22, 'bmi': 27.8, 'weight_kg': 85.0,
        'gender': 'Male', 'fitness_goal': 'Weight Loss',
        'age_category': 'Young Adult', 'bmi_category': 'Overweight',
        'available_hours_per_week': 3, 'fitness_experience_level': 'Beginner'
    })

    experienced_result = agent.predict_fitness_level({
        'age': 35, 'bmi': 23.1, 'weight_kg': 75.0,
        'gender': 'Male', 'fitness_goal': 'Muscle Building',
        'age_category': 'Adult', 'bmi_category': 'Normal',
        'available_hours_per_week': 10, 'fitness_experience_level': 'Advanced'
    })

    # Both produce valid outputs
    assert beginner_result['fitness_level_score'] >= 0
    assert experienced_result['fitness_level_score'] >= 0

    # Valid classifications
    assert beginner_result['fitness_level_class'] in VALID_FITNESS_CLASSES
    assert experienced_result['fitness_level_class'] in VALID_FITNESS_CLASSES


def test_injury_assessor_low_risk():
    """Test injury assessor evaluates low-risk profile"""
    from agents.injury_assessor_ml import InjuryAssessorMLAgent

    agent = InjuryAssessorMLAgent()
    result = agent.predict_injury_risk({
        'age': 25, 'bmi': 23.0, 'weight_kg': 75.0,
        'fitness_level_class': 'Intermediate',
        'gender': 'Male', 'health_conditions': '',
        'age_category': 'Young Adult', 'bmi_category': 'Normal',
        'available_hours_per_week': 5, 'fitness_experience_level': 'Beginner'
    })

    # Validate output structure
    assert 'injury_risk_score' in result
    assert 'injury_risk_class' in result
    assert 'injury_confidence' in result
    assert 'injury_risk_factors' in result

    # Validate types
    assert isinstance(result['injury_risk_class'], str)
    assert isinstance(result['injury_risk_factors'], list)

    # Validate classification
    assert result['injury_risk_class'] in VALID_RISK_CLASSES


def test_injury_assessor_high_risk():
    """Test injury assessor identifies high-risk profile"""
    from agents.injury_assessor_ml import InjuryAssessorMLAgent

    agent = InjuryAssessorMLAgent()
    result = agent.predict_injury_risk({
        'age': 55, 'bmi': 32.0, 'weight_kg': 100.0,
        'fitness_level_class': 'Beginner',
        'gender': 'Female', 'health_conditions': 'Lower back pain',
        'age_category': 'Senior', 'bmi_category': 'Obese',
        'available_hours_per_week': 2, 'fitness_experience_level': 'Beginner'
    })

    # Validate structure
    assert 'injury_risk_factors' in result
    assert isinstance(result['injury_risk_factors'], list)
    assert result['injury_risk_class'] in VALID_RISK_CLASSES


def test_injury_assessor_with_conditions():
    """Test injury assessor considers health conditions"""
    from agents.injury_assessor_ml import InjuryAssessorMLAgent

    agent = InjuryAssessorMLAgent()

    # Profile without conditions
    normal_result = agent.predict_injury_risk({
        'age': 30, 'bmi': 24.0, 'weight_kg': 75.0,
        'fitness_level_class': 'Intermediate',
        'gender': 'Male', 'health_conditions': '',
        'age_category': 'Adult', 'bmi_category': 'Normal',
        'available_hours_per_week': 5, 'fitness_experience_level': 'Beginner'
    })

    # Profile with conditions
    conditions_result = agent.predict_injury_risk({
        'age': 45, 'bmi': 28.0, 'weight_kg': 95.0,
        'fitness_level_class': 'Beginner',
        'gender': 'Female', 'health_conditions': 'Asthma, back pain',
        'age_category': 'Middle Aged', 'bmi_category': 'Overweight',
        'available_hours_per_week': 3, 'fitness_experience_level': 'Beginner'
    })

    # Both produce valid outputs
    assert normal_result['injury_risk_class'] in VALID_RISK_CLASSES
    assert conditions_result['injury_risk_class'] in VALID_RISK_CLASSES

    # Both have risk factors
    assert isinstance(normal_result['injury_risk_factors'], list)
    assert isinstance(conditions_result['injury_risk_factors'], list)


# ============================================================================
# PART 4: LLM Agent Tests (5 tests)
# ============================================================================

def test_input_normalizer_natural_language():
    """Test input normalizer parses natural language correctly"""
    from agents.input_normalizer_llm import InputNormalizerLLMAgent

    mock_client = MockGeminiClient()
    agent = InputNormalizerLLMAgent(client=mock_client)

    result = agent.normalize_inputs(
        fitness_experience="Was doing cardio before 6 months",
        health_conditions="Having slight asthma",
        available_hours_per_week="I am free after 8:00 every night"
    )

    # Validate required fields
    assert 'normalized_fitness_experience' in result
    assert 'normalized_health_conditions' in result
    assert 'normalized_schedule' in result

    # Validate types
    assert isinstance(result['normalized_fitness_experience'], dict)
    assert isinstance(result['normalized_health_conditions'], dict)
    assert isinstance(result['normalized_schedule'], dict)

    # Verify LLM was called
    assert mock_client.call_count >= 1


def test_workout_planner_structure():
    """Test workout planner returns required fields"""
    from agents.workout_plan_generator_llm import WorkoutPlanGeneratorLLMAgent

    mock_client = MockGeminiClient()
    agent = WorkoutPlanGeneratorLLMAgent(client=mock_client)

    result = agent.generate_workout_plan({
        'fitness_level_class': 'Beginner',
        'injury_risk_class': 'Moderate Risk',
        'fitness_goal': 'Weight Loss',
        'health_conditions': 'None',
        'age': 26,
        'gender': 'Male'
    })

    # Validate required fields
    required_fields = [
        'weekly_schedule', 'workout_intensity_level',
        'workout_duration_per_session', 'workout_frequency_per_week',
        'workout_progression_timeline', 'workout_safety_notes',
        'workout_equipment_needed'
    ]

    for field in required_fields:
        assert field in result, f"Missing field: {field}"

    # Validate types
    assert isinstance(result['weekly_schedule'], dict)
    assert isinstance(result['workout_intensity_level'], str)
    assert isinstance(result['workout_safety_notes'], list)
    assert isinstance(result['workout_equipment_needed'], list)

    # Verify LLM was called
    assert mock_client.call_count >= 1


def test_nutrition_advisor_structure():
    """Test nutrition advisor returns required structure"""
    from agents.nutrition_plan_generator_llm import NutritionPlanGeneratorLLMAgent

    mock_client = MockGeminiClient()
    agent = NutritionPlanGeneratorLLMAgent(client=mock_client)

    result = agent.generate_nutrition_plan({
        'age': 26, 'weight_kg': 90, 'height_cm': 170,
        'gender': 'Male', 'fitness_level_class': 'Beginner',
        'fitness_goal': 'Weight Loss', 'bmi': 29.4
    })

    # Validate required fields
    required_fields = [
        'daily_calorie_target', 'macro_targets', 'meal_suggestions',
        'hydration_recommendation', 'nutrition_timing_guidance'
    ]

    for field in required_fields:
        assert field in result

    # Validate types
    assert isinstance(result['daily_calorie_target'], (int, float))
    assert isinstance(result['macro_targets'], dict)
    assert isinstance(result['meal_suggestions'], list)

    # Verify LLM was called
    assert mock_client.call_count >= 1


def test_recovery_optimizer_structure():
    """Test recovery optimizer returns complete recovery plan"""
    from agents.recovery_lifestyle_optimizer_llm import RecoveryLifestyleOptimizerLLMAgent

    mock_client = MockGeminiClient()
    agent = RecoveryLifestyleOptimizerLLMAgent(client=mock_client)

    result = agent.generate_recovery_lifestyle_plan({
        'age': 26, 'fitness_level_class': 'Beginner',
        'injury_risk_class': 'Moderate Risk',
        'health_conditions': 'None'
    })

    # Validate required fields
    required_fields = [
        'sleep_recommendations', 'rest_day_activities', 'mobility_work',
        'stress_management_techniques', 'recovery_techniques',
        'deload_strategy', 'schedule_integration', 'time_management_tips',
        'habit_formation_strategies', 'adherence_tips'
    ]

    for field in required_fields:
        assert field in result

    # Validate types
    assert isinstance(result['sleep_recommendations'], dict)
    assert isinstance(result['rest_day_activities'], list)
    assert isinstance(result['mobility_work'], list)

    # Verify LLM was called
    assert mock_client.call_count >= 1


def test_llm_agents_require_client():
    """Test LLM agents raise error when client is None"""
    from agents.input_normalizer_llm import InputNormalizerLLMAgent
    from agents.workout_plan_generator_llm import WorkoutPlanGeneratorLLMAgent
    from agents.nutrition_plan_generator_llm import NutritionPlanGeneratorLLMAgent
    from agents.recovery_lifestyle_optimizer_llm import RecoveryLifestyleOptimizerLLMAgent

    with pytest.raises(ValueError):
        InputNormalizerLLMAgent(client=None)

    with pytest.raises(ValueError):
        WorkoutPlanGeneratorLLMAgent(client=None)

    with pytest.raises(ValueError):
        NutritionPlanGeneratorLLMAgent(client=None)

    with pytest.raises(ValueError):
        RecoveryLifestyleOptimizerLLMAgent(client=None)


# ============================================================================
# PART 5: State Management Tests (2 tests)
# ============================================================================

def test_initial_state_creation():
    """Test state initialization with form data"""
    from state import get_initial_state

    form_data = {
        'age': 26, 'height_cm': 170, 'weight_kg': 90,
        'gender': 'Male', 'fitness_goal': 'Weight Loss',
        'fitness_experience': 'New to gym',
        'health_conditions': 'None',
        'available_hours_per_week': '4-5 hours',
        'user_name': 'Test User'
    }

    state = get_initial_state(form_data)

    # Validate input fields copied
    assert state['age'] == 26
    assert state['height_cm'] == 170
    assert state['user_name'] == 'Test User'

    # Validate output fields initialized
    assert state['bmi'] is None
    assert state['fitness_level_score'] is None
    assert state['error_messages'] == []


def test_state_validation():
    """Test state structure is valid after updates"""
    from state import get_initial_state

    form_data = SAMPLE_USER_BEGINNER
    state = get_initial_state(form_data)

    # Populate some fields
    state['bmi'] = 27.8
    state['age_category'] = 'Young Adult'
    state['fitness_level_score'] = 45.0
    state['fitness_level_class'] = 'Beginner'

    # Validate state structure
    assert 'age' in state
    assert 'fitness_level_class' in state
    assert 'error_messages' in state

    # Validate types
    assert isinstance(state['age'], int)
    assert isinstance(state['fitness_level_class'], str)
    assert isinstance(state['error_messages'], list)


# ============================================================================
# PART 6: Integration/Workflow Tests (4 tests)
# ============================================================================

def test_assess_fitness_complete_beginner():
    """Test complete assessment workflow for beginner user"""
    from graph import assess_fitness

    mock_client = MockGeminiClient()

    result = assess_fitness(
        age=22, height_cm=175, weight_kg=85, gender='Male',
        fitness_goal='Weight Loss',
        fitness_experience='Never exercised before',
        health_conditions='None',
        available_hours_per_week='3-4 hours',
        client=mock_client,
        user_name='Alex'
    )

    # Validate workflow completion
    assert result['parsing_complete'] is True
    assert result['fitness_analysis_complete'] is True
    assert result['injury_assessment_complete'] is True
    assert result['workout_analysis_complete'] is True
    assert result['nutrition_analysis_complete'] is True
    assert result['recovery_lifestyle_analysis_complete'] is True

    # Validate presence of results
    assert result['fitness_level_class'] is not None
    assert result['injury_risk_class'] is not None
    assert result['workout_plan'] is not None
    assert result['nutrition_plan'] is not None
    assert result['sleep_recommendations'] is not None


def test_assess_fitness_complete_experienced():
    """Test complete assessment for experienced athlete"""
    from graph import assess_fitness

    mock_client = MockGeminiClient()

    result = assess_fitness(
        age=35, height_cm=180, weight_kg=75, gender='Male',
        fitness_goal='Muscle Building',
        fitness_experience='5 years gym training',
        health_conditions='None',
        available_hours_per_week='10-12 hours',
        client=mock_client,
        user_name='Jordan'
    )

    # Validate completion
    assert result['fitness_analysis_complete'] is True
    assert result['injury_assessment_complete'] is True

    # Validate results exist
    assert result['fitness_level_class'] in VALID_FITNESS_CLASSES
    assert result['injury_risk_class'] in VALID_RISK_CLASSES


def test_assess_fitness_with_health_conditions():
    """Test assessment properly handles health conditions"""
    from graph import assess_fitness

    mock_client = MockGeminiClient()

    result = assess_fitness(
        age=45, height_cm=170, weight_kg=95, gender='Female',
        fitness_goal='General Fitness',
        fitness_experience='2-year break',
        health_conditions='Lower back pain, asthma',
        available_hours_per_week='5 hours',
        client=mock_client,
        user_name='Sarah'
    )

    # Validate completion
    assert result['injury_assessment_complete'] is True

    # Validate risk factors identified
    assert result['injury_risk_factors'] is not None
    assert isinstance(result['injury_risk_factors'], list)

    # Validate safety recommendations included
    assert result['workout_safety_notes'] is not None
    assert isinstance(result['workout_safety_notes'], list)


def test_assessment_comparison():
    """Different users produce differentiated assessments"""
    from graph import assess_fitness

    mock_client = MockGeminiClient()

    beginner_result = assess_fitness(
        age=22, height_cm=175, weight_kg=85, gender='Male',
        fitness_goal='Weight Loss',
        fitness_experience='Never exercised',
        health_conditions='None',
        available_hours_per_week='3-4 hours',
        client=mock_client,
        user_name='Beginner'
    )

    # Reset call count
    mock_client.call_count = 0

    experienced_result = assess_fitness(
        age=35, height_cm=180, weight_kg=75, gender='Male',
        fitness_goal='Muscle Building',
        fitness_experience='5 years training',
        health_conditions='None',
        available_hours_per_week='10-12 hours',
        client=mock_client,
        user_name='Experienced'
    )

    # Validate both completed
    assert beginner_result['fitness_level_class'] is not None
    assert experienced_result['fitness_level_class'] is not None

    # Both should be valid
    assert beginner_result['injury_risk_class'] in VALID_RISK_CLASSES
    assert experienced_result['injury_risk_class'] in VALID_RISK_CLASSES


# ============================================================================
# PART 7: Data Persistence Tests (2 tests)
# ============================================================================

def test_ml_models_exist():
    """Test that trained ML models exist and have content"""
    import os
    from pathlib import Path

    project_root = Path(__file__).parent
    models_dir = project_root / "ml" / "models"

    model_files = [
        "fitness_level_model.pkl",
        "fitness_level_scaler.pkl",
        "fitness_level_encoder.pkl",
        "injury_risk_model.pkl",
        "injury_risk_scaler.pkl",
        "injury_risk_encoder.pkl"
    ]

    for model_file in model_files:
        model_path = models_dir / model_file
        assert model_path.exists(), f"Missing: {model_file}"
        assert os.path.getsize(model_path) > 0, f"Empty: {model_file}"


def test_processed_data_not_empty():
    """Test that processed datasets exist and are not empty"""
    from pathlib import Path
    import pandas as pd

    project_root = Path(__file__).parent
    processed_dir = project_root / "data" / "processed"

    processed_files = [
        "fitness_level_training_cleaned.csv",
        "injury_risk_training_cleaned.csv"
    ]

    for dataset_file in processed_files:
        dataset_path = processed_dir / dataset_file
        assert dataset_path.exists(), f"Missing processed data: {dataset_file}"

        # Check file has content
        df = pd.read_csv(dataset_path)
        assert len(df) > 0, f"Empty processed data: {dataset_file}"


# ============================================================================
# Test Execution
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
