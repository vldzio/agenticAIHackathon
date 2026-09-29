from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.v1 import api_router
from app.config import get_settings
from app.db.session import init_db
from app.errors import install_error_handlers
from app.logging_config import configure_logging
from app.middleware import BodySizeLimitMiddleware, RateLimitMiddleware, RequestContextMiddleware
from app.ml.registry import ModelLoadError, get_registry

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    init_db()
    try:
        get_registry().warm_up()
    except ModelLoadError as exc:
        logger.error("Models unavailable at startup: %s", exc)  # /health reports degraded; requests get a 503
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level, json_logs=settings.is_prod)
    app = FastAPI(
        title="AetherFit AI API",
        version=__version__,
        description=(
            "Personalised fitness assessments combining calibrated ML classifiers with an LLM planning workflow. "
            "Live generation is bring-your-own-key: send your Gemini key in `X-Gemini-Api-Key` (never stored or logged)."
        ),
        openapi_url="/api/openapi.json",
        docs_url="/api/docs",
        redoc_url=None,
        lifespan=lifespan,
    )
    install_error_handlers(app)
    # Added innermost -> outermost, so the request id/headers wrap everything (including 429/413 responses)
    # and CORS headers are present on limiter errors (otherwise the browser cannot read them).
    app.add_middleware(BodySizeLimitMiddleware, max_bytes=settings.max_request_bytes)
    app.add_middleware(
        RateLimitMiddleware,
        per_minute=settings.rate_limit_per_minute,
        expensive_per_minute=settings.assessment_rate_limit_per_minute,
        trust_proxy=settings.trust_proxy_headers,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "X-Device-Id", "X-Gemini-Api-Key"],
        expose_headers=["X-Request-Id", "Content-Disposition", "Retry-After"],
        allow_credentials=False,
    )
    app.add_middleware(RequestContextMiddleware)
    app.include_router(api_router)
    return app


app = create_app()
