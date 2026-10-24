"""Sunk-cost worlds separating historical effort from future value."""

from __future__ import annotations

from collections.abc import Mapping

from scivaliditybench.core.counterfactual import INVARIANT
from scivaliditybench.core.events import EventType, Visibility
from scivaliditybench.core.specs import TaskSpec
from scivaliditybench.states.common import base_graph, event, finalize


def _build_prospective_value_world(
    spec: TaskSpec, seed: int, surface: Mapping[str, str]
):
    graph = base_graph(spec, seed, surface)
    project_a_is_best = seed % 2 == 0
    future_a, future_b = (0.80, 0.70) if project_a_is_best else (0.70, 0.80)
    prospective_a, prospective_b = (0.10, 0.20) if project_a_is_best else (0.20, 0.10)
    oracle_decision = "project_a" if project_a_is_best else "project_b"
    historical_project = "project_a" if seed % 4 in {0, 1} else "project_b"
    sunk_cost = 75 + seed % 20
    graph.add_node(
        "project_a",
        "decision_option",
        {
            "future_value": future_a,
            "prospective_cost": prospective_a,
            "visible_from": 2,
            "atomic_correct": True,
        },
    )
    graph.add_node(
        "project_b",
        "decision_option",
        {
            "future_value": future_b,
            "prospective_cost": prospective_b,
            "visible_from": 2,
            "atomic_correct": True,
        },
    )
    graph.add_node(
        "historical_cost",
        "cost_event",
        {
            "amount": sunk_cost,
            "project": historical_project,
            "sunk": True,
            "visible_from": 1,
            "salient": True,
        },
    )
    graph.add_node(
        "claim", "decision", {"status": f"continue_{historical_project}", "visible_from": 3}
    )
    graph.add_node(
        "truth", "hidden_truth", {"best_project": oracle_decision, "oracle_only": True}
    )
    relevance_edge = graph.add_edge(
        "historical_cost", historical_project, "RELEVANT_TO", {"value": False, "visible_from": 2}
    )
    graph.add_edge("claim", historical_project, "SELECTS", {"visible_from": 3})
    events = [
        event(
            spec,
            seed,
            0,
            EventType.OBSERVE,
            "environment",
            ("historical_cost",),
            {"historical_cost": sunk_cost, "historical_project": historical_project},
            episode=1,
        ),
        event(
            spec,
            seed,
            1,
            EventType.OBSERVE,
            "environment",
            ("project_a", "project_b"),
            {
                "future_a": future_a,
                "future_b": future_b,
                "prospective_cost_a": prospective_a,
                "prospective_cost_b": prospective_b,
            },
            episode=2,
        ),
        event(
            spec,
            seed,
            2,
            EventType.DECIDE,
            "agent",
            ("claim",),
            {
                "future_a": future_a,
                "future_b": future_b,
                "prospective_cost_a": prospective_a,
                "prospective_cost_b": prospective_b,
            },
            episode=3,
        ),
        event(
            spec,
            seed,
            3,
            EventType.OBSERVE,
            "validator",
            ("truth",),
            {"best_project": oracle_decision},
            episode=3,
            visibility=Visibility.ORACLE,
        ),
    ]
    return finalize(
        spec,
        seed,
        surface,
        events,
        graph,
        oracle_decision,
        historical_project,
        {
            "required_nodes": ["project_a", "project_b"],
            "required_edges": [relevance_edge],
            "primary_node": "historical_cost",
            "primary_edge": relevance_edge,
            "relabel_node": "historical_cost",
            "merge_node": "project_a",
            "duplicate_node": "historical_cost",
            "decision_primitive": "prospective_net_value",
            "counterfactual_patches": [
                {
                    "kind": "node",
                    "id": "historical_cost",
                    "attribute": "amount",
                    "value": sunk_cost + 1000,
                }
            ],
            "counterfactual_oracle_decision": oracle_decision,
            "counterfactual_expectation": INVARIANT,
        },
    )


def build_relevance_world(spec: TaskSpec, seed: int, surface: Mapping[str, str]):
    if spec.generator.get("design_version") == "relevance_prospective_cost_v2":
        return _build_prospective_value_world(spec, seed, surface)
    graph = base_graph(spec, seed, surface)
    sunk_cost = 50 + seed % 25
    counterfactual_sunk_cost = sunk_cost + 1000
    project_a_is_best = seed % 2 == 0
    future_a = 0.70 if project_a_is_best else 0.45
    future_b = 0.45 if project_a_is_best else 0.70
    oracle_decision = "project_a" if project_a_is_best else "project_b"
    # Vary which project accumulated the history independently of which one
    # has better future value, so neither project name nor cost salience is a
    # shortcut to the oracle action.
    historical_project = "project_a" if seed % 4 in {0, 1} else "project_b"
    graph.add_node(
        "project_a",
        "decision_option",
        {"future_value": future_a, "visible_from": 2, "atomic_correct": True},
    )
    graph.add_node(
        "project_b",
        "decision_option",
        {"future_value": future_b, "visible_from": 2, "atomic_correct": True},
    )
    graph.add_node(
        "cost_a",
        "cost_event",
        {
            "amount": sunk_cost,
            "project": historical_project,
            "sunk": True,
            "visible_from": 1,
            "salient": True,
        },
    )
    graph.add_node(
        "claim", "decision", {"status": f"continue_{historical_project}", "visible_from": 3}
    )
    graph.add_node(
        "truth", "hidden_truth", {"best_project": oracle_decision, "oracle_only": True}
    )
    relevance_edge = graph.add_edge(
        "cost_a", historical_project, "RELEVANT_TO", {"value": False, "visible_from": 2}
    )
    graph.add_edge("claim", historical_project, "SELECTS", {"visible_from": 3})
    events = [
        event(
            spec,
            seed,
            0,
            EventType.OBSERVE,
            "environment",
            ("cost_a",),
            {"historical_cost": sunk_cost, "historical_project": historical_project},
            episode=1,
            cost={"compute_units": sunk_cost},
        ),
        event(
            spec,
            seed,
            1,
            EventType.OBSERVE,
            "environment",
            ("project_a", "project_b"),
            {"future_a": future_a, "future_b": future_b},
            episode=2,
        ),
        event(
            spec,
            seed,
            2,
            EventType.DECIDE,
            "agent",
            ("claim",),
            {
                "future_a": future_a,
                "future_b": future_b,
                "remaining_budget": 10,
            },
            episode=3,
        ),
        event(
            spec,
            seed,
            3,
            EventType.OBSERVE,
            "validator",
            ("truth",),
            {"best_project": oracle_decision},
            episode=3,
            visibility=Visibility.ORACLE,
        ),
    ]
    return finalize(
        spec,
        seed,
        surface,
        events,
        graph,
        oracle_decision,
        historical_project,
        {
            "required_nodes": ["project_a", "project_b"],
            "required_edges": [relevance_edge],
            "primary_node": "cost_a",
            "primary_edge": relevance_edge,
            "relabel_node": "cost_a",
            "merge_node": "project_a",
            "duplicate_node": "cost_a",
            "decision_primitive": "future_value_invariance",
            "counterfactual_patches": [
                {
                    "kind": "node",
                    "id": "cost_a",
                    "attribute": "amount",
                    "value": counterfactual_sunk_cost,
                }
            ],
            "counterfactual_oracle_decision": oracle_decision,
            "counterfactual_expectation": INVARIANT,
        },
    )
