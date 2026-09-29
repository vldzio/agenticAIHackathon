from __future__ import annotations

import datetime as dt
from collections import Counter

from app.db.models import ProgressLogRow
from app.schemas.assessment import Assessment, ProgressContext
from app.schemas.progress import ProgressSummary, WeekAdherence


def _monday(d: dt.date) -> dt.date:
    return d - dt.timedelta(days=d.weekday())


def summarize(assessment: Assessment, logs: list[ProgressLogRow], today: dt.date | None = None) -> ProgressSummary:
    today = today or dt.date.today()
    created = assessment.created_at.date()
    planned = assessment.workout.workout_frequency_per_week if assessment.workout else 0
    weeks_on_plan = max((today - created).days, 0) / 7

    sessions = [log for log in logs if log.kind == "session" and log.completed]
    recent = [log for log in sessions if 0 <= (today - log.logged_on).days < 28]
    effective_weeks = min(4.0, max(weeks_on_plan, 1.0))
    adherence = round(min(100.0, len(recent) / (planned * effective_weeks) * 100), 1) if planned else None
    rpes = [log.rpe for log in recent if log.rpe]
    avg_rpe = round(sum(rpes) / len(rpes), 1) if rpes else None

    weights = sorted((log.logged_on, log.weight_kg) for log in logs if log.kind == "weight" and log.weight_kg)
    latest_weight = weights[-1][1] if weights else None
    change = round(latest_weight - assessment.profile.weight_kg, 1) if latest_weight is not None else None

    per_week = Counter(_monday(log.logged_on) for log in sessions)
    this_monday = _monday(today)
    weekly = [
        WeekAdherence(
            week_start=this_monday - dt.timedelta(weeks=i),
            sessions=per_week.get(this_monday - dt.timedelta(weeks=i), 0),
            planned=planned,
        )
        for i in range(7, -1, -1)
    ]

    notes: list[str] = []
    deload_due = weeks_on_plan >= 5 or (avg_rpe is not None and avg_rpe >= 8.5 and len(rpes) >= 3)
    if weeks_on_plan >= 5:
        notes.append(f"You have been on this plan for about {weeks_on_plan:.0f} weeks; a deload week is due.")
    if avg_rpe is not None and avg_rpe >= 8.5 and len(rpes) >= 3:
        notes.append(f"Sessions have felt very hard (average RPE {avg_rpe}); lower the load to avoid overtraining.")
    if adherence is not None and adherence < 50 and weeks_on_plan >= 1:
        notes.append("Adherence is below 50%; a shorter, more achievable plan will be suggested.")
    return ProgressSummary(
        assessment_id=assessment.id,
        planned_sessions_per_week=planned,
        sessions_last_28_days=len(recent),
        adherence_pct=adherence,
        average_rpe=avg_rpe,
        latest_weight_kg=latest_weight,
        weight_change_kg=change,
        weeks_on_plan=round(weeks_on_plan, 1),
        deload_due=deload_due,
        weekly=weekly,
        weights=[(d, w) for d, w in weights],
        notes=notes,
    )


def to_context(summary: ProgressSummary) -> ProgressContext:
    return ProgressContext(
        weeks_on_plan=summary.weeks_on_plan,
        sessions_last_28_days=summary.sessions_last_28_days,
        planned_sessions_per_week=summary.planned_sessions_per_week,
        adherence_pct=summary.adherence_pct,
        average_rpe=summary.average_rpe,
        latest_weight_kg=summary.latest_weight_kg,
        weight_change_kg=summary.weight_change_kg,
        deload_due=summary.deload_due,
        notes=summary.notes,
    )
