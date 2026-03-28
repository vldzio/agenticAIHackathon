from pathlib import Path
import pickle
from typing import Any, Dict

import numpy as np


class InjuryAssessorMLAgent:
    """Predicts injury risk using the trained RandomForest model."""

    def __init__(self, model_dir: str = "ml/models"):
        base_dir = Path(__file__).resolve().parent.parent
        model_root = Path(model_dir)
        if not model_root.is_absolute():
            model_root = base_dir / model_root

        with open(model_root / "injury_risk_model.pkl", "rb") as model_file:
            self.model = pickle.load(model_file)
        with open(model_root / "injury_risk_scaler.pkl", "rb") as scaler_file:
            self.scaler = pickle.load(scaler_file)
        with open(model_root / "injury_risk_encoder.pkl", "rb") as encoder_file:
            self.encoder_data = pickle.load(encoder_file)
        if hasattr(self.model, "n_jobs"):
            self.model.n_jobs = 1

        self.feature_columns = self.encoder_data["feature_columns"]
        self.feature_encoders = self.encoder_data["feature_encoders"]
        self.label_encoder = self.encoder_data["target_encoder"]

    def _age_category(self, age: int) -> str:
        if age < 30:
            return "Young Adult"
        if age < 45:
            return "Adult"
        if age < 60:
            return "Middle Aged"
        return "Senior"

    def _bmi_category(self, bmi: float) -> str:
        if bmi < 18.5:
            return "Underweight"
        if bmi < 25:
            return "Normal"
        if bmi < 30:
            return "Overweight"
        return "Obese"

    def _flexibility_score(self, experience: str) -> int:
        mapping = {"Beginner": 40, "Intermediate": 60, "Advanced": 80, "Athlete": 90}
        return mapping.get(experience, 50)

    def _strength_imbalance(self, experience: str) -> int:
        mapping = {"Beginner": 70, "Intermediate": 50, "Advanced": 30, "Athlete": 20}
        return mapping.get(experience, 50)

    def _training_frequency(self, hours: float) -> int:
        if hours < 2:
            return 1
        if hours < 5:
            return 3
        return 5

    def _encode_features(self, features: Dict[str, Any]) -> np.ndarray:
        values = []
        for col in self.feature_columns:
            value = features.get(col)
            if col in self.feature_encoders:
                encoder = self.feature_encoders[col]
                if value is None or value not in encoder.classes_:
                    value = encoder.classes_[0]
                value = encoder.transform([value])[0]
            elif value is None:
                value = 0
            values.append(value)
        return np.array(values, dtype=float).reshape(1, -1)

    def _compute_risk_factors(self, age: int, bmi: float, has_conditions: int, previous_injury: int) -> list[str]:
        factors = []
        if age > 50:
            factors.append("Age above 50")
        if bmi > 30:
            factors.append("High BMI")
        if has_conditions:
            factors.append("Existing health conditions")
        if previous_injury:
            factors.append("Previous injury history")
        return factors

    def predict_injury_risk(self, user_profile: Dict[str, Any]) -> Dict[str, Any]:
        age = int(user_profile.get("age", 43))
        bmi = float(user_profile.get("bmi", 22))
        gender = user_profile.get("gender", "Male")
        experience = user_profile.get("fitness_experience_level") or user_profile.get("fitness_experience") or "Beginner"
        fitness_level = user_profile.get("fitness_level_class", "Beginner")
        hours = float(user_profile.get("available_hours_per_week", 3))
        health_conditions = str(user_profile.get("health_conditions", "") or "")
        injury_history = str(user_profile.get("injury_history", "") or "")

        has_health_conditions = 1 if health_conditions and health_conditions.lower() not in {"none", "no", ""} else 0
        previous_injury = 1 if injury_history or "injury" in health_conditions.lower() else 0

        features = {
            "Age": age,
            "BMI": bmi,
            "Fitness_Level": fitness_level,
            "Gender": gender,
            "Fitness_Experience": experience,
            "Age_Category": user_profile.get("age_category") or self._age_category(age),
            "BMI_Category": user_profile.get("bmi_category") or self._bmi_category(bmi),
            "Has_Health_Conditions": has_health_conditions,
            "Previous_Injury": previous_injury,
            "Flexibility_Score": self._flexibility_score(experience),
            "Strength_Imbalance_Score": self._strength_imbalance(experience),
            "Training_Frequency_Hours": self._training_frequency(hours),
        }

        x_scaled = self.scaler.transform(self._encode_features(features))
        prediction = self.model.predict(x_scaled)[0]
        probs = self.model.predict_proba(x_scaled)[0]

        return {
            "injury_risk_score": int(prediction),
            "injury_risk_class": self.label_encoder.inverse_transform([prediction])[0],
            "injury_confidence": float(np.max(probs) * 100),
            "injury_risk_factors": self._compute_risk_factors(age, bmi, has_health_conditions, previous_injury),
        }
