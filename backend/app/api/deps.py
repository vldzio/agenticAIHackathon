from __future__ import annotations

import re
from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.errors import AppError
from app.llm.base import LLMAuthError, LLMClient
from app.llm.factory import build_llm_client

DEVICE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{8,64}$")
API_KEY_RE = re.compile(r"^[A-Za-z0-9_\-]{20,256}$")

DbSession = Annotated[Session, Depends(get_session)]


def device_id(
    x_device_id: Annotated[
        str | None,
        Header(description="Anonymous, client-generated identifier that scopes saved plans to one browser."),
    ] = None,
) -> str:
    if not x_device_id or not DEVICE_ID_RE.match(x_device_id):
        raise AppError(400, "missing_device_id", "A valid X-Device-Id header (8-64 chars: letters, digits, - _) is required.")
    return x_device_id


DeviceId = Annotated[str, Depends(device_id)]


def gemini_key(
    x_gemini_api_key: Annotated[
        str | None,
        Header(description="Bring-your-own Gemini API key. Used for this request only; never stored or logged."),
    ] = None,
) -> str | None:
    if x_gemini_api_key is None:
        return None
    key = x_gemini_api_key.strip()
    if not API_KEY_RE.match(key):
        raise AppError(400, "invalid_api_key_format", "The Gemini API key format looks invalid.")
    return key


GeminiKey = Annotated[str | None, Depends(gemini_key)]


def make_client(mode: str, api_key: str | None) -> LLMClient:
    if mode == "live" and not api_key:
        raise AppError(401, "llm_auth", "Live mode requires your Gemini API key (X-Gemini-Api-Key header).")
    try:
        return build_llm_client(mode, api_key)
    except LLMAuthError as exc:
        raise AppError(401, exc.code, exc.message) from exc
