"""LangGraph topology.

    form_parser -> input_normalizer -> fitness_scorer -> injury_assessor -> safety_guardrail
                -> workout_planner -> nutrition_advisor -> recovery_optimizer -> END

* The injury model consumes the fitness prediction, so the two ML steps are strictly ordered.
* Every edge is conditional: a validation failure or a fatal error (bad API key, quota, missing model)
  short-circuits to END and remaining sections are reported as "skipped".
"""

from __future__ import annotations

from typing import Any, cast

from langgraph.graph import END, StateGraph

from app.graph import nodes
from app.graph.state import AssessmentState

NODE_ORDER = [
    "form_parser",
    "input_normalizer",
    "fitness_scorer",
    "injury_assessor",
    "safety_guardrail",
    "workout_planner",
    "nutrition_advisor",
    "recovery_optimizer",
]
NODE_LABELS = {
    "form_parser": "Validating your profile",
    "input_normalizer": "Interpreting your answers",
    "fitness_scorer": "Estimating fitness level",
    "injury_assessor": "Estimating injury risk",
    "safety_guardrail": "Applying safety rules",
    "workout_planner": "Designing your workout plan",
    "nutrition_advisor": "Building your nutrition plan",
    "recovery_optimizer": "Planning recovery & habits",
}
NODE_SECTION = {
    "form_parser": "profile",
    "input_normalizer": "normalization",
    "fitness_scorer": "fitness",
    "injury_assessor": "injury",
    "safety_guardrail": "safety",
    "workout_planner": "workout",
    "nutrition_advisor": "nutrition",
    "recovery_optimizer": "recovery",
}


def _route(state: dict[str, Any]) -> str:
    return "end" if state.get("fatal") else "continue"


def build_graph(deps: nodes.Deps):
    functions = {
        "form_parser": nodes.form_parser,
        "input_normalizer": nodes.make_input_normalizer(deps),
        "fitness_scorer": nodes.make_fitness_scorer(deps),
        "injury_assessor": nodes.make_injury_assessor(deps),
        "safety_guardrail": nodes.safety_guardrail,
        "workout_planner": nodes.make_workout_planner(deps),
        "nutrition_advisor": nodes.make_nutrition_advisor(deps),
        "recovery_optimizer": nodes.make_recovery_optimizer(deps),
    }
    graph = StateGraph(AssessmentState)
    for name in NODE_ORDER:
        graph.add_node(name, cast(Any, nodes.timed(name, functions[name])))
    graph.set_entry_point(NODE_ORDER[0])
    for current, following in zip(NODE_ORDER, NODE_ORDER[1:], strict=False):
        graph.add_conditional_edges(current, _route, {"continue": following, "end": END})
    graph.add_edge(NODE_ORDER[-1], END)
    return graph.compile()


def workflow_structure() -> dict[str, Any]:
    return {
        "nodes": [{"name": n, "label": NODE_LABELS[n], "section": NODE_SECTION[n]} for n in NODE_ORDER],
        "edges": list(zip(NODE_ORDER, NODE_ORDER[1:], strict=False)),
    }
