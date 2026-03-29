#!/usr/bin/env python3
"""
Gemini client helpers for AetherFit.
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

INVALID_API_KEY_VALUES = {
    "",
    "your_api_key_here",
    "your_api_key",
    "replace_me",
    "changeme",
    "none",
    "null",
}

try:
    from google import generativeai as genai
except ImportError:
    genai = None


def _clean_json_text(text: str) -> str:
    cleaned = text.strip()
    cleaned = re.sub(r"```json\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"```", "", cleaned)
    cleaned = re.sub(r",\s*([}\]])", r"\1", cleaned)
    return cleaned.strip()


def _extract_json_candidates(text: str) -> List[str]:
    cleaned = _clean_json_text(text)
    candidates = [cleaned]
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        candidates.append(match.group(0))
    return list(dict.fromkeys(candidate for candidate in candidates if candidate))


def _normalize_api_key(api_key: Optional[str]) -> Optional[str]:
    if api_key is None:
        return None
    normalized = api_key.strip()
    if not normalized or normalized.lower() in INVALID_API_KEY_VALUES:
        return None
    return normalized


def _mock_payload_for_prompt(prompt: str) -> Dict[str, Any]:
    prompt_lower = prompt.lower()
    if "normalize" in prompt_lower:
        return {
            "normalized_fitness_experience": {
                "experience_level": "Beginner",
                "years_active": 0,
                "activity_description": "Starting a new fitness journey",
            },
            "normalized_health_conditions": {
                "conditions": [],
                "severity_assessment": "none",
                "exercise_limitations": [],
                "cleared_for_exercise": True,
            },
            "normalized_schedule": {
                "estimated_hours_per_week": 4.0,
                "preferred_days": ["Monday", "Wednesday", "Friday"],
                "preferred_times": ["Morning"],
                "schedule_constraints": [],
            },
        }
    if "nutrition" in prompt_lower:
        return {
            "maintenance_calories": 2200,
            "daily_calorie_target": 2200,
            "macro_targets": {"protein_g": 150, "carbs_g": 230, "fat_g": 65},
            "meal_suggestions": [
                {
                    "meal_name": "Breakfast",
                    "foods": ["Oats", "Greek Yogurt", "Banana"],
                    "protein_g": 28,
                    "carbs_g": 48,
                    "fat_g": 10,
                    "calories": 380,
                },
                {
                    "meal_name": "Lunch",
                    "foods": ["Brown Rice", "Paneer Curry", "Salad"],
                    "protein_g": 35,
                    "carbs_g": 60,
                    "fat_g": 18,
                    "calories": 620,
                },
            ],
            "hydration_recommendation": "Aim for 2.5 to 3 liters of water daily.",
            "nutrition_timing_guidance": "Have a light carb snack pre-workout and protein plus carbs within 60 minutes after training.",
        }
    if "recovery" in prompt_lower or "lifestyle" in prompt_lower:
        return {
            "sleep_recommendations": {
                "hours_per_night": 8,
                "sleep_quality_tips": ["Maintain a fixed sleep schedule", "Limit screens before bed"],
            },
            "rest_day_activities": ["Walking", "Light stretching"],
            "mobility_work": ["Hip mobility drills", "Thoracic spine rotation"],
            "stress_management_techniques": ["Box breathing", "Short meditation"],
            "recovery_techniques": ["Foam rolling", "Mobility flow", "Easy walk"],
            "deload_strategy": "Reduce volume by 30 to 40 percent every 4 to 6 weeks.",
            "schedule_integration": {
                "best_days": ["Tuesday", "Thursday", "Saturday"],
                "best_times": ["Morning"],
                "weekly_schedule_tips": "Keep one full rest day between demanding sessions when possible.",
            },
            "time_management_tips": ["Prepare workout clothes the night before", "Block sessions on your calendar"],
            "habit_formation_strategies": ["Start with consistent training days", "Track each completed session"],
            "adherence_tips": ["Focus on small weekly wins", "Review progress every Sunday"],
        }
    return {
        "weekly_schedule": {
            "Monday": [
                {"exercise_name": "Bodyweight Squat", "sets": 3, "reps": "12", "rest_period": "60 sec"},
                {"exercise_name": "Push-ups", "sets": 3, "reps": "10", "rest_period": "60 sec"},
            ],
            "Wednesday": [
                {"exercise_name": "Walking Lunges", "sets": 3, "reps": "10 each side", "rest_period": "60 sec"},
                {"exercise_name": "Plank", "sets": 3, "reps": "30 sec", "rest_period": "45 sec"},
            ],
        },
        "workout_intensity_level": "Moderate",
        "workout_frequency_per_week": 3,
        "workout_duration_per_session": 45,
        "workout_progression_timeline": "6 weeks",
        "workout_safety_notes": ["Warm up for 5 to 10 minutes", "Prioritize controlled form"],
        "workout_equipment_needed": ["Dumbbells", "Exercise mat"],
    }


class MockGeminiClient:
    def generate_content(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        response_mime_type: Optional[str] = None,
    ) -> str:
        del temperature, max_tokens, response_mime_type
        return json.dumps(_mock_payload_for_prompt(prompt))

    def extract_json_from_response(self, response_text: str) -> Dict[str, Any]:
        return extract_json(response_text)

    def validate_response_fields(self, response: Dict[str, Any], required_fields: List[str]) -> None:
        missing_fields = [field for field in required_fields if field not in response]
        if missing_fields:
            raise ValueError(f"LLM response missing required fields: {missing_fields}")

    def generate_structured_json(
        self,
        prompt: str,
        required_fields: List[str],
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> Dict[str, Any]:
        response_text = self.generate_content(
            prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            response_mime_type="application/json",
        )
        result = self.extract_json_from_response(response_text)
        self.validate_response_fields(result, required_fields)
        return result


def build_gemini_client(
    api_key: Optional[str] = None,
    use_mock: bool = False,
    model_name: Optional[str] = None,
):
    if use_mock:
        logger.info("Using mock Gemini client")
        return MockGeminiClient()

    normalized_api_key = _normalize_api_key(api_key)
    selected_model = model_name or os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
    if not normalized_api_key:
        raise ValueError("Gemini API key is required for live generation.")
    if genai is None:
        raise ImportError("google-generativeai is not installed. Install with: pip install google-generativeai")

    genai.configure(api_key=normalized_api_key)
    return GeminiClient(api_key=normalized_api_key, model=selected_model)


class GeminiClient:
    def __init__(self, api_key: str, model: str = "gemini-2.5-flash-lite"):
        self.api_key = api_key
        self.model = model
        self.client = None
        self._initialize_client()

    def _initialize_client(self) -> None:
        if not self.api_key:
            raise ValueError("No valid Gemini API key available")
        genai.configure(api_key=self.api_key)
        self.client = genai.GenerativeModel(self.model)

    def generate_content(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        response_mime_type: Optional[str] = None,
    ) -> str:
        generation_config: Dict[str, Any] = {
            "temperature": temperature,
            "max_output_tokens": max_tokens,
        }
        if response_mime_type:
            generation_config["response_mime_type"] = response_mime_type

        try:
            response = self.client.generate_content(prompt, generation_config=generation_config)
            if not response or not getattr(response, "text", None):
                raise ValueError("Empty response from LLM")
            return response.text
        except Exception as exc:
            raise ValueError(f"Failed to generate content from LLM: {exc}") from exc

    def extract_json_from_response(self, response_text: str) -> Dict[str, Any]:
        return extract_json(response_text)

    def validate_response_fields(self, response: Dict[str, Any], required_fields: List[str]) -> None:
        missing_fields = [field for field in required_fields if field not in response]
        if missing_fields:
            raise ValueError(f"LLM response missing required fields: {missing_fields}")

    def generate_structured_json(
        self,
        prompt: str,
        required_fields: List[str],
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> Dict[str, Any]:
        response_text = self.generate_content(
            prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            response_mime_type="application/json",
        )
        result = self.extract_json_from_response(response_text)
        self.validate_response_fields(result, required_fields)
        return result


def extract_json(text: str) -> Dict[str, Any]:
    for candidate in _extract_json_candidates(text):
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            continue
    raise ValueError("No valid JSON object found in response")
