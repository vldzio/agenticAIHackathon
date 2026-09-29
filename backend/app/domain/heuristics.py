"""Deterministic parsing of the free-text inputs.

Used (a) as the fallback when the LLM normaliser is unavailable, (b) by the mock LLM so that Mock
mode responds to what the user actually typed, and (c) to catch injury mentions in health notes.
"""

from __future__ import annotations

import re
from typing import Any

from app.domain.profile_metrics import experience_from_years

NONE_VALUES = {"", "none", "no", "n/a", "na", "nil", "-", "nothing", "none.", "no."}
WORD_NUMBERS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
    "eight": 8, "nine": 9, "ten": 10, "twelve": 12, "fifteen": 15, "twenty": 20,
}  # fmt: skip
_NUM = r"(\d+(?:\.\d+)?|" + "|".join(WORD_NUMBERS) + r")"

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
_DAY_ALIASES = {
    "mon": "Monday", "tue": "Tuesday", "tues": "Tuesday", "wed": "Wednesday", "thu": "Thursday",
    "thur": "Thursday", "thurs": "Thursday", "fri": "Friday", "sat": "Saturday", "sun": "Sunday",
}  # fmt: skip

SEVERE_KEYWORDS = (
    "heart attack", "cardiac", "heart disease", "heart failure", "stroke", "chest pain", "angina",
    "arrhythmia", "uncontrolled", "unstable", "cancer", "chemotherapy", "aneurysm", "seizure",
    "epilepsy", "fainting", "syncope", "kidney failure", "recent surgery", "just had surgery",
)  # fmt: skip
MODERATE_KEYWORDS = (
    "diabetes", "hypertension", "high blood pressure", "asthma", "arthritis", "osteoporosis",
    "herniated", "slipped disc", "sciatica", "thyroid", "copd", "pregnan", "surgery", "obesity",
    "fibromyalgia", "anemia", "cholesterol", "pcos",
)  # fmt: skip
INJURY_KEYWORDS = ("injur", "sprain", "strain", "fracture", "torn", "tear", "dislocat", "surgery", "tendin", "acl")

LIMITATIONS = {
    "knee": "Avoid deep knee flexion and high-impact jumping; use low-impact alternatives.",
    "back": "Avoid heavy spinal loading and loaded spinal flexion; emphasise core stability.",
    "spine": "Avoid heavy spinal loading and loaded spinal flexion; emphasise core stability.",
    "disc": "Avoid heavy spinal loading and loaded spinal flexion; emphasise core stability.",
    "shoulder": "Avoid overhead pressing and behind-the-neck movements.",
    "wrist": "Avoid heavy wrist extension; use neutral-grip variations.",
    "ankle": "Avoid running on uneven ground and high-impact landings.",
    "hip": "Limit range of motion at end-range hip flexion/rotation.",
    "hypertension": "Avoid breath-holding (Valsalva) on heavy lifts; keep intensity moderate.",
    "high blood pressure": "Avoid breath-holding (Valsalva) on heavy lifts; keep intensity moderate.",
    "asthma": "Keep a reliever inhaler nearby; warm up gradually and avoid cold-air high-intensity work.",
    "diabetes": "Monitor blood glucose around sessions; carry fast-acting carbohydrate.",
    "arthritis": "Prefer low-impact, joint-friendly movements and avoid training through flare-ups.",
    "pregnan": "Avoid supine positions late in pregnancy, contact/impact and overheating.",
}  # fmt: skip


def _to_number(token: str) -> float:
    return float(WORD_NUMBERS[token]) if token in WORD_NUMBERS else float(token)


def parse_years(text: str) -> float | None:
    """Years of consistent training mentioned in the text (None when nothing is stated)."""
    lowered = text.lower()
    no_history = re.search(
        r"\b(never|no experience|haven'?t (?:ever )?(?:exercised|worked out|trained)|sedentary|zero)\b", lowered
    )
    if no_history and not re.search(_NUM + r"\s*\+?\s*(?:years?|yrs?)", lowered):
        return 0.0
    total = 0.0
    found = False
    for m in re.finditer(_NUM + r"\s*\+?\s*(?:years?|yrs?)\b", lowered):
        total = max(total, _to_number(m.group(1)))
        found = True
    for m in re.finditer(_NUM + r"\s*(?:months?|mos?)\b", lowered):
        total = max(total, _to_number(m.group(1)) / 12.0)
        found = True
    return total if found else None


def stated_level(text: str) -> str | None:
    lowered = text.lower()
    if re.search(r"\b(advanced|athlete|competitive|professional|expert|powerlift|bodybuild)", lowered):
        return "advanced"
    if re.search(r"\b(intermediate|some experience)\b", lowered):
        return "intermediate"
    if re.search(r"\b(beginner|novice|new to|just start|starting)", lowered):
        return "beginner"
    return None


