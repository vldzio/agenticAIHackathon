"""Deterministic, input-aware plan generators used by Mock mode (and as the test double).

They consume the *structured* ``context`` passed by the graph nodes, so results change with the user's
profile: goal, fitness level, hours, preferred days, injuries/limitations and progress history.
"""

from __future__ import annotations

from typing import Any

from app.domain.heuristics import WEEKDAYS, normalize_inputs

DEFAULT_SPREAD = {
    1: ["Wednesday"],
    2: ["Monday", "Thursday"],
    3: ["Monday", "Wednesday", "Friday"],
    4: ["Monday", "Tuesday", "Thursday", "Friday"],
    5: ["Monday", "Tuesday", "Wednesday", "Friday", "Saturday"],
    6: ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"],
    7: WEEKDAYS,
}

# (name, equipment, restricted_by tags, kind) -- restricted_by: knee | overhead | spine | impact
LIB: dict[str, list[tuple[str, str | None, tuple[str, ...]]]] = {
    "legs": [
        ("Bodyweight Squat", None, ("knee",)),
        ("Goblet Squat", "Dumbbell", ("knee",)),
        ("Reverse Lunge", None, ("knee",)),
        ("Glute Bridge", None, ()),
        ("Romanian Deadlift", "Dumbbells", ("spine",)),
        ("Step-ups (low box)", "Box or step", ("knee",)),
        ("Hip Thrust", "Bench", ()),
        ("Calf Raises", None, ()),
    ],
    "push": [
        ("Incline Push-ups", None, ()),
        ("Push-ups", None, ()),
        ("Dumbbell Bench Press", "Dumbbells, bench", ()),
        ("Dumbbell Shoulder Press", "Dumbbells", ("overhead",)),
        ("Triceps Dips (bench)", "Bench", ("overhead",)),
        ("Lateral Raises", "Dumbbells", ("overhead",)),
        ("Chest Fly", "Dumbbells, bench", ()),
    ],
    "pull": [
        ("Dumbbell Row", "Dumbbell", ("spine",)),
        ("Resistance Band Pull-apart", "Resistance band", ()),
        ("Lat Pulldown (or band)", "Cable or band", ()),
        ("Face Pulls", "Resistance band", ()),
        ("Biceps Curl", "Dumbbells", ()),
        ("Inverted Row", "Bar or table", ("spine",)),
    ],
    "core": [
        ("Plank", None, ()),
        ("Dead Bug", None, ()),
        ("Bird Dog", None, ()),
        ("Side Plank", None, ()),
        ("Pallof Press", "Resistance band", ()),
    ],
    "cardio": [
        ("Brisk Walk", None, ()),
        ("Stationary Bike Intervals", "Stationary bike", ()),
        ("Easy Jog", None, ("impact", "knee")),
        ("Rowing Machine", "Rowing machine", ("spine",)),
        ("Jump Rope", "Jump rope", ("impact", "knee")),
        ("Swimming (easy laps)", "Pool access", ()),
    ],
    "mobility": [
        ("Cat-Cow", None, ()),
        ("Hip Flexor Stretch", None, ()),
        ("Thoracic Rotation", None, ()),
        ("World's Greatest Stretch", None, ()),
    ],
}

SPLITS = {
    "full": [("Full body A", ["legs", "push", "pull", "core"]), ("Full body B", ["legs", "pull", "push", "core"])],
    "ul": [("Upper body", ["push", "pull", "core"]), ("Lower body", ["legs", "core", "mobility"])],
    "ppl": [("Push", ["push", "core"]), ("Pull", ["pull", "core"]), ("Legs", ["legs", "core"])],
    "cardio": [("Aerobic base", ["cardio", "mobility"]), ("Intervals + strength", ["cardio", "legs", "core"]), ("Long easy session", ["cardio", "mobility"])],
}  # fmt: skip


