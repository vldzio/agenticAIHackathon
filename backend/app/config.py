"""Application settings (environment variables prefixed ``AETHERFIT_``; see ``.env.example``)."""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

from app.ml.paths import BACKEND_DIR


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AETHERFIT_", env_file=".env", extra="ignore")

    env: str = "dev"
    log_level: str = "INFO"
    database_url: str = f"sqlite:///{BACKEND_DIR / 'var' / 'aetherfit.db'}"
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:5173", "http://localhost:8080"]

    # Abuse protection (in-memory, per process; put a shared limiter in front for multi-replica deploys).
    rate_limit_per_minute: int = 120
    assessment_rate_limit_per_minute: int = 10
    max_request_bytes: int = 64_000
    trust_proxy_headers: bool = False

    # LLM
    gemini_model: str = "gemini-2.5-flash-lite"
    llm_timeout_seconds: float = 45.0
    llm_max_retries: int = 3

    strict_model_versions: bool = False

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            value = value.strip()
            if value.startswith("["):
                import json

                return json.loads(value)
            return [v.strip() for v in value.split(",") if v.strip()]
        return value

    @property
    def is_prod(self) -> bool:
        return self.env.lower() in {"prod", "production"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
