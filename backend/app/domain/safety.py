"""Rule-based safety guardrail. This is deliberately NOT an ML/LLM decision."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from app.domain.heuristics import SEVERE_KEYWORDS

INTENSITY_ORDER = ["Light", "Moderate", "Vigorous"]

DISCLAIMER = (
    "AetherFit is an educational fitness-planning tool, not a medical device or a clinical screening service. "
    "Its guidance is not medical advice. Consult a qualified professional before starting or changing an "
    "exercise or nutrition programme, and stop immediately if you feel pain, dizziness or chest discomfort."
)


@dataclass
class SafetyAssessment:
    level: str = "standard"  # standard | conservative | clinician_first
    requires_clearance: bool = False
    max_intensity: str = "Vigorous"
    max_sessions_per_week: int = 6
    reasons: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)  # instructions injected into planner prompts
    disclaimer: str = DISCLAIMER

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def cap_intensity(intensity: str | None, maximum: str) -> str:
    if intensity not in INTENSITY_ORDER:
        return maximum
    return INTENSITY_ORDER[min(INTENSITY_ORDER.index(intensity), INTENSITY_ORDER.index(maximum))]


def assess_safety(
    *,
    age: int,
    bmi: float,
    health_text: str,
    health: dict[str, Any],
    injury_risk: str,
    previous_injury: bool,
) -> SafetyAssessment:
    clinician: list[str] = []
    conservative: list[str] = []
    lowered = health_text.lower()
    severity = health.get("severity_assessment", "none")

    if health.get("cleared_for_exercise") is False:
        clinician.append("The health information suggests medical clearance is needed before exercising.")
    if severity == "severe":
        clinician.append("A severe health condition was reported.")
    flagged = [k for k in SEVERE_KEYWORDS if k in lowered]
    if flagged:
        clinician.append(f"Red-flag term(s) in health notes: {', '.join(sorted(set(flagged)))}.")
    if bmi >= 40:
        clinician.append(f"BMI of {bmi:.1f} is in the very-high range.")
    if bmi < 16:
        clinician.append(f"BMI of {bmi:.1f} is in the severely-underweight range.")
    if age >= 70 and health.get("conditions"):
        clinician.append("Age 70+ combined with reported health conditions.")

    if severity == "moderate":
        conservative.append("A moderate health condition was reported.")
    if injury_risk in {"High Risk", "Very High Risk"}:
        conservative.append(f"The injury-risk model estimates '{injury_risk}'.")
    if age >= 60:
        conservative.append("Age 60+.")
    if bmi >= 35:
        conservative.append(f"BMI of {bmi:.1f} (class II obesity or higher).")
    elif bmi < 17.5:
        conservative.append(f"BMI of {bmi:.1f} (underweight).")
    if previous_injury:
        conservative.append("Previous injury history.")

    limitations = list(health.get("exercise_limitations") or [])
    if clinician:
        result = SafetyAssessment(
            level="clinician_first",
            requires_clearance=True,
            max_intensity="Light",
            max_sessions_per_week=3,
            reasons=clinician + conservative,
        )
        result.constraints = [
            "The user must obtain medical clearance first; generate only a gentle introductory plan.",
            "Use LIGHT intensity only, at most 3 sessions per week, no maximal efforts or heavy loading.",
        ]
    elif conservative:
        very_high = injury_risk == "Very High Risk" or age >= 70
        result = SafetyAssessment(
            level="conservative",
            max_intensity="Light" if very_high else "Moderate",
            max_sessions_per_week=4 if very_high else 5,
            reasons=conservative,
        )
        result.constraints = [
            f"Keep intensity at or below {result.max_intensity.upper()}; at most {result.max_sessions_per_week} sessions per week.",
            "Prioritise low-impact, joint-friendly movements and a long warm-up.",
        ]
    else:
        result = SafetyAssessment()
    result.constraints += limitations
    return result