def _restrictions(limitations: list[str], conditions: list[str]) -> set[str]:
    text = " ".join(limitations + conditions).lower()
    tags: set[str] = set()
    if any(k in text for k in ("knee", "ankle", "hip")):
        tags.add("knee")
    if "shoulder" in text or "overhead" in text:
        tags.add("overhead")
    if any(k in text for k in ("back", "spine", "disc", "sciatica")):
        tags.add("spine")
    if "impact" in text or "jump" in text or "knee" in text or "obes" in text:
        tags.add("impact")
    return tags


def _pick_days(preferred: list[str], sessions: int) -> list[str]:
    preferred = [d for d in WEEKDAYS if d in preferred]
    if len(preferred) >= sessions:
        # keep them spread out: take evenly spaced entries of the preferred list
        step = len(preferred) / sessions
        return [preferred[int(i * step)] for i in range(sessions)]
    days = list(preferred)
    for d in DEFAULT_SPREAD.get(sessions, WEEKDAYS[:sessions]):
        if len(days) == sessions:
            break
        if d not in days:
            days.append(d)
    for d in WEEKDAYS:
        if len(days) == sessions:
            break
        if d not in days:
            days.append(d)
    return [d for d in WEEKDAYS if d in days]


def _choose_split(goal: str, sessions: int) -> list[tuple[str, list[str]]]:
    goal_l = goal.lower()
    if "endurance" in goal_l:
        key = "cardio"
    elif sessions <= 3:
        key = "full"
    elif sessions == 4:
        key = "ul"
    else:
        key = "ppl"
    return SPLITS[key]


def _scheme(goal: str, level: str, deload: bool) -> tuple[int, str, str]:
    goal_l = goal.lower()
    tier = {"Beginner": 0, "Intermediate": 1, "Advanced": 2, "Athlete": 2}.get(level, 0)
    sets = 2 + (1 if tier >= 1 else 0) + (1 if tier == 2 and "muscle" in goal_l else 0)
    if "muscle" in goal_l:
        reps, rest = "8-12", "90 sec"
    elif "weight loss" in goal_l:
        reps, rest = "12-15", "45 sec"
    elif "endurance" in goal_l:
        reps, rest = "15-20", "45 sec"
    else:
        reps, rest = "10-12", "60 sec"
    if deload:
        sets = max(2, sets - 1)
    return sets, reps, rest


