from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy import text

from app import __version__
from app.db.session import get_engine
from app.graph.workflow import workflow_structure
from app.ml.registry import ModelLoadError, get_registry
from app.services import evaluation_service

router = APIRouter(tags=["system"])


class Health(BaseModel):
    status: str
    version: str
    database: bool
    models_loaded: bool


@router.get("/health", response_model=Health)
def health() -> Health:
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False
    try:
        get_registry().warm_up()
        models_ok = True
    except ModelLoadError:
        models_ok = False
    return Health(
        status="ok" if db_ok and models_ok else "degraded", version=__version__, database=db_ok, models_loaded=models_ok
    )


@router.get("/workflow", summary="The pipeline steps, in order")
def workflow() -> dict[str, Any]:
    return workflow_structure()


@router.get("/models/info", summary="Model metadata, training-data provenance and limitations")
def models_info() -> dict[str, Any]:
    return evaluation_service.model_info()


@router.get("/models/evaluation", summary="Accuracy, per-class metrics and confusion matrices on the evaluation CSVs")
def models_evaluation(refresh: Annotated[bool, Query()] = False) -> dict[str, Any]:
    return evaluation_service.evaluate(force=refresh)
