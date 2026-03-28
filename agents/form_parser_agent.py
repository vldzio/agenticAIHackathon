from typing import Any, Dict, List


class FormParserAgent:
    """Validates user form inputs and calculates derived metrics."""

    VALID_GENDERS = ["Male", "Female", "Other"]
    VALID_FITNESS_GOALS = ["Weight Loss", "Muscle Building", "Endurance/Cardio", "General Fitness"]

    def __init__(self, client=None):
        del client

    def _validate_numeric(self, value: Any, min_v: float, max_v: float, label: str) -> List[str]:
        try:
            num = float(value)
        except (ValueError, TypeError):
            return [f"{label} must be numeric."]

        if not (min_v <= num <= max_v):
            return [f"{label} must be between {min_v} and {max_v}."]
        return []

    def _get_validation_errors(self, data: Dict[str, Any]) -> List[str]:
        errors: List[str] = []
        errors.extend(self._validate_numeric(data.get("age"), 18, 100, "Age"))
        errors.extend(self._validate_numeric(data.get("weight_kg"), 30, 300, "Weight"))
        errors.extend(self._validate_numeric(data.get("height_cm"), 100, 250, "Height"))

        if data.get("gender") not in self.VALID_GENDERS:
            errors.append("Invalid gender value.")
        if data.get("fitness_goal") not in self.VALID_FITNESS_GOALS:
            errors.append("Invalid fitness goal.")

        for field in ["fitness_experience", "health_conditions", "available_hours_per_week"]:
            value = data.get(field)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"Invalid {field.replace('_', ' ')}.")

        return errors

    def _extract_profile(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "age": int(float(data["age"])),
            "height_cm": float(data["height_cm"]),
            "weight_kg": float(data["weight_kg"]),
            "gender": data["gender"],
            "fitness_goal": data["fitness_goal"],
            "fitness_experience": data["fitness_experience"],
            "health_conditions": data["health_conditions"],
            "available_hours_per_week": data["available_hours_per_week"],
            "user_name": data.get("user_name"),
        }

    def _calculate_bmi(self, weight_kg: float, height_cm: float) -> float:
        height_m = height_cm / 100
        return round(weight_kg / (height_m ** 2), 2)

    def _get_age_category(self, age: int) -> str:
        if age < 30:
            return "Young Adult"
        if age <= 44:
            return "Adult"
        if age <= 59:
            return "Middle Aged"
        return "Senior"

    def _get_bmi_category(self, bmi: float) -> str:
        if bmi < 18.5:
            return "Underweight"
        if bmi <= 24.9:
            return "Normal"
        if bmi <= 29.9:
            return "Overweight"
        return "Obese"

    def validate_and_parse(self, form_data: Dict[str, Any]) -> Dict[str, Any]:
        errors = self._get_validation_errors(form_data)

        if errors:
            return {
                "parsed_profile": None,
                "bmi": None,
                "age_category": None,
                "bmi_category": None,
                "validation_errors": errors,
                "parsing_complete": False,
                "error_occurred": True,
            }

        profile = self._extract_profile(form_data)
        bmi = self._calculate_bmi(profile["weight_kg"], profile["height_cm"])

        return {
            "parsed_profile": profile,
            "bmi": bmi,
            "age_category": self._get_age_category(profile["age"]),
            "bmi_category": self._get_bmi_category(bmi),
            "validation_errors": [],
            "parsing_complete": True,
            "error_occurred": False,
        }