def mock_workout(ctx: dict[str, Any]) -> dict[str, Any]:
    sessions = int(ctx["target_sessions"])
    level = ctx["fitness_level"]
    goal = ctx["goal"]
    progress = ctx.get("progress") or {}
    deload = bool(progress.get("deload_due"))
    restricted = _restrictions(ctx.get("limitations", []), ctx.get("conditions", []))
    days = _pick_days(ctx.get("preferred_days", []), sessions)
    split = _choose_split(goal, sessions)
    sets, reps, rest = _scheme(goal, level, deload)
    tier_count = {"Beginner": 1, "Intermediate": 2, "Advanced": 2, "Athlete": 3}.get(level, 1)

    equipment: set[str] = set()
    schedule = []
    used: dict[str, int] = {}
    for i, day in enumerate(days):
        focus, groups = split[i % len(split)]
        exercises = []
        for group in groups:
            pool = [e for e in LIB[group] if not (set(e[2]) & restricted)] or [LIB[group][-1]]
            n = tier_count if group in {"legs", "push", "pull"} else 1
            for _ in range(n):
                idx = used.get(group, 0)
                name, equip, _tags = pool[idx % len(pool)]
                used[group] = idx + 1
                if equip:
                    equipment.add(equip)
                if group == "cardio":
                    exercises.append(
                        {
                            "exercise_name": name,
                            "sets": 1,
                            "reps": "20-30 min" if level == "Beginner" else "30-40 min",
                            "rest_period": "n/a",
                            "notes": "Conversational pace",
                        }
                    )
                elif group in {"core", "mobility"} and name in {
                    "Plank",
                    "Side Plank",
                    "Cat-Cow",
                    "Hip Flexor Stretch",
                    "Thoracic Rotation",
                    "World's Greatest Stretch",
                }:
                    exercises.append(
                        {
                            "exercise_name": name,
                            "sets": 2 if group == "core" else 1,
                            "reps": "30-45 sec" if group == "core" else "8 each side",
                            "rest_period": "30 sec",
                            "notes": None,
                        }
                    )
                else:
                    exercises.append({"exercise_name": name, "sets": sets, "reps": reps, "rest_period": rest, "notes": None})
        if "weight loss" in goal.lower() and "impact" not in restricted and "cardio" not in groups:
            exercises.append(
                {"exercise_name": "Brisk Walk", "sets": 1, "reps": "10-15 min", "rest_period": "n/a", "notes": "Finisher"}
            )
        schedule.append({"day": day, "focus": focus, "exercises": exercises[:10]})

    base_intensity = {"Beginner": "Light", "Intermediate": "Moderate", "Advanced": "Vigorous", "Athlete": "Vigorous"}.get(
        level, "Light"
    )
    intensity = ["Light", "Moderate", "Vigorous"]
    idx = min(intensity.index(base_intensity), intensity.index(ctx.get("max_intensity", "Vigorous")))
    if deload:
        idx = max(0, idx - 1)
    hours = float(ctx.get("available_hours") or 3)
    duration = int(max(20, min(90, round((hours * 60 / max(sessions, 1) - 5) / 5) * 5)))

    notes = [
        "Warm up for 5-10 minutes before every session and cool down afterwards.",
        "Prioritise controlled form over load; stop if you feel sharp pain.",
    ]
    risk = ctx.get("injury_risk", "")
    if risk in {"High Risk", "Very High Risk"}:
        notes.append(
            f"Injury risk is estimated as '{risk}': progress loads by no more than ~5% per week and keep 48 hours between similar sessions."
        )
    notes += [n for n in ctx.get("limitations", [])][:3]
    if deload:
        notes.append("This is a DELOAD block: volume reduced to help recovery.")
    if ctx.get("safety_level") == "clinician_first":
        notes.append("Get medical clearance before starting this plan.")
    return {
        "weekly_schedule": schedule,
        "workout_intensity_level": intensity[idx],
        "workout_frequency_per_week": len(schedule),
        "workout_duration_per_session": duration,
        "workout_progression_timeline": "6 weeks"
        if level == "Beginner"
        else "8 weeks"
        if level == "Intermediate"
        else "12 weeks",
        "workout_safety_notes": notes,
        "workout_equipment_needed": sorted(equipment),
    }


def mock_nutrition(ctx: dict[str, Any]) -> dict[str, Any]:
    macros = ctx["macro_targets"]
    conditions = " ".join(ctx.get("conditions", [])).lower()
    goal = ctx["goal"].lower()
    meals_def = [
        ("Breakfast", 0.25, ["Vegetable oats upma or masala oats", "Boiled eggs or Greek yogurt", "Banana"]),
        ("Lunch", 0.32, ["Brown rice or 2 rotis", "Dal or chicken/paneer curry", "Cucumber-tomato salad"]),
        ("Snack", 0.13, ["Roasted chana", "Fruit", "Buttermilk"]),
        ("Dinner", 0.30, ["Grilled fish, chicken or tofu", "Sauteed vegetables", "1 roti or small portion of rice"]),
    ]
    if "muscle" in goal:
        meals_def[2] = ("Snack", 0.13, ["Sprouts salad or peanut chikki", "Milk or whey-free protein shake", "Banana"])
    meals = []
    for name, share, foods in meals_def:
        protein, carbs, fat = (round(macros[k] * share) for k in ("protein_g", "carbs_g", "fat_g"))
        meals.append(
            {
                "meal_name": name,
                "foods": foods,
                "protein_g": protein,
                "carbs_g": carbs,
                "fat_g": fat,
                "calories": round(protein * 4 + carbs * 4 + fat * 9),
            }
        )
    liters = round(ctx.get("weight_kg", 70) * 0.035 * 2) / 2
    timing = "Have a light carbohydrate snack (e.g. banana) 45-60 minutes before training and a protein + carbohydrate meal within 1-2 hours afterwards."
    if "diabetes" in conditions:
        timing += " Prefer low-glycaemic carbohydrates and check your glucose plan with your clinician."
    return {
        "meal_suggestions": meals,
        "hydration_recommendation": f"Aim for about {liters:g} litres of water per day, more on training days and in hot weather.",
        "nutrition_timing_guidance": timing,
    }


