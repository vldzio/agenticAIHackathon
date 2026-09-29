from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.models import AssessmentRow, ProgressLogRow
from app.schemas.assessment import Assessment, AssessmentSummary
from app.schemas.progress import ProgressLogIn


def save_assessment(db: Session, device_id: str, assessment: Assessment) -> None:
    row = AssessmentRow(
        id=assessment.id,
        device_id=device_id,
        created_at=assessment.created_at,
        parent_id=assessment.parent_id,
        mode=assessment.mode,
        simulated=assessment.simulated,
        status=assessment.status,
        user_name=assessment.profile.user_name,
        fitness_goal=assessment.profile.fitness_goal,
        fitness_level=assessment.fitness.level if assessment.fitness else None,
        injury_risk=assessment.injury.risk if assessment.injury else None,
        safety_level=assessment.safety.level if assessment.safety else None,
        daily_calorie_target=assessment.nutrition.daily_calorie_target if assessment.nutrition else None,
        sessions_per_week=assessment.workout.workout_frequency_per_week if assessment.workout else None,
        payload=assessment.model_dump_json(),
    )
    db.add(row)
    db.commit()


def _row(db: Session, device_id: str, assessment_id: str) -> AssessmentRow | None:
    row = db.get(AssessmentRow, assessment_id)
    return row if row is not None and row.device_id == device_id else None


def get_assessment(db: Session, device_id: str, assessment_id: str) -> Assessment | None:
    row = _row(db, device_id, assessment_id)
    return Assessment.model_validate_json(row.payload) if row else None


def list_assessments(db: Session, device_id: str, limit: int = 50) -> list[AssessmentSummary]:
    rows = db.scalars(
        select(AssessmentRow).where(AssessmentRow.device_id == device_id).order_by(AssessmentRow.created_at.desc()).limit(limit)
    ).all()
    return [
        AssessmentSummary(
            id=r.id,
            created_at=r.created_at,
            parent_id=r.parent_id,
            mode=r.mode,
            simulated=r.simulated,  # type: ignore[arg-type]
            status=r.status,
            user_name=r.user_name,
            fitness_goal=r.fitness_goal,
            fitness_level=r.fitness_level,  # type: ignore[arg-type]
            injury_risk=r.injury_risk,
            safety_level=r.safety_level,
            daily_calorie_target=r.daily_calorie_target,
            sessions_per_week=r.sessions_per_week,
        )
        for r in rows
    ]


def delete_assessment(db: Session, device_id: str, assessment_id: str) -> bool:
    row = _row(db, device_id, assessment_id)
    if row is None:
        return False
    db.delete(row)
    db.commit()
    return True


def add_log(db: Session, device_id: str, assessment_id: str, data: ProgressLogIn) -> ProgressLogRow | None:
    if _row(db, device_id, assessment_id) is None:
        return None
    row = ProgressLogRow(assessment_id=assessment_id, device_id=device_id, **data.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_logs(db: Session, device_id: str, assessment_id: str) -> list[ProgressLogRow]:
    return list(
        db.scalars(
            select(ProgressLogRow)
            .where(ProgressLogRow.assessment_id == assessment_id, ProgressLogRow.device_id == device_id)
            .order_by(ProgressLogRow.logged_on.desc(), ProgressLogRow.id.desc())
        ).all()
    )


def delete_log(db: Session, device_id: str, assessment_id: str, log_id: int) -> bool:
    result = db.execute(
        delete(ProgressLogRow).where(
            ProgressLogRow.id == log_id,
            ProgressLogRow.assessment_id == assessment_id,
            ProgressLogRow.device_id == device_id,
        )
    )
    db.commit()
    return bool(getattr(result, "rowcount", 0))
