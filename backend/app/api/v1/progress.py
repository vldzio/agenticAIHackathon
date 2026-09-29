from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Path, Response, status

from app.api.deps import DbSession, DeviceId
from app.db import repository as repo
from app.errors import AppError, ErrorResponse
from app.schemas.progress import ProgressLogIn, ProgressLogOut, ProgressSummary
from app.services import progress_service

router = APIRouter(prefix="/assessments/{assessment_id}", tags=["progress"])
AssessmentId = Annotated[str, Path(min_length=36, max_length=36)]
ERRORS: dict[int | str, dict[str, Any]] = {404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}}


@router.get("/progress", response_model=ProgressSummary, responses=ERRORS)
def get_progress(assessment_id: AssessmentId, db: DbSession, device: DeviceId) -> ProgressSummary:
    assessment = repo.get_assessment(db, device, assessment_id)
    if assessment is None:
        raise AppError(404, "not_found", "Assessment not found.")
    return progress_service.summarize(assessment, repo.list_logs(db, device, assessment_id))


@router.get("/logs", response_model=list[ProgressLogOut], responses=ERRORS)
def list_logs(assessment_id: AssessmentId, db: DbSession, device: DeviceId) -> list[ProgressLogOut]:
    if repo.get_assessment(db, device, assessment_id) is None:
        raise AppError(404, "not_found", "Assessment not found.")
    return [ProgressLogOut.model_validate(r) for r in repo.list_logs(db, device, assessment_id)]


@router.post("/logs", response_model=ProgressLogOut, status_code=status.HTTP_201_CREATED, responses=ERRORS)
def add_log(assessment_id: AssessmentId, body: ProgressLogIn, db: DbSession, device: DeviceId) -> ProgressLogOut:
    if body.kind == "weight" and body.weight_kg is None:
        raise AppError(
            422, "validation_error", "weight_kg is required for weight logs.", [{"field": "weight_kg", "message": "required"}]
        )
    row = repo.add_log(db, device, assessment_id, body)
    if row is None:
        raise AppError(404, "not_found", "Assessment not found.")
    return ProgressLogOut.model_validate(row)


@router.delete("/logs/{log_id}", status_code=status.HTTP_204_NO_CONTENT, responses=ERRORS)
def delete_log(assessment_id: AssessmentId, log_id: int, db: DbSession, device: DeviceId) -> Response:
    if not repo.delete_log(db, device, assessment_id, log_id):
        raise AppError(404, "not_found", "Log entry not found.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
