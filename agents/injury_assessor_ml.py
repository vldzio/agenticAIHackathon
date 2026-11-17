from pathlib import Path
import pickle
import re
from typing import Any, Dict

import numpy as np


RISK_ORDER = ["Low Risk", "Moderate Risk", "High Risk", "Very High Risk"]
NOTHING_REPORTED = re.compile(r"^(no|none|nil|nothing|n/?a|not applicable|healthy)\b")
INJURY_WORDS = re.compile(
    r"injur|surger|operat|sprain|strain|tear|torn|fractur|broke|dislocat|ruptur|herniat|slipped disc|\bacl\b|meniscus|tendon"
)


class InjuryAssessorMLAgent:
    """Predicts injury risk from the trained classifier."""

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

    def _normalize_experience_label(self, raw_value: Any, years_active: Any) -> str:
        years = 0.0
        try:
            if years_active is not None:
                years = max(float(years_active), 0.0)
        except (TypeError, ValueError):
            years = 0.0

        normalized = str(raw_value or "").strip().lower()
        if years >= 5:
            return "Advanced"
        if years >= 1:
            return "Some Experience"
        if normalized in {"advanced", "athlete"}:
            return "Advanced"
        if normalized in {"intermediate", "some experience"}:
            return "Some Experience"
        if normalized in {"never exercised", "none", "no experience"}:
            return "Never Exercised"
        if normalized == "beginner":
            return "Beginner"
        return "Beginner" if years > 0 else "Never Exercised"

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

    def _health_flags(self, user_profile: Dict[str, Any]) -> tuple[int, int]:
        """Return (has_health_conditions, previous_injury), the model's two strongest inputs.

        An injury alone sets only previous_injury, and an illness alone only
        has_health_conditions, matching how the training data separates them. The
        normalizer's condition list is used when present, otherwise the raw text.
        """
        normalized = user_profile.get("normalized_health_conditions") or {}
        items = normalized.get("conditions", normalized.get("condtions"))  # the prompt spells the key "condtions"
        if not isinstance(items, list):
            text = str(user_profile.get("health_conditions") or "")
            items = re.split(r"[,;.\n]|\band\b", text)
        items = [str(item).strip().lower() for item in items]
        items = [item for item in items if item and not NOTHING_REPORTED.match(item)]

        injuries = [item for item in items if INJURY_WORDS.search(item)]
        previous_injury = 1 if injuries or str(user_profile.get("injury_history") or "").strip() else 0
        has_health_conditions = 1 if len(items) > len(injuries) else 0
        return has_health_conditions, previous_injury

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
        experience = self._normalize_experience_label(
            user_profile.get("fitness_experience_level") or user_profile.get("fitness_experience"),
            user_profile.get("fitness_years_active"),
        )
        hours = float(user_profile.get("available_hours_per_week", 3))
        has_health_conditions, previous_injury = self._health_flags(user_profile)

        # Only inputs the app really collects (no flexibility or strength-imbalance measurements, and
        # no fitness level: that model runs in parallel, so its result is not available here).
        features = {
            "Age": age,
            "BMI": bmi,
            "Gender": gender,
            "Fitness_Experience": experience,
            "Has_Health_Conditions": has_health_conditions,
            "Previous_Injury": previous_injury,
            "Training_Frequency_Hours": hours,
        }

        x_scaled = self.scaler.transform(self._encode_features(features))
        probs = self.model.predict_proba(x_scaled)[0]
        prediction = self.model.classes_[int(np.argmax(probs))]
        label = str(self.label_encoder.inverse_transform([prediction])[0])

        return {
            "injury_risk_score": RISK_ORDER.index(label),
            "injury_risk_class": label,
            "injury_confidence": float(np.max(probs) * 100),
            "injury_risk_factors": self._compute_risk_factors(age, bmi, has_health_conditions, previous_injury),
        }
