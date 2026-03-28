from pathlib import Path
import pickle
from typing import Any, Dict

import numpy as np


class FitnessScorerMLAgent:
    """Classifies fitness level using the trained RandomForest model."""

    CLASS_NAMES = ["Beginner", "Intermediate", "Advanced", "Athlete"]

    def __init__(self, model_dir: str = "ml/models"):
        base_dir = Path(__file__).resolve().parent.parent
        model_root = Path(model_dir)
        if not model_root.is_absolute():
            model_root = base_dir / model_root

        with open(model_root / "fitness_level_model.pkl", "rb") as model_file:
            self.model = pickle.load(model_file)
        with open(model_root / "fitness_level_scaler.pkl", "rb") as scaler_file:
            self.scaler = pickle.load(scaler_file)
        with open(model_root / "fitness_level_encoder.pkl", "rb") as encoder_file:
            self.encoder = pickle.load(encoder_file)
        if hasattr(self.model, "n_jobs"):
            self.model.n_jobs = 1

    def _get_hours_category(self, available_hours: float) -> str:
        if available_hours < 3:
            return "Minimal"
        if available_hours < 6:
            return "Moderate"
        if available_hours < 10:
            return "High"
        return "Athletic"

    def predict_fitness_level(self, user_profile: Dict[str, Any]) -> Dict[str, Any]:
        available_hours = float(user_profile.get("available_hours_per_week", 3))
        experience_level = user_profile.get("fitness_experience_level") or user_profile.get("fitness_experience") or "Beginner"

        features = {
            "Age": int(user_profile["age"]),
            "BMI": float(user_profile["bmi"]),
            "Weight_KG": float(user_profile["weight_kg"]),
            "Available_Hours_Per_Week": available_hours,
            "Gender": user_profile["gender"],
            "Fitness_Experience": experience_level,
            "Age_Category": user_profile["age_category"],
            "Fitness_Goal": user_profile["fitness_goal"],
            "BMI_Category": user_profile["bmi_category"],
            "Hours_Category": self._get_hours_category(available_hours),
            "Activity_Score": min(100, available_hours * 15),
        }

        encoded_values = []
        for col in self.encoder["feature_columns"]:
            value = features[col]
            if col in self.encoder["feature_encoders"]:
                encoder = self.encoder["feature_encoders"][col]
                if value not in encoder.classes_:
                    value = encoder.classes_[0]
                value = encoder.transform([value])[0]
            encoded_values.append(value)

        x = np.array(encoded_values, dtype=float).reshape(1, -1)
        x_scaled = self.scaler.transform(x)
        prediction = self.model.predict(x_scaled)[0]
        probs = self.model.predict_proba(x_scaled)[0]

        return {
            "fitness_level_score": float(prediction),
            "fitness_level_class": self.CLASS_NAMES[int(prediction)],
            "fitness_confidence": float(np.max(probs) * 100),
        }
