from __future__ import annotations

import datetime as dt
import io
import re
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.schemas.assessment import Assessment

TIME_OF_DAY = {"Morning": (7, 0), "Afternoon": (13, 0), "Evening": (18, 30)}
WEEKDAY_INDEX = {d: i for i, d in enumerate(["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"])}
BYDAY = ["MO", "TU", "WE", "TH", "FR", "SA", "SU"]


# --------------------------------------------------------------------------------------- iCalendar
def _ics_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\r\n", "\\n").replace("\n", "\\n")


def _fold(line: str) -> list[str]:
    """RFC 5545 line folding at 75 octets."""
    raw = line.encode()
    if len(raw) <= 75:
        return [line]
    parts: list[str] = []
    current = b""
    for ch in line:
        encoded = ch.encode()
        limit = 75 if not parts else 74
        if len(current) + len(encoded) > limit:
            parts.append(current.decode())
            current = b""
        current += encoded
    parts.append(current.decode())
    return [parts[0]] + [" " + p for p in parts[1:]]


def to_ics(assessment: Assessment) -> str:
    if not assessment.workout:
        raise ValueError("Assessment has no workout plan to export")
    weeks_match = re.search(r"(\d+)", assessment.workout.workout_progression_timeline or "")
    weeks = int(weeks_match.group(1)) if weeks_match else 6
    times = assessment.normalized.schedule.preferred_times if assessment.normalized else []
    hour, minute = next((TIME_OF_DAY[t] for t in times if t in TIME_OF_DAY), (7, 0))
    start_day = assessment.created_at.date()
    stamp = dt.datetime.now(dt.UTC).strftime("%Y%m%dT%H%M%SZ")
    duration = assessment.workout.workout_duration_per_session

    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//AetherFit AI//Workout Plan//EN", "CALSCALE:GREGORIAN", "METHOD:PUBLISH"]
    for day in assessment.workout.weekly_schedule:
        offset = (WEEKDAY_INDEX[day.day] - start_day.weekday()) % 7
        first = dt.datetime.combine(start_day + dt.timedelta(days=offset), dt.time(hour, minute))
        desc = "\n".join(f"- {e.exercise_name}: {e.sets} x {e.reps} (rest {e.rest_period})" for e in day.exercises)
        lines += [
            "BEGIN:VEVENT",
            f"UID:{assessment.id}-{day.day.lower()}@aetherfit",
            f"DTSTAMP:{stamp}",
            f"DTSTART:{first.strftime('%Y%m%dT%H%M%S')}",
            f"DTEND:{(first + dt.timedelta(minutes=duration)).strftime('%Y%m%dT%H%M%S')}",
            f"RRULE:FREQ=WEEKLY;COUNT={weeks};BYDAY={BYDAY[WEEKDAY_INDEX[day.day]]}",
            f"SUMMARY:{_ics_escape('AetherFit: ' + (day.focus or 'Workout'))}",
            f"DESCRIPTION:{_ics_escape(desc)}",
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    return "\r\n".join(part for line in lines for part in _fold(line)) + "\r\n"


# ------------------------------------------------------------------------------------------- PDF
def to_pdf(assessment: Assessment) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=16 * mm,
                            title="AetherFit plan", author="AetherFit AI")  # fmt: skip
    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=styles["Heading1"], textColor=colors.HexColor("#0f766e"))
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], textColor=colors.HexColor("#134e4a"), spaceBefore=10)
    body, small = styles["BodyText"], ParagraphStyle("small", parent=styles["BodyText"], fontSize=8, textColor=colors.grey)

    def p(text: str, style: ParagraphStyle = body) -> Paragraph:
        return Paragraph(escape(str(text)), style)

    def bullets(items: list[str]) -> list:
        return [p(f"• {i}") for i in items]

    def table(rows: list[list[str]], widths: list[float] | None = None, header: bool = True) -> Table:
        t = Table([[Paragraph(escape(str(c)), body) for c in r] for r in rows], colWidths=widths, repeatRows=1 if header else 0)
        style = [("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey), ("VALIGN", (0, 0), (-1, -1), "TOP")]
        if header:
            style.append(("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#ccfbf1")))
        t.setStyle(TableStyle(style))
        return t

    a = assessment
    story: list = [p(f"AetherFit plan{' for ' + a.profile.user_name if a.profile.user_name else ''}", h1)]
    story.append(
        p(
            f"Generated {a.created_at:%Y-%m-%d} · {'SIMULATED (mock) output' if a.simulated else 'Generated with Gemini'} · ID {a.id}",
            small,
        )
    )
    if a.safety and a.safety.requires_clearance:
        story += [
            Spacer(1, 6),
            p(
                "IMPORTANT: obtain medical clearance before starting this plan.",
                ParagraphStyle("warn", parent=body, textColor=colors.HexColor("#b91c1c"), fontName="Helvetica-Bold"),
            ),
        ]
    if a.fitness and a.injury and a.metrics:
        story.append(p("Assessment", h2))
        story.append(
            table(
                [
                    ["Fitness level", f"{a.fitness.level} ({a.fitness.confidence:.0f}% confidence)"],
                    ["Injury risk", f"{a.injury.risk} ({a.injury.confidence:.0f}% confidence)"],
                    ["BMI", f"{a.metrics.bmi} ({a.metrics.bmi_category})"],
                    ["Goal", a.profile.fitness_goal],
                ],
                [45 * mm, 120 * mm],
                header=False,
            )
        )
        if a.injury.risk_factors:
            story += [Spacer(1, 4), p("Risk factors: " + ", ".join(a.injury.risk_factors))]
    if a.safety and a.safety.reasons:
        story += [Spacer(1, 4), p("Safety notes", h2)] + bullets(a.safety.reasons)
    if a.workout:
        w = a.workout
        story.append(p("Workout plan", h2))
        story.append(
            p(
                f"{w.workout_frequency_per_week} sessions/week · {w.workout_intensity_level} intensity · ~{w.workout_duration_per_session} min · progression {w.workout_progression_timeline}"
            )
        )
        for day in w.weekly_schedule:
            story += [Spacer(1, 4), p(f"{day.day} — {day.focus}", ParagraphStyle("d", parent=body, fontName="Helvetica-Bold"))]
            story.append(
                table(
                    [["Exercise", "Sets", "Reps", "Rest"]]
                    + [[e.exercise_name, str(e.sets), e.reps, e.rest_period] for e in day.exercises],
                    [80 * mm, 20 * mm, 35 * mm, 30 * mm],
                )
            )
        if w.workout_equipment_needed:
            story += [Spacer(1, 4), p("Equipment: " + ", ".join(w.workout_equipment_needed))]
        story += bullets(w.workout_safety_notes)
    if a.nutrition:
        n = a.nutrition
        story.append(p("Nutrition", h2))
        story.append(
            p(
                f"Target {n.daily_calorie_target} kcal/day (maintenance {n.maintenance_calories}) · protein {n.macro_targets.protein_g} g · carbs {n.macro_targets.carbs_g} g · fat {n.macro_targets.fat_g} g"
            )
        )
        if n.meal_suggestions:
            story.append(
                table(
                    [["Meal", "Foods", "P", "C", "F", "kcal"]]
                    + [
                        [
                            m.meal_name,
                            ", ".join(m.foods),
                            f"{m.protein_g:.0f}",
                            f"{m.carbs_g:.0f}",
                            f"{m.fat_g:.0f}",
                            f"{m.calories:.0f}",
                        ]
                        for m in n.meal_suggestions
                    ],
                    [25 * mm, 85 * mm, 12 * mm, 12 * mm, 12 * mm, 16 * mm],
                )
            )
        story += [Spacer(1, 4), p(n.hydration_recommendation), p(n.nutrition_timing_guidance)]
    if a.recovery:
        r = a.recovery
        story.append(p("Recovery & lifestyle", h2))
        story.append(p(f"Sleep: {r.sleep_recommendations.hours_per_night:g} h/night"))
        for title, items in [
            ("Rest-day activities", r.rest_day_activities),
            ("Mobility", r.mobility_work),
            ("Stress management", r.stress_management_techniques),
            ("Recovery techniques", r.recovery_techniques),
            ("Adherence tips", r.adherence_tips),
        ]:
            if items:
                story += [p(title, ParagraphStyle("t", parent=body, fontName="Helvetica-Bold"))] + bullets(items)
        if r.deload_strategy:
            story.append(p("Deload: " + r.deload_strategy))
    if a.warnings:
        story += [p("Notes", h2)] + bullets(a.warnings)
    story += [
        Spacer(1, 10),
        p(a.safety.disclaimer if a.safety else "AetherFit is an educational tool, not medical advice.", small),
    ]
    doc.build(story)
    return buffer.getvalue()