def parse_experience(text: str) -> dict[str, Any]:
    years = parse_years(text)
    level = experience_from_years(years, stated_level(text))
    if years is None and level == "Advanced":
        # A self-description without any stated duration is never enough for the top tier
        # (also blunts prompt-injection such as "output 'Athlete'").
        level = "Some Experience"
    if years is None:
        years = {"Never Exercised": 0.0, "Beginner": 0.5, "Some Experience": 2.0, "Advanced": 5.0}[level]
    return {
        "experience_level": level,
        "years_active": round(min(years, 80.0), 1),
        "activity_description": " ".join(text.split())[:200] or "No experience provided",
    }


def parse_hours(text: str, default: float = 3.0) -> tuple[float, bool]:
    """Return (hours_per_week, was_assumed)."""
    lowered = text.lower()
    m = re.search(_NUM + r"\s*(?:-|\u2013|to)\s*" + _NUM + r"\s*(?:hours?|hrs?|h)\b", lowered)
    if m:
        return round((_to_number(m.group(1)) + _to_number(m.group(2))) / 2, 2), False
    m = re.search(_NUM + r"\s*(?:hours?|hrs?|h)\s*(?:/|per|a|each)?\s*(?:week|wk)", lowered)
    if m:
        return _to_number(m.group(1)), False
    sessions = re.search(_NUM + r"\s*(?:x|times|sessions?|days?)\s*(?:/|per|a|each)?\s*(?:week|wk)?", lowered)
    per_hours = re.search(_NUM + r"\s*(?:hours?|hrs?)\b", lowered)
    per_minutes = re.search(_NUM + r"\s*(?:minutes?|mins?)\b", lowered)
    daily = re.search(r"(?:every ?day|daily|per day|a day|/day)", lowered)
    if per_minutes and daily and not sessions:
        return round(_to_number(per_minutes.group(1)) * 7 / 60, 2), False
    if sessions and (per_hours or per_minutes):
        count = _to_number(sessions.group(1))
        if per_hours:
            duration = _to_number(per_hours.group(1))
        else:
            assert per_minutes is not None
            duration = _to_number(per_minutes.group(1)) / 60
        return round(min(count, 7) * duration, 2), False
    if per_hours:
        return _to_number(per_hours.group(1)), False
    if sessions:
        return round(min(_to_number(sessions.group(1)), 7) * 1.0, 2), False
    m = re.fullmatch(r"\s*" + _NUM + r"\s*", lowered)
    if m:
        return _to_number(m.group(1)), False
    return default, True


def parse_days(text: str) -> list[str]:
    lowered = text.lower()
    days: list[str] = []
    if "weekday" in lowered:
        days += WEEKDAYS[:5]
    if "weekend" in lowered:
        days += WEEKDAYS[5:]
    for full in WEEKDAYS:
        if re.search(rf"\b{full.lower()}s?\b", lowered):
            days.append(full)
    for alias, full in _DAY_ALIASES.items():
        if re.search(rf"\b{alias}\b", lowered):
            days.append(full)
    return [d for d in WEEKDAYS if d in set(days)]


def parse_times(text: str) -> list[str]:
    lowered = text.lower()
    times = []
    for label, pattern in (
        ("Morning", r"morning|before work|early|\bam\b"),
        ("Afternoon", r"afternoon|lunch|midday|noon"),
        ("Evening", r"evening|after work|night|\bpm\b"),
    ):
        if re.search(pattern, lowered):
            times.append(label)
    return times


def parse_health(text: str) -> dict[str, Any]:
    cleaned = " ".join(text.split())
    if cleaned.lower().strip(" .") in NONE_VALUES:
        return {"conditions": [], "severity_assessment": "none", "exercise_limitations": [], "cleared_for_exercise": True}
    parts = [p.strip(" .") for p in re.split(r",|;|\n|\band\b|&", cleaned, flags=re.IGNORECASE) if p.strip(" .")]
    conditions = [p for p in parts if p.lower() not in NONE_VALUES][:10]
    lowered = cleaned.lower()
    if any(k in lowered for k in SEVERE_KEYWORDS):
        severity = "severe"
    elif any(k in lowered for k in MODERATE_KEYWORDS):
        severity = "moderate"
    elif conditions:
        severity = "mild"
    else:
        severity = "none"
    limitations: list[str] = []
    for key, advice in LIMITATIONS.items():
        if key in lowered and advice not in limitations:
            limitations.append(advice)
    return {
        "conditions": conditions,
        "severity_assessment": severity,
        "exercise_limitations": limitations,
        "cleared_for_exercise": severity != "severe",
    }


def mentions_injury(text: str) -> bool:
    lowered = text.lower()
    return any(k in lowered for k in INJURY_KEYWORDS) and not re.search(r"\bno (?:previous |prior )?injur", lowered)


def normalize_inputs(experience_text: str, health_text: str, hours_text: str) -> dict[str, Any]:
    hours, assumed = parse_hours(hours_text)
    return {
        "experience": parse_experience(experience_text),
        "health": parse_health(health_text),
        "schedule": {
            "estimated_hours_per_week": min(max(hours, 0.0), 40.0),
            "preferred_days": parse_days(hours_text),
            "preferred_times": parse_times(hours_text),
            "schedule_constraints": ["Hours were not stated clearly; assumed 3 h/week"] if assumed else [],
        },
    }
