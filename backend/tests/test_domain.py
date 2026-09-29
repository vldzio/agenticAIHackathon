import pytest

from app.domain.nutrition_math import build_targets, macro_targets
from app.domain.profile_metrics import age_category, bmi_category, calculate_bmi, experience_from_years
from app.domain.safety import assess_safety, cap_intensity


def test_bmi_and_categories():
    assert calculate_bmi(70, 170) == pytest.approx(24.22, abs=0.01)
    assert [bmi_category(x) for x in (17, 22, 27, 33)] == ["Underweight", "Normal", "Overweight", "Obese"]
    assert bmi_category(24.95) == "Normal"
    assert [age_category(x) for x in (18, 30, 44, 45, 59, 60)] == [
        "Young Adult",
        "Adult",
        "Adult",
        "Middle Aged",
        "Middle Aged",
        "Senior",
    ]


def test_experience_mapping():
    assert experience_from_years(0.0) == "Never Exercised"
    assert experience_from_years(0.5) == "Beginner"
    assert experience_from_years(3) == "Some Experience"
    assert experience_from_years(7) == "Advanced"


@pytest.mark.parametrize("goal", ["Weight Loss", "Muscle Building", "Endurance/Cardio", "General Fitness"])
def test_macros_add_up_to_calories(goal):
    t = build_targets(age=30, weight_kg=70, height_cm=170, gender="Male", goal=goal, bmi=24.2, sessions_per_week=4)
    m = t["macro_targets"]
    total = m["protein_g"] * 4 + m["carbs_g"] * 4 + m["fat_g"] * 9
    assert abs(total - t["daily_calorie_target"]) < 20
    assert all(v > 0 for v in m.values())


def test_calorie_floor_and_underweight_no_deficit():
    t = build_targets(age=70, weight_kg=40, height_cm=150, gender="Female", goal="Weight Loss", bmi=17.8, sessions_per_week=1)
    assert t["daily_calorie_target"] >= 1200
    low = build_targets(age=40, weight_kg=45, height_cm=172, gender="Male", goal="Weight Loss", bmi=15.2, sessions_per_week=1)
    assert low["daily_calorie_target"] >= 1500
    assert low["notes"]


def test_macro_rebalance_never_negative_carbs():
    m = macro_targets(200, 1500, "Muscle Building")
    assert m["carbs_g"] > 0


def _safety(**kw):
    base = dict(
        age=30,
        bmi=23,
        health_text="None",
        health={"severity_assessment": "none", "cleared_for_exercise": True, "conditions": [], "exercise_limitations": []},
        injury_risk="Low Risk",
        previous_injury=False,
    )
    base.update(kw)
    return assess_safety(**base)


def test_standard_profile_has_no_restrictions():
    s = _safety()
    assert (s.level, s.requires_clearance, s.max_intensity) == ("standard", False, "Vigorous")


def test_clinician_first_triggers():
    assert _safety(
        health={"severity_assessment": "severe", "cleared_for_exercise": False, "conditions": ["x"], "exercise_limitations": []}
    ).requires_clearance
    assert _safety(health_text="chest pain when climbing stairs").level == "clinician_first"
    assert _safety(bmi=41).level == "clinician_first"
    assert _safety(bmi=15).level == "clinician_first"
    s = _safety(
        age=72,
        health={
            "severity_assessment": "mild",
            "cleared_for_exercise": True,
            "conditions": ["arthritis"],
            "exercise_limitations": [],
        },
    )
    assert s.level == "clinician_first" and s.max_intensity == "Light" and s.max_sessions_per_week == 3


def test_conservative_triggers():
    assert _safety(injury_risk="High Risk").level == "conservative"
    assert _safety(age=61).level == "conservative"
    assert _safety(injury_risk="Very High Risk").max_intensity == "Light"


def test_cap_intensity():
    assert cap_intensity("Vigorous", "Moderate") == "Moderate"
    assert cap_intensity("Light", "Vigorous") == "Light"
    assert cap_intensity("bogus", "Light") == "Light"
