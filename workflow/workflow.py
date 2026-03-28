from langgraph.graph import StateGraph, END
from typing import Dict, Any
from state import FitnessAssessmentState
from nodes.fitness_scorer_node import fitness_scorer_node
from nodes.form_parser_node import form_parser_node
from nodes.injury_assessor_node import injury_assessor_node
from nodes.input_normalizer_node import input_normalizer_node
from nodes.nutrition_advisor_node import nutrition_advisor_node
from nodes.recovery_lifestyle_optimizer_node import recovery_lifestyle_optimizer_node
from nodes.workout_planner_node import workout_planner_node

def build_fitness_assessment_graph(client=None):
    """
    Build 7-node fitness assessment workflow graph.

    Returns:
        Compiled StateGraph for workflow execution
    """
    graph = StateGraph(FitnessAssessmentState)

    graph.add_node("form_parser", lambda state: form_parser_node(state))
    graph.add_node("input_normalizer", lambda state: input_normalizer_node(state, client))
    graph.add_node("fitness_scorer", lambda state: fitness_scorer_node(state))
    graph.add_node("injury_assessor", lambda state: injury_assessor_node(state))
    graph.add_node("workout_planner", lambda state: workout_planner_node(state, client))
    graph.add_node("nutrition_advisor", lambda state: nutrition_advisor_node(state, client))

    graph.add_node("recovery_lifestyle_optimizer", lambda state: recovery_lifestyle_optimizer_node(state, client))

    graph.set_entry_point("form_parser")
    graph.add_edge("form_parser","input_normalizer")

    graph.add_edge("input_normalizer", "fitness_scorer")
    graph.add_edge("input_normalizer", "injury_assessor")

    graph.add_edge("fitness_scorer", "workout_planner")
    graph.add_edge("injury_assessor", "workout_planner")

    graph.add_edge("workout_planner", "nutrition_advisor")
    graph.add_edge("nutrition_advisor", "recovery_lifestyle_optimizer")

    graph.add_edge("recovery_lifestyle_optimizer", END)

    return graph.compile()

def get_workflow_structure() -> Dict[str, Any]:
    """Return dict with workflow metadata: name, nodes[], edges[], entry/exit points."""
    return {
      "name": "Fitness Assessment Workflow",
      "description" : "AI-powered pipeline that analyzes fitness profile and generates workout, nutrition, and recovery plans.",
      "nodes" : [
        {
          "name" : "form_parser",
          "type" : "validation",
          "description" : "Parse and validate form inputs"
        },
        {
          "name" : "input_normalizer",
          "type" : "llm",
          "description" : "Normalize free text inputs."
        },
        {
          "name" : "fitness_scorer",
          "type" : "ml",
          "description" : "Predict fitness level using ML model."
        },
        {
          "name" : "injury_assessor",
          "type" : "ml",
          "description" : "Predict injury risk using ML model."
        },
        {
          "name" : "workout_planner",
          "type" : "llm",
          "description" : "Generate workout plan."
        },
        {
          "name" : "nutrition_advisor",
          "type" : "llm",
          "description" : "Generate nutrition plan."
        },
        {
          "name" : "recovery_lifestyle_optimizer",
          "type" : "llm",
          "description" : "Generate recovery and lifestyle optimization plan."
        }
      ],
      "edges" : [
        ("form_parser","input_normalizer"),
        ("input_normalizer", "fitness_scorer"),
        ("input_normalizer", "injury_assessor"),
        ("fitness_scorer", "workout_planner"),
        ("injury_assessor", "workout_planner"),
        ("workout_planner", "nutrition_advisor"),
        ("nutrition_advisor", "recovery_lifestyle_optimizer"),
      ],
      "entry_point" : "form_parser",
      "exit_point" : "END"
    }