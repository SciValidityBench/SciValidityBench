"""Construct-drift worlds with explicit comparability relations."""

from __future__ import annotations

from collections.abc import Mapping

from scivaliditybench.core.events import EventType, Visibility
from scivaliditybench.core.specs import TaskSpec
from scivaliditybench.states.common import base_graph, event, finalize


_HARMONIZATION_CHOICES = {
    "IDENTICAL": "pool_without_transform",
    "CONVERTIBLE": "transform_then_pool",
    "INCOMMENSURATE": "keep_separate",
}
_HARMONIZATION_COUNTERFACTUAL = {
    "IDENTICAL": "INCOMMENSURATE",
    "CONVERTIBLE": "IDENTICAL",
    "INCOMMENSURATE": "CONVERTIBLE",
}


def _build_harmonization_world(
    spec: TaskSpec, seed: int, surface: Mapping[str, str]
):
    graph = base_graph(spec, seed, surface)
    state = tuple(_HARMONIZATION_CHOICES)[seed % 3]
    counterfactual_state = _HARMONIZATION_COUNTERFACTUAL[state]
    graph.add_node(
        "construct_v1",
        "construct",
        {"scale": "reference", "unit": "u1", "visible_from": 1},
    )
    graph.add_node(
        "construct_v2",
        "construct",
        {
            "scale": "reference" if state == "IDENTICAL" else "alternate",
            "unit": "u1" if state == "IDENTICAL" else "u2",
            "visible_from": 2,
        },
    )
    graph.add_node(
        "harmonization_state",
        "construct_state",
        {"value": state, "visible_from": 2, "critical": True, "atomic_correct": True},
    )
    graph.add_node(
        "observation_v1",
        "observation",
        {"value": round(0.5 + seed * 0.001, 4), "visible_from": 1},
    )
    graph.add_node(
        "observation_v2",
        "observation",
        {"value": round(0.6 + seed * 0.001, 4), "visible_from": 2},
    )
    graph.add_node(
        "claim", "claim", {"status": "pending_harmonization", "visible_from": 3}
    )
    graph.add_node("truth", "hidden_truth", {"state": state, "oracle_only": True})
    harmonization_edge = graph.add_edge(
        "construct_v1",
        "harmonization_state",
        "HARMONIZES_WITH",
        {"target": "construct_v2", "visible_from": 2},
    )
    graph.add_edge(
        "harmonization_state", "construct_v2", "APPLIES_TO", {"visible_from": 2}
    )
    graph.add_edge("observation_v1", "construct_v1", "MEASURES", {"visible_from": 1})
    graph.add_edge("observation_v2", "construct_v2", "MEASURES", {"visible_from": 2})
    events = [
        event(
            spec,
            seed,
            0,
            EventType.OBSERVE,
            "environment",
            ("construct_v1", "observation_v1"),
            {"scale": "reference", "unit": "u1"},
            episode=1,
        ),
        event(
            spec,
            seed,
            1,
            EventType.OBSERVE,
            "environment",
            ("construct_v2", "observation_v2", "harmonization_state"),
            {"harmonization_state": state},
            episode=2,
        ),
        event(
            spec,
            seed,
            2,
            EventType.DECIDE,
            "agent",
            ("claim",),
            {"operation": "select_harmonization_action"},
            episode=3,
        ),
        event(
            spec,
            seed,
            3,
            EventType.OBSERVE,
            "validator",
            ("truth",),
            {"harmonization_state": state},
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
        _HARMONIZATION_CHOICES[state],
        "keep_separate",
        {
            "required_nodes": ["construct_v1", "construct_v2", "harmonization_state"],
            "required_edges": [harmonization_edge],
            "primary_node": "harmonization_state",
            "primary_edge": harmonization_edge,
            "relabel_node": "harmonization_state",
            "merge_node": "construct_v2",
            "duplicate_node": "observation_v1",
            "decision_primitive": "construct_harmonization",
            "allowed_choices": list(_HARMONIZATION_CHOICES.values()),
            "counterfactual_patches": [
                {
                    "kind": "node",
                    "id": "harmonization_state",
                    "attribute": "value",
                    "value": counterfactual_state,
                }
            ],
            "counterfactual_oracle_decision": _HARMONIZATION_CHOICES[
                counterfactual_state
            ],
            "counterfactual_expectation": "flip",
        },
    )


def build_construct_world(spec: TaskSpec, seed: int, surface: Mapping[str, str]):
    if spec.generator.get("design_version") == "construct_harmonization_v2":
        return _build_harmonization_world(spec, seed, surface)
    graph = base_graph(spec, seed, surface)
    # Comparable and non-comparable worlds are exactly balanced.  Earlier
    # candidate worlds were always non-comparable, allowing "separate" to
    # score perfectly without reading memory.
    comparable = seed % 2 == 0
    definition_v1 = f"definition-{seed % 3}"
    definition_v2 = definition_v1 if comparable else f"definition-{(seed + 1) % 3}"
    population_v1 = "eligible"
    population_v2 = population_v1 if comparable else "all"
    graph.add_node(
        "metric_v1",
        "construct",
        {"definition": definition_v1, "population": population_v1, "visible_from": 1},
    )
    graph.add_node(
        "metric_v2",
        "construct",
        {"definition": definition_v2, "population": population_v2, "visible_from": 2},
    )
    graph.add_node(
        "observation_v1",
        "observation",
        {"value": round(0.7 + seed * 0.0001, 4), "visible_from": 1, "atomic_correct": True},
    )
    graph.add_node(
        "observation_v2",
        "observation",
        {"value": round(0.72 + seed * 0.0001, 4), "visible_from": 2, "atomic_correct": True},
    )
    graph.add_node("claim", "claim", {"status": "pool", "visible_from": 3, "salient": True})
    graph.add_node(
        "truth", "hidden_truth", {"comparable": comparable, "oracle_only": True}
    )
    comparability_edge = graph.add_edge(
        "metric_v1",
        "metric_v2",
        "COMPARABLE_WITH",
        {"value": comparable, "visible_from": 2},
    )
    graph.add_edge("observation_v1", "metric_v1", "MEASURES", {"visible_from": 1})
    graph.add_edge("observation_v2", "metric_v2", "MEASURES", {"visible_from": 2})
    events = [
        event(
            spec,
            seed,
            0,
            EventType.OBSERVE,
            "environment",
            ("metric_v1", "observation_v1"),
            {"definition": definition_v1, "population": population_v1},
            episode=1,
        ),
        event(
            spec,
            seed,
            1,
            EventType.OBSERVE,
            "environment",
            ("metric_v2", "observation_v2"),
            {"definition": definition_v2, "population": population_v2},
            episode=2,
        ),
        event(
            spec,
            seed,
            2,
            EventType.DECIDE,
            "agent",
            ("claim",),
            {"operation": "pool_or_separate"},
            episode=3,
        ),
        event(
            spec,
            seed,
            3,
            EventType.OBSERVE,
            "validator",
            ("truth",),
            {"comparable": comparable},
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
        "pool" if comparable else "separate",
        "pool",
        {
            "required_nodes": ["metric_v1", "metric_v2"],
            "required_edges": [comparability_edge],
            "primary_node": "metric_v2",
            "primary_edge": comparability_edge,
            "relabel_node": "metric_v2",
            "merge_node": "metric_v1",
            "duplicate_node": "observation_v1",
            "decision_primitive": "construct_comparability",
            "counterfactual_patches": [
                {
                    "kind": "edge",
                    "id": comparability_edge,
                    "attribute": "value",
                    "value": not comparable,
                }
            ],
            "counterfactual_oracle_decision": (
                "separate" if comparable else "pool"
            ),
            "counterfactual_expectation": "flip",
        },
    )
