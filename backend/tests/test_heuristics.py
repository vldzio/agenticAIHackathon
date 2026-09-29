import pytest

from app.domain import heuristics as h


@pytest.mark.parametrize(
    ("text", "level", "years"),
    [
        ("Beginner, training 3 times per week", "Beginner", None),
        ("10 years competitive powerlifter", "Advanced", 10),
        ("never exercised", "Never Exercised", 0),
        ("6 months of jogging", "Beginner", 0.5),
        ("about 2 years at the gym", "Some Experience", 2),
        ("five years of crossfit", "Advanced", 5),
    ],
)
def test_experience(text, level, years):
    parsed = h.parse_experience(text)
    assert parsed["experience_level"] == level
    if years is not None:
        assert parsed["years_active"] == pytest.approx(years)


@pytest.mark.parametrize(
    ("text", "hours", "assumed"),
    [
        ("4-5 hours, weekday mornings", 4.5, False),
        ("12 hours", 12, False),
        ("30 minutes a day", 3.5, False),
        ("3 sessions of 1.5 hours", 4.5, False),
        ("whenever", 3.0, True),
    ],
)
def test_hours(text, hours, assumed):
    value, was_assumed = h.parse_hours(text)
    assert value == pytest.approx(hours)
    assert was_assumed is assumed


def test_days_and_times():
    assert h.parse_days("Tue/Thu/Sat evenings") == ["Tuesday", "Thursday", "Saturday"]
    assert h.parse_days("weekdays") == h.WEEKDAYS[:5]
    assert h.parse_times("mornings or after work") == ["Morning", "Evening"]


def test_health_severity_and_limitations():
    assert h.parse_health("None")["severity_assessment"] == "none"
    knee = h.parse_health("knee injury, hypertension")
    assert knee["severity_assessment"] == "moderate"
    assert any("knee" in x.lower() for x in knee["exercise_limitations"])
    severe = h.parse_health("heart attack last year")
    assert severe["severity_assessment"] == "severe"
    assert severe["cleared_for_exercise"] is False


def test_injury_mentions():
    assert h.mentions_injury("torn ACL")
    assert not h.mentions_injury("No injuries")
    assert not h.mentions_injury("none")