def mock_recovery(ctx: dict[str, Any]) -> dict[str, Any]:
    age = int(ctx["age"])
    intensity = ctx.get("intensity", "Moderate")
    risk = ctx.get("injury_risk", "")
    progress = ctx.get("progress") or {}
    sleep = 8.5 if (age < 25 or intensity == "Vigorous") else 7.5 if age >= 65 else 8.0
    restricted = _restrictions(ctx.get("limitations", []), ctx.get("conditions", []))
    mobility = ["Cat-Cow (2 x 10)", "Hip flexor stretch (2 x 30 sec per side)", "Thoracic rotation (2 x 8 per side)"]
    if "spine" in restricted:
        mobility.append("Pelvic tilts and gentle lumbar mobility (avoid loaded flexion)")
    if "knee" in restricted:
        mobility.append("Quad and hamstring stretches within a pain-free range")
    if "overhead" in restricted:
        mobility.append("Scapular wall slides within a pain-free range")
    high_risk = risk in {"High Risk", "Very High Risk"}
    deload = "Every 4-6 weeks reduce total sets by ~30-40% and keep loads at ~80% for one week; take an extra rest day if soreness lasts more than 72 hours."
    if progress.get("deload_due"):
        deload = (
            "A deload is due now: this week cut sets by ~30-40%, keep loads at ~80% and focus on technique and mobility. "
            + deload
        )
    adherence = progress.get("adherence_pct")
    adherence_tips = [
        "Focus on small weekly wins and track each completed session.",
        "Review progress every Sunday and adjust the next week.",
    ]
    if adherence is not None and adherence < 60:
        adherence_tips.insert(
            0, f"Adherence has been {adherence:.0f}% recently: shorten sessions to 20-30 minutes rather than skipping them."
        )
    days = ctx.get("training_days", [])
    return {
        "sleep_recommendations": {
            "hours_per_night": sleep,
            "sleep_quality_tips": [
                "Keep a consistent sleep and wake time",
                "Avoid screens and heavy meals 60 minutes before bed",
                "Keep the room cool and dark",
            ],
        },
        "rest_day_activities": ["Easy walk (20-30 minutes)", "Light stretching or yoga"]
        + (["Gentle swimming or cycling"] if high_risk else []),
        "mobility_work": mobility,
        "stress_management_techniques": [
            "Box breathing (4-4-4-4) for 5 minutes",
            "10 minutes of mindfulness or a short walk outdoors",
        ],
        "recovery_techniques": [
            "Foam rolling major muscle groups (5-10 minutes)",
            "Contrast or warm shower after hard sessions",
            "Protein and carbohydrates within 2 hours of training",
        ],
        "deload_strategy": deload,
        "schedule_integration": {
            "best_days": days or ["Monday", "Wednesday", "Friday"],
            "best_times": ctx.get("preferred_times") or ["Morning"],
            "weekly_schedule_tips": "Keep at least one full rest day between demanding sessions and leave the day before your hardest session light.",
        },
        "time_management_tips": [
            "Prepare training clothes and meals the night before",
            "Block sessions in your calendar like appointments",
        ],
        "habit_formation_strategies": [
            "Anchor training to an existing routine (e.g. right after morning coffee)",
            "Start with the minimum viable session on low-energy days",
        ],
        "adherence_tips": adherence_tips,
    }


def mock_normalize(ctx: dict[str, Any]) -> dict[str, Any]:
    return normalize_inputs(ctx["fitness_experience"], ctx["health_conditions"], ctx["available_hours_per_week"])


GENERATORS = {
    "normalize": mock_normalize,
    "workout": mock_workout,
    "nutrition": mock_nutrition,
    "recovery": mock_recovery,
}
