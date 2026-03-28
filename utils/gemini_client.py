#!/usr/bin/env python3
"""
Gemini client helpers for AetherFit.
"""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
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
    from dotenv import load_dotenv

    env_file = Path.cwd() / ".env"
    if env_file.exists():
        load_dotenv(env_file)
except ImportError:
    pass

try:
    from google import generativeai as genai
except ImportError:
    genai = None


def _get_all_api_keys() -> List[str]:
    keys: List[str] = []
    try:
        import streamlit as st

        for i in range(1, 5):
            key = st.secrets.get(f"GEMINI_API_KEY_{i}")
            if key:
                keys.append(key)
    except Exception:
        pass

    env_key = os.getenv("GEMINI_API_KEY")
    if env_key:
        keys.append(env_key)

    for i in range(1, 5):
        env_key_i = os.getenv(f"GEMINI_API_KEY_{i}")
        if env_key_i:
            keys.append(env_key_i)

    filtered_keys = []
    for key in keys:
        normalized = key.strip()
        if normalized.lower() in INVALID_API_KEY_VALUES:
            continue
        filtered_keys.append(normalized)

    return list(dict.fromkeys(filtered_keys))


def _get_first_api_key() -> Optional[str]:
    keys = _get_all_api_keys()
    return keys[0] if keys else None


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


def _is_mock_enabled() -> bool:
    value = os.getenv("AETHERFIT_USE_MOCK_LLM", "").strip().lower()
    return value in {"1", "true", "yes", "on"}


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


def build_gemini_client():
    if _is_mock_enabled():
        logger.info("Using mock Gemini client")
        return MockGeminiClient()

    api_key = _get_first_api_key()
    model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
    if not api_key:
        raise ValueError("Gemini API key not found. Set GEMINI_API_KEY or GEMINI_API_KEY_1..4 in .env")
    if genai is None:
        raise ImportError("google-generativeai is not installed. Install with: pip install google-generativeai")

    genai.configure(api_key=api_key)
    return GeminiClient(model=model_name)


class GeminiClient:
    def __init__(self, model: str = "gemini-2.5-flash-lite"):
        self.model = model
        self.api_keys = _get_all_api_keys()
        self.current_key_index = 0
        self.client = None
        self._initialize_client()

    def _initialize_client(self) -> None:
        if not self.api_keys:
            raise ValueError("No valid API keys available for Gemini")
        genai.configure(api_key=self.api_keys[self.current_key_index])
        self.client = genai.GenerativeModel(self.model)

    def _rotate_api_key(self) -> bool:
        self.current_key_index += 1
        if self.current_key_index >= len(self.api_keys):
            return False
        self._initialize_client()
        return True

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

        for attempt in range(len(self.api_keys)):
            try:
                response = self.client.generate_content(prompt, generation_config=generation_config)
                if not response or not getattr(response, "text", None):
                    raise ValueError("Empty response from LLM")
                return response.text
            except Exception as exc:
                error_text = str(exc).lower()
                is_quota_error = any(token in error_text for token in ["429", "quota", "rate limit", "exceeded"])
                if is_quota_error and attempt < len(self.api_keys) - 1 and self._rotate_api_key():
                    continue
                raise ValueError(f"Failed to generate content from LLM: {exc}") from exc
        raise ValueError("Failed after exhausting all available API keys")

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
