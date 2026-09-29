from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict


def merge_dicts(left: dict[str, Any] | None, right: dict[str, Any] | None) -> dict[str, Any]:
    return {**(left or {}), **(right or {})}


class AssessmentState(TypedDict, total=False):
    """Shared graph state. Fields written by more than one node use reducers, so nothing can raise
    ``INVALID_CONCURRENT_GRAPH_UPDATE`` and errors from any node are always preserved."""

    raw_profile: dict[str, Any]
    progress_context: dict[str, Any] | None
    profile: dict[str, Any]
    previous_injury: bool
    metrics: dict[str, Any]
    normalized: dict[str, Any]
    fitness: dict[str, Any]
    injury: dict[str, Any]
    safety: dict[str, Any]
    target_sessions: int
    workout: dict[str, Any] | None
    nutrition: dict[str, Any] | None
    recovery: dict[str, Any] | None
    sections: Annotated[dict[str, str], merge_dicts]
    errors: Annotated[list[dict[str, Any]], operator.add]
    warnings: Annotated[list[str], operator.add]
    fatal: bool
