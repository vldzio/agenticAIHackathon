from __future__ import annotations

import logging
from collections.abc import Iterator
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Path, Response, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.api.deps import DbSession, DeviceId, GeminiKey, make_client
from app.db import repository as repo
from app.db.session import session_factory
from app.errors import AppError, ErrorResponse
from app.schemas.assessment import Assessment, AssessmentSummary
from app.schemas.profile import AssessmentRequest, Mode, ProfileIn
from app.services import assessment_service as svc
from app.services import export_service, progress_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/assessments", tags=["assessments"])

AssessmentId = Annotated[str, Path(min_length=36, max_length=36, description="Assessment UUID")]
ERRORS: dict[int | str, dict[str, Any]] = {
    400: {"model": ErrorResponse},
    401: {"model": ErrorResponse, "description": "Invalid or missing Gemini API key (live mode)"},
    404: {"model": ErrorResponse},
    422: {"model": ErrorResponse},
    429: {"model": ErrorResponse, "description": "Rate limited (this API or the Gemini key's quota)"},
    503: {"model": ErrorResponse},
}


class ReplanRequest(BaseModel):
    mode: Mode = "mock"


def _get_or_404(db: DbSession, device: str, assessment_id: str) -> Assessment:
    assessment = repo.get_assessment(db, device, assessment_id)
    if assessment is None:
        raise AppError(404, "not_found", "Assessment not found.")
    return assessment


@router.post(
    "", response_model=Assessment, status_code=status.HTTP_201_CREATED, responses=ERRORS, summary="Generate an assessment"
)
def create_assessment(body: AssessmentRequest, db: DbSession, device: DeviceId, api_key: GeminiKey) -> Assessment:
    client = make_client(body.mode, api_key)
    assessment = svc.run_to_completion(client, body.profile, mode=body.mode)
    repo.save_assessment(db, device, assessment)
    return assessment


@router.post(
    "/stream",
    responses={200: {"content": {"text/event-stream": {}}, "description": "SSE events: start, node, result, error"}, **ERRORS},
    summary="Generate an assessment, streaming per-step progress (Server-Sent Events)",
)
def stream_assessment(body: AssessmentRequest, device: DeviceId, api_key: GeminiKey) -> StreamingResponse:
    client = make_client(body.mode, api_key)  # auth problems surface as a normal HTTP error before streaming starts
    return StreamingResponse(
        _event_stream(client, body.profile, body.mode, device),
        media_type="text/event-stream",
        headers={"X-Accel-Buffering": "no"},
    )


def _event_stream(client, profile: ProfileIn, mode: str, device: str, **kwargs) -> Iterator[str]:
    with session_factory()() as db:
        try:
            for event in svc.execute(client, profile, mode=mode, **kwargs):
                if event["event"] == "done":
                    assessment: Assessment = event["assessment"]
                    repo.save_assessment(db, device, assessment)
                    yield svc.sse("result", assessment.model_dump(mode="json"))
                else:
                    yield svc.sse(event["event"], event)
        except AppError as exc:
            yield svc.sse("error", {"code": exc.code, "message": exc.message, "status": exc.status_code})
        except Exception:
            logger.exception("Assessment stream failed")
            yield svc.sse("error", {"code": "internal_error", "message": "An unexpected error occurred.", "status": 500})


@router.get("", response_model=list[AssessmentSummary], summary="List saved assessments for this device")
def list_assessments(db: DbSession, device: DeviceId) -> list[AssessmentSummary]:
    return repo.list_assessments(db, device)


@router.get("/{assessment_id}", response_model=Assessment, responses=ERRORS)
def get_assessment(assessment_id: AssessmentId, db: DbSession, device: DeviceId) -> Assessment:
    return _get_or_404(db, device, assessment_id)


@router.delete("/{assessment_id}", status_code=status.HTTP_204_NO_CONTENT, responses=ERRORS)
def delete_assessment(assessment_id: AssessmentId, db: DbSession, device: DeviceId) -> Response:
    if not repo.delete_assessment(db, device, assessment_id):
        raise AppError(404, "not_found", "Assessment not found.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{assessment_id}/replan",
    response_model=Assessment,
    status_code=201,
    responses=ERRORS,
    summary="Regenerate the next training block using logged progress",
)
def replan(assessment_id: AssessmentId, body: ReplanRequest, db: DbSession, device: DeviceId, api_key: GeminiKey) -> Assessment:
    parent = _get_or_404(db, device, assessment_id)
    profile, context = _replan_inputs(db, device, parent)
    client = make_client(body.mode, api_key)
    assessment = svc.run_to_completion(client, profile, mode=body.mode, progress_context=context, parent_id=parent.id)
    repo.save_assessment(db, device, assessment)
    return assessment


@router.post("/{assessment_id}/replan/stream", responses=ERRORS, summary="Replan, streaming progress (SSE)")
def replan_stream(
    assessment_id: AssessmentId, body: ReplanRequest, db: DbSession, device: DeviceId, api_key: GeminiKey
) -> StreamingResponse:
    parent = _get_or_404(db, device, assessment_id)
    profile, context = _replan_inputs(db, device, parent)
    client = make_client(body.mode, api_key)
    return StreamingResponse(
        _event_stream(client, profile, body.mode, device, progress_context=context, parent_id=parent.id),
        media_type="text/event-stream",
        headers={"X-Accel-Buffering": "no"},
    )


def _replan_inputs(db: DbSession, device: str, parent: Assessment):
    logs = repo.list_logs(db, device, parent.id)
    summary = progress_service.summarize(parent, logs)
    profile = parent.profile.model_copy(update={"weight_kg": summary.latest_weight_kg or parent.profile.weight_kg})
    return profile, progress_service.to_context(summary).model_dump()


@router.get(
    "/{assessment_id}/export.{fmt}",
    responses={200: {"content": {"application/pdf": {}, "text/calendar": {}, "application/json": {}}}, **ERRORS},
    summary="Export as PDF, iCalendar (.ics) or JSON",
)
def export(assessment_id: AssessmentId, fmt: Literal["pdf", "ics", "json"], db: DbSession, device: DeviceId) -> Response:
    assessment = _get_or_404(db, device, assessment_id)
    name = f"aetherfit-{assessment.id[:8]}"
    if fmt == "pdf":
        return Response(
            export_service.to_pdf(assessment),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{name}.pdf"'},
        )
    if fmt == "ics":
        if not assessment.workout:
            raise AppError(422, "no_workout", "This assessment has no workout plan to export.")
        return Response(
            export_service.to_ics(assessment),
            media_type="text/calendar",
            headers={"Content-Disposition": f'attachment; filename="{name}.ics"'},
        )
    return Response(
        assessment.model_dump_json(indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{name}.json"'},
    )
