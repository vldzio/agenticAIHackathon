from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from string import Template
from typing import Any

from pydantic import BaseModel

PROMPT_DIR = Path(__file__).parent / "prompts"


@lru_cache
def _template(name: str) -> Template:
    return Template((PROMPT_DIR / f"{name}.md").read_text(encoding="utf-8"))


@lru_cache
def _common() -> str:
    return (PROMPT_DIR / "_common.md").read_text(encoding="utf-8").strip()


def sanitize_user_text(text: str) -> str:
    """Untrusted text is placed inside <user_input> tags; make sure it cannot close or open tags."""
    return " ".join(text.replace("<", " ").replace(">", " ").split())


def render(name: str, schema: type[BaseModel], **values: Any) -> str:
    schema_json = json.dumps(schema.model_json_schema(), separators=(",", ":"))
    return _template(name).safe_substitute(common=_common(), schema=schema_json, **values)
