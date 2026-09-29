"""Graph nodes. Each node returns a partial state update and NEVER invents fake results on failure:
failures are recorded in ``errors`` and the affected section is marked ``failed``."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError

from app.domain import heuristics
from app.domain.nutrition_math import build_targets
from app.domain.profile_metrics import (
    FITNESS_CLASSES,
    age_category,
    bmi_category,
    calculate_bmi,
)
from app.domain.safety import INTENSITY_ORDER, assess_safety, cap_intensity
from app.llm.base import LLMClient, LLMError
from app.llm.prompt_loader import render, sanitize_user_text
from app.ml.predictors import FitnessPredictor, InjuryPredictor
from app.schemas.llm import (
    NormalizedInputs,
    NutritionMeals,
    NutritionPlan,
    RecoveryPlan,
    WorkoutPlan,
)
from app.schemas.profile import ProfileIn

logger = logging.getLogger(__name__)
SEVERITY_ORDER = ["none", "mild", "moderate", "severe"]


@dataclass
class Deps:
    llm: LLMClient
    fitness: FitnessPredictor
    injury: InjuryPredictor


def _err(node: str, code: str, message: str, retryable: bool = False) -> dict[str, Any]:
    return {"node": node, "code": code, "message": message, "retryable": retryable}


def _llm_failure(node: str, section: str, exc: LLMError) -> dict[str, Any]:
    logger.warning("node=%s llm_error=%s", node, exc.code)
    update: dict[str, Any] = {
        "errors": [_err(node, exc.code, exc.message, exc.retryable)],
        "sections": {section: "failed"},
    }
    if exc.fatal:
        update["fatal"] = True
    return update


def timed(name: str, fn: Callable[[dict[str, Any]], dict[str, Any]]) -> Callable[[dict[str, Any]], dict[str, Any]]:
    def wrapper(state: dict[str, Any]) -> dict[str, Any]:
        start = time.perf_counter()
        try:
            return fn(state)
        finally:
            logger.info("node=%s duration_ms=%d", name, (time.perf_counter() - start) * 1000)

    return wrapper


def _hours(state: dict[str, Any]) -> float:
    return float(state["normalized"]["schedule"]["estimated_hours_per_week"])


# --------------------------------------------------------------------------------------------------
def form_parser(state: dict[str, Any]) -> dict[str, Any]:
    try:
        profile = ProfileIn.model_validate(state.get("raw_profile") or {})
    except ValidationError as exc:
        return {
            "fatal": True,
            "errors": [
                _err("form_parser", "validation_error", f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}") for e in exc.errors()
            ],
            "sections": {"profile": "failed"},
        }
    bmi = calculate_bmi(profile.weight_kg, profile.height_cm)
    return {
        "profile": profile.model_dump(),
        "metrics": {"bmi": bmi, "bmi_category": bmi_category(bmi), "age_category": age_category(profile.age)},
        "sections": {"profile": "ok"},
    }


def make_input_normalizer(deps: Deps) -> Callable[[dict[str, Any]], dict[str, Any]]:
    def node(state: dict[str, Any]) -> dict[str, Any]:
        p = state["profile"]
        heur = heuristics.normalize_inputs(p["fitness_experience"], p["health_conditions"], p["available_hours_per_week"])
        context = {k: p[k] for k in ("fitness_experience", "health_conditions", "available_hours_per_week")}
        warnings: list[str] = []
        try:
            prompt = render(
                "normalize",
                NormalizedInputs,
                **{k: sanitize_user_text(v) for k, v in context.items()},
            )
            normalized = deps.llm.generate("normalize", prompt, NormalizedInputs, context).model_dump()
        except LLMError as exc:
            if exc.fatal:
                return _llm_failure("input_normalizer", "normalization", exc)
            normalized = heur
            warnings.append(f"AI input interpretation failed ({exc.code}); rule-based parsing was used instead.")

        # Safety-critical merge: never let the LLM *downgrade* what deterministic keyword rules found.
        health, hh = normalized["health"], heur["health"]
        if SEVERITY_ORDER.index(hh["severity_assessment"]) > SEVERITY_ORDER.index(health["severity_assessment"]):
            health["severity_assessment"] = hh["severity_assessment"]
            warnings.append("Health-condition severity was raised by rule-based screening of your notes.")
        health["cleared_for_exercise"] = bool(health["cleared_for_exercise"] and hh["cleared_for_exercise"])
        health["exercise_limitations"] = list(dict.fromkeys(health["exercise_limitations"] + hh["exercise_limitations"]))
        if not health["conditions"]:
            health["conditions"] = hh["conditions"]
        if not normalized["schedule"]["preferred_days"]:
            normalized["schedule"]["preferred_days"] = heur["schedule"]["preferred_days"]
        if normalized["schedule"]["estimated_hours_per_week"] <= 0:
            normalized["schedule"]["estimated_hours_per_week"] = 3.0
            warnings.append("No usable weekly hours were found; 3 h/week was assumed.")

        return {
            "normalized": normalized,
            "previous_injury": bool(p["previous_injury"] or heuristics.mentions_injury(p["health_conditions"])),
            "sections": {"normalization": "ok"},
            "warnings": warnings,
        }

    return node


def make_fitness_scorer(deps: Deps) -> Callable[[dict[str, Any]], dict[str, Any]]:
    def node(state: dict[str, Any]) -> dict[str, Any]:
        p, n = state["profile"], state["normalized"]
        try:
            pred = deps.fitness.predict(
                {
                    "age": p["age"], "bmi": state["metrics"]["bmi"], "weight_kg": p["weight_kg"],
                    "hours": _hours(state), "gender": p["gender"], "goal": p["fitness_goal"],
                    "experience": n["experience"]["experience_level"],
                }
            )  # fmt: skip
        except Exception as exc:
            logger.exception("fitness model failed")
            return {
                "fatal": True,
                "errors": [_err("fitness_scorer", "ml_failure", f"Fitness model unavailable: {type(exc).__name__}")],
                "sections": {"fitness": "failed"},
            }
        return {
            "fitness": {
                "level": pred.label, "confidence": pred.confidence, "probabilities": pred.probabilities,
                "drivers": pred.drivers, "notes": pred.notes,
            },
            "sections": {"fitness": "ok"},
        }  # fmt: skip

    return node


def risk_factors(age: int, bmi: float, has_conditions: bool, previous_injury: bool, hours: float, experience: str) -> list[str]:
    factors = []
    if age > 50:
        factors.append("Age above 50")
    if bmi >= 30:
        factors.append("High BMI (30+)")
    elif bmi < 18.5:
        factors.append("Low BMI (underweight)")
    if has_conditions:
        factors.append("Existing health conditions")
    if previous_injury:
        factors.append("Previous injury history")
    if hours >= 10 and experience in {"Never Exercised", "Beginner"}:
        factors.append("High training volume for your experience level")
    return factors


def make_injury_assessor(deps: Deps) -> Callable[[dict[str, Any]], dict[str, Any]]:
    def node(state: dict[str, Any]) -> dict[str, Any]:
        p, n = state["profile"], state["normalized"]
        has_conditions = bool(n["health"]["conditions"])
        try:
            pred = deps.injury.predict(
                {
                    "age": p["age"], "bmi": state["metrics"]["bmi"], "gender": p["gender"],
                    "has_health_conditions": has_conditions, "previous_injury": state["previous_injury"],
                    "hours": _hours(state), "experience": n["experience"]["experience_level"],
                    "fitness_level": state["fitness"]["level"],  # sequential: fitness always runs first
                }
            )  # fmt: skip
        except Exception as exc:
            logger.exception("injury model failed")
            return {
                "fatal": True,
                "errors": [_err("injury_assessor", "ml_failure", f"Injury-risk model unavailable: {type(exc).__name__}")],
                "sections": {"injury": "failed"},
            }
        return {
            "injury": {
                "risk": pred.label, "confidence": pred.confidence, "probabilities": pred.probabilities,
                "risk_factors": risk_factors(
                    p["age"], state["metrics"]["bmi"], has_conditions, state["previous_injury"], _hours(state),
                    n["experience"]["experience_level"],
                ),
                "drivers": pred.drivers, "notes": pred.notes,
            },
            "sections": {"injury": "ok"},
        }  # fmt: skip

    return node


def safety_guardrail(state: dict[str, Any]) -> dict[str, Any]:
    p, n = state["profile"], state["normalized"]
    safety = assess_safety(
        age=p["age"],
        bmi=state["metrics"]["bmi"],
        health_text=p["health_conditions"],
        health=n["health"],
        injury_risk=state["injury"]["risk"],
        previous_injury=state["previous_injury"],
    )
    progress = state.get("progress_context") or {}
    sessions = _target_sessions(state, safety.max_sessions_per_week)
    warnings = []
    adherence = progress.get("adherence_pct")
    if adherence is not None and adherence < 50 and sessions > 2:
        sessions -= 1
        warnings.append(
            f"Recent adherence was {adherence:.0f}%, so weekly sessions were reduced by one to make the plan sustainable."
        )
    return {"safety": safety.to_dict(), "target_sessions": sessions, "sections": {"safety": "ok"}, "warnings": warnings}


def _target_sessions(state: dict[str, Any], max_sessions: int) -> int:
    hours = _hours(state)
    sessions = int(min(max(round(hours / 1.0), 2), 6))
    preferred = state["normalized"]["schedule"]["preferred_days"]
    if 2 <= len(preferred) < sessions:
        sessions = len(preferred)
    if state["fitness"]["level"] == "Beginner":
        sessions = min(sessions, 4)
    return max(1, min(sessions, max_sessions))


def _spread(days: list[dict[str, Any]], count: int) -> list[dict[str, Any]]:
    step = len(days) / count
    return [days[int(i * step)] for i in range(count)]


def make_workout_planner(deps: Deps) -> Callable[[dict[str, Any]], dict[str, Any]]:
    def node(state: dict[str, Any]) -> dict[str, Any]:
        p, n, safety = state["profile"], state["normalized"], state["safety"]
        progress = state.get("progress_context") or {}
        target = state["target_sessions"]
        conditions = ", ".join(n["health"]["conditions"]) or "none"
        context = {
            "age": p["age"], "gender": p["gender"], "goal": p["fitness_goal"],
            "fitness_level": state["fitness"]["level"], "injury_risk": state["injury"]["risk"],
            "available_hours": _hours(state), "preferred_days": n["schedule"]["preferred_days"],
            "preferred_times": n["schedule"]["preferred_times"], "target_sessions": target,
            "max_intensity": safety["max_intensity"], "limitations": n["health"]["exercise_limitations"],
            "conditions": n["health"]["conditions"], "progress": progress, "safety_level": safety["level"],
        }  # fmt: skip
        prompt = render(
            "workout",
            WorkoutPlan,
            age=p["age"], gender=p["gender"], bmi=state["metrics"]["bmi"],
            fitness_level=context["fitness_level"], injury_risk=context["injury_risk"],
            fitness_goal=p["fitness_goal"], available_hours=context["available_hours"],
            preferred_days=", ".join(context["preferred_days"]) or "no preference",
            preferred_times=", ".join(context["preferred_times"]) or "no preference",
            health_conditions=sanitize_user_text(conditions),
            limitations=sanitize_user_text("; ".join(context["limitations"]) or "none"),
            constraints="\n".join(f"- {c}" for c in safety["constraints"]) or "- none beyond standard good practice",
            progress=_progress_text(progress), target_sessions=target, max_intensity=safety["max_intensity"].upper(),
        )  # fmt: skip
        try:
            plan = deps.llm.generate("workout", prompt, WorkoutPlan, context).model_dump()
        except LLMError as exc:
            return {**_llm_failure("workout_planner", "workout", exc), "workout": None}

        warnings: list[str] = []
        schedule = list({d["day"]: d for d in reversed(plan["weekly_schedule"])}.values())[::-1]  # first entry per day wins
        allowed = min(target, safety["max_sessions_per_week"])
        if len(schedule) > allowed:
            schedule = _spread(schedule, allowed)
            warnings.append(f"Workout days were reduced to {allowed} per week to respect safety limits and your available time.")
        order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        plan["weekly_schedule"] = sorted(schedule, key=lambda d: order.index(d["day"]))
        if plan["workout_frequency_per_week"] != len(schedule):
            plan["workout_frequency_per_week"] = len(schedule)
        capped = cap_intensity(plan["workout_intensity_level"], safety["max_intensity"])
        if capped != plan["workout_intensity_level"]:
            warnings.append(f"Workout intensity was capped at '{capped}' for safety.")
            plan["workout_intensity_level"] = capped
        if safety["requires_clearance"]:
            plan["workout_safety_notes"] = ["Obtain medical clearance BEFORE starting this plan."] + [
                s for s in plan["workout_safety_notes"] if "clearance" not in s.lower()
            ]
        return {"workout": plan, "sections": {"workout": "ok"}, "warnings": warnings}

    return node


def _progress_text(progress: dict[str, Any]) -> str:
    if not progress:
        return "No history: this is a new plan."
    bits = []
    if progress.get("adherence_pct") is not None:
        bits.append(f"adherence over the last 28 days: {progress['adherence_pct']:.0f}%")
    if progress.get("average_rpe") is not None:
        bits.append(f"average session RPE: {progress['average_rpe']:.1f}/10")
    if progress.get("weight_change_kg") is not None:
        bits.append(f"weight change: {progress['weight_change_kg']:+.1f} kg")
    if progress.get("deload_due"):
        bits.append("a DELOAD block is due: reduce volume by ~30-40% and lower intensity one step")
    bits += progress.get("notes", [])
    return "; ".join(bits) or "History available but no notable signals."


def make_nutrition_advisor(deps: Deps) -> Callable[[dict[str, Any]], dict[str, Any]]:
    def node(state: dict[str, Any]) -> dict[str, Any]:
        p, n = state["profile"], state["normalized"]
        sessions = (state.get("workout") or {}).get("workout_frequency_per_week") or state["target_sessions"]
        targets = build_targets(
            age=p["age"], weight_kg=p["weight_kg"], height_cm=p["height_cm"], gender=p["gender"],
            goal=p["fitness_goal"], bmi=state["metrics"]["bmi"], sessions_per_week=int(sessions),
        )  # fmt: skip
        plan = NutritionPlan(
            maintenance_calories=targets["maintenance_calories"],
            daily_calorie_target=targets["daily_calorie_target"],
            macro_targets=targets["macro_targets"],
            notes=targets["notes"],
        ).model_dump()
        conditions = n["health"]["conditions"]
        context = {
            "daily_calorie_target": plan["daily_calorie_target"], "macro_targets": plan["macro_targets"],
            "goal": p["fitness_goal"], "weight_kg": p["weight_kg"], "conditions": conditions, "gender": p["gender"],
        }  # fmt: skip
        prompt = render(
            "nutrition",
            NutritionMeals,
            age=p["age"], gender=p["gender"], weight_kg=p["weight_kg"], bmi=state["metrics"]["bmi"],
            fitness_goal=p["fitness_goal"], fitness_level=state["fitness"]["level"], sessions_per_week=sessions,
            health_conditions=sanitize_user_text(", ".join(conditions) or "none"),
            daily_calorie_target=plan["daily_calorie_target"], protein_g=plan["macro_targets"]["protein_g"],
            carbs_g=plan["macro_targets"]["carbs_g"], fat_g=plan["macro_targets"]["fat_g"],
            constraints="\n".join(f"- {c}" for c in state["safety"]["constraints"]) or "- none",
        )  # fmt: skip
        try:
            meals = deps.llm.generate("nutrition", prompt, NutritionMeals, context).model_dump()
        except LLMError as exc:
            failure = _llm_failure("nutrition_advisor", "nutrition", exc)
            failure["sections"] = {"nutrition": "partial"}  # targets are still valid and useful
            return {**failure, "nutrition": plan}

        for meal in meals["meal_suggestions"]:  # keep calories consistent with macros
            meal["calories"] = round(meal["protein_g"] * 4 + meal["carbs_g"] * 4 + meal["fat_g"] * 9)
        plan.update(meals)
        totals = {
            "calories": sum(m["calories"] for m in meals["meal_suggestions"]),
            "protein_g": sum(m["protein_g"] for m in meals["meal_suggestions"]),
            "carbs_g": sum(m["carbs_g"] for m in meals["meal_suggestions"]),
            "fat_g": sum(m["fat_g"] for m in meals["meal_suggestions"]),
        }
        plan["meal_totals"] = totals
        warnings = []
        target = plan["daily_calorie_target"]
        if abs(totals["calories"] - target) / target > 0.2:
            warnings.append(
                f"The suggested meals total {totals['calories']:.0f} kcal vs your {target} kcal target; treat meals as examples and scale portions."
            )
        return {"nutrition": plan, "sections": {"nutrition": "ok"}, "warnings": warnings}

    return node


def make_recovery_optimizer(deps: Deps) -> Callable[[dict[str, Any]], dict[str, Any]]:
    def node(state: dict[str, Any]) -> dict[str, Any]:
        p, n, safety = state["profile"], state["normalized"], state["safety"]
        workout = state.get("workout") or {}
        progress = state.get("progress_context") or {}
        training_days = [d["day"] for d in workout.get("weekly_schedule", [])]
        sessions = workout.get("workout_frequency_per_week") or state["target_sessions"]
        intensity = workout.get("workout_intensity_level") or safety["max_intensity"]
        conditions = n["health"]["conditions"]
        context = {
            "age": p["age"], "fitness_level": state["fitness"]["level"], "injury_risk": state["injury"]["risk"],
            "intensity": intensity, "training_days": training_days, "preferred_times": n["schedule"]["preferred_times"],
            "limitations": n["health"]["exercise_limitations"], "conditions": conditions, "progress": progress,
        }  # fmt: skip
        prompt = render(
            "recovery",
            RecoveryPlan,
            age=p["age"], fitness_level=context["fitness_level"], injury_risk=context["injury_risk"],
            health_conditions=sanitize_user_text(", ".join(conditions) or "none"),
            fitness_goal=p["fitness_goal"], sessions_per_week=sessions, intensity=intensity,
            available_hours=_hours(state), training_days=", ".join(training_days) or "not yet scheduled",
            preferred_days=", ".join(n["schedule"]["preferred_days"]) or "no preference",
            preferred_times=", ".join(n["schedule"]["preferred_times"]) or "no preference",
            constraints="\n".join(f"- {c}" for c in safety["constraints"]) or "- none",
            progress=_progress_text(progress),
        )  # fmt: skip
        try:
            plan = deps.llm.generate("recovery", prompt, RecoveryPlan, context).model_dump()
        except LLMError as exc:
            return {**_llm_failure("recovery_optimizer", "recovery", exc), "recovery": None}
        return {"recovery": plan, "sections": {"recovery": "ok"}}

    return node


__all__ = ["FITNESS_CLASSES", "INTENSITY_ORDER", "Deps"]
