from __future__ import annotations

import datetime as dt
import json
import logging
import uuid
from collections.abc import Iterator
from typing import Any

from app.errors import AppError
from app.graph.nodes import Deps
from app.graph.workflow import NODE_LABELS, NODE_ORDER, NODE_SECTION, build_graph
from app.llm.base import LLMClient
from app.ml.predictors import FitnessPredictor, InjuryPredictor
from app.schemas.assessment import Assessment
from app.schemas.profile import ProfileIn

logger = logging.getLogger(__name__)

FATAL_HTTP = {"llm_auth": 401, "llm_rate_limited": 429, "validation_error": 422, "ml_failure": 503}
SECTIONS = ["normalization", "fitness", "injury", "safety", "workout", "nutrition", "recovery"]


def _overall_status(state: dict[str, Any]) -> str:
    sections = state.get("sections", {})
    if not state.get("fitness") or state.get("profile") is None:
        return "failed"
    return "complete" if all(sections.get(s) == "ok" for s in SECTIONS) else "partial"


def build_assessment(
    state: dict[str, Any],
    *,
    profile: ProfileIn,
    mode: str,
    simulated: bool,
    parent_id: str | None = None,
) -> Assessment:
    sections = {s: state.get("sections", {}).get(s, "skipped") for s in SECTIONS}
    return Assessment(
        id=str(uuid.uuid4()),
        created_at=dt.datetime.now(dt.UTC),
        parent_id=parent_id,
        mode=mode,  # type: ignore[arg-type]
        simulated=simulated,
        status=_overall_status(state),  # type: ignore[arg-type]
        profile=profile,
        metrics=state.get("metrics"),
        normalized=state.get("normalized"),
        fitness=state.get("fitness"),
        injury=state.get("injury"),
        safety=state.get("safety"),
        workout=state.get("workout"),
        nutrition=state.get("nutrition"),
        recovery=state.get("recovery"),
        sections=sections,  # type: ignore[arg-type]
        errors=state.get("errors", []),
        warnings=list(dict.fromkeys(state.get("warnings", []))),
        progress_context=state.get("progress_context"),
    )


def raise_if_unusable(state: dict[str, Any]) -> None:
    """Nothing useful was produced -> surface a typed HTTP error instead of a hollow 'failed' assessment."""
    if _overall_status(state) != "failed":
        return
    errors = state.get("errors") or [{"code": "internal_error", "message": "The assessment could not be generated."}]
    first = errors[0]
    fields = [
        {"field": e["message"].split(":")[0], "message": e["message"]} for e in errors if e["code"] == "validation_error"
    ] or None
    raise AppError(FATAL_HTTP.get(first["code"], 502), first["code"], first["message"], fields)


def execute(
    client: LLMClient,
    profile: ProfileIn,
    *,
    mode: str,
    progress_context: dict[str, Any] | None = None,
    parent_id: str | None = None,
) -> Iterator[dict[str, Any]]:
    """Run the graph, yielding progress events; the final event is ``{"event": "done", "assessment": Assessment}``."""
    graph = build_graph(Deps(llm=client, fitness=FitnessPredictor(), injury=InjuryPredictor()))
    initial: dict[str, Any] = {
        "raw_profile": profile.model_dump(),
        "progress_context": progress_context,
        "sections": {},
        "errors": [],
        "warnings": [],
    }
    yield {"event": "start", "nodes": [{"name": n, "label": NODE_LABELS[n], "section": NODE_SECTION[n]} for n in NODE_ORDER]}
    final: dict[str, Any] = dict(initial)
    for kind, chunk in graph.stream(initial, stream_mode=["updates", "values"]):
        if kind == "values":
            final = chunk
            continue
        for node, update in chunk.items():
            section = NODE_SECTION[node]
            yield {
                "event": "node",
                "node": node,
                "label": NODE_LABELS[node],
                "status": (update.get("sections") or {}).get(section, "ok"),
            }
    raise_if_unusable(final)
    yield {
        "event": "done",
        "assessment": build_assessment(final, profile=profile, mode=mode, simulated=client.simulated, parent_id=parent_id),
    }


def run_to_completion(client: LLMClient, profile: ProfileIn, **kwargs: Any) -> Assessment:
    last: dict[str, Any] = {}
    for event in execute(client, profile, **kwargs):
        last = event
    return last["assessment"]


def sse(event: str, data: Any) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"
