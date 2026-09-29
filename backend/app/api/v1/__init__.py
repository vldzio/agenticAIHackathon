from fastapi import APIRouter

from app.api.v1 import assessments, progress, system

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(system.router)
api_router.include_router(assessments.router)
api_router.include_router(progress.router)
