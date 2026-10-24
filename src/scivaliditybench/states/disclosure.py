"""Blind-memory worlds where valid analysis depends on disclosure history."""

from __future__ import annotations

from collections.abc import Mapping

from scivaliditybench.core.events import EventType, Visibility
from scivaliditybench.core.specs import TaskSpec
from scivaliditybench.states.common import base_graph, event, finalize


def _build_dual_access_world(
    spec: TaskSpec, seed: int, surface: Mapping[str, str]
):
    graph = base_graph(spec, seed, surface)
    compromised = seed % 2 == 0
    analyst_episode = 1 if compromised else 3
    reviewer_episode = 3
    counterfactual_analyst_episode = 3 if compromised else 1
    state_value = "compromised" if compromised else "intact"
    counterfactual_state = "intact" if compromised else "compromised"
    graph.add_node(
        "plan",
        "analysis_plan",
        {"locked_at": 3, "visible_from": 0, "critical": True},
    )
    for node_id, role, actual_episode in (
        ("analyst_access", "analyst", analyst_episode),
        ("reviewer_access", "reviewer", reviewer_episode),
    ):
        graph.add_node(
            node_id,
            "access_event",
            {
                "role": role,
                "actual_episode": actual_episode,
                "allowed_episode": 3,
                "visible_from": 1,
                "atomic_correct": True,
            },
        )
    graph.add_node(
        "blinding_state",
        "blinding_state",
        {
            "value": state_value,
            "derivation": "intact iff every registered role accessed at or after lock",
            "visible_from": 1,
            "critical": True,
            "atomic_correct": True,
        },
    )
    graph.add_node(
        "outcome", "observation", {"value": round(0.3 + seed * 0.001, 4), "visible_from": 1}
    )
    graph.add_node(
        "claim", "claim", {"status": "pending_classification", "visible_from": 3}
    )
    graph.add_node(
        "truth", "hidden_truth", {"compromised": compromised, "oracle_only": True}
    )
    analyst_edge = graph.add_edge(
        "analyst_access", "blinding_state", "DERIVED_AS", {"visible_from": 1}
    )
    reviewer_edge = graph.add_edge(
        "reviewer_access", "blinding_state", "DERIVED_AS", {"visible_from": 1}
    )
    sealed_edge = graph.add_edge(
        "outcome", "plan", "SEALED_UNTIL", {"episode": 3, "visible_from": 1}
    )
    graph.add_edge("claim", "outcome", "USES_EVIDENCE", {"visible_from": 3})
    events = [
        event(
            spec,
            seed,
            0,
            EventType.PLAN,
            "agent",
            ("plan",),
            {"locked_at": 3, "registered_roles": ["analyst", "reviewer"]},
            episode=0,
        ),
        event(
            spec,
            seed,
            1,
            EventType.ACCESS,
            "agent",
            ("analyst_access", "reviewer_access", "outcome"),
            {
                "analyst_episode": analyst_episode,
                "reviewer_episode": reviewer_episode,
            },
            episode=1,
        ),
        event(
            spec,
            seed,
            2,
            EventType.DECIDE,
            "agent",
            ("claim",),
            {"requested_assessment": "classify_analysis_validity"},
            episode=3,
        ),
        event(
            spec,
            seed,
            3,
            EventType.OBSERVE,
            "validator",
            ("truth",),
            {"compromised": compromised},
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
        state_value,
        "compromised",
        {
            "required_nodes": [
                "plan",
                "analyst_access",
                "reviewer_access",
                "blinding_state",
            ],
            "required_edges": [analyst_edge, reviewer_edge, sealed_edge],
            "primary_node": "blinding_state",
            "primary_edge": analyst_edge,
            "relabel_node": "blinding_state",
            "merge_node": "analyst_access",
            "duplicate_node": "outcome",
            "decision_primitive": "dual_access_integrity",
            "allowed_choices": ["intact", "compromised"],
            "compromised_choice": "compromised",
            "direct_state_choice": True,
            "intact_choice": "intact",
            "counterfactual_patches": [
                {
                    "kind": "node",
                    "id": "analyst_access",
                    "attribute": "actual_episode",
                    "value": counterfactual_analyst_episode,
                },
                {
                    "kind": "node",
                    "id": "blinding_state",
                    "attribute": "value",
                    "value": counterfactual_state,
                },
            ],
            "counterfactual_oracle_decision": counterfactual_state,
            "counterfactual_expectation": "flip",
        },
    )


def build_disclosure_world(spec: TaskSpec, seed: int, surface: Mapping[str, str]):
    if spec.generator.get("design_version") == "blind_dual_access_v6":
        return _build_dual_access_world(spec, seed, surface)
    graph = base_graph(spec, seed, surface)
    redesigned = spec.generator.get("design_version") in {
        "blind_categorical_status_v2",
        "blind_neutral_access_status_v3",
        "blind_neutral_action_codes_v4",
        "blind_direct_state_v5",
    }
    direct_state = spec.generator.get("design_version") == "blind_direct_state_v5"
    neutral_actions = (
        spec.generator.get("design_version") == "blind_neutral_action_codes_v4"
    )
    if direct_state:
        intact_choice = "intact"
        compromised_choice = "compromised"
    else:
        intact_choice = "status_a" if neutral_actions else "confirmatory"
        compromised_choice = "status_b" if neutral_actions else "exploratory"
    # Exact action balance prevents a constant confirmatory/exploratory policy
    # from passing calibration.  The current request is held fixed; only the
    # recovered access history distinguishes the two worlds.
    premature = seed % 2 == 0
    actual_episode = 1 if premature else 3
    counterfactual_episode = 3 if premature else 1
    graph.add_node(
        "plan",
        "analysis_plan",
        {"locked_at": 3, "visible_from": 0, "critical": True},
    )
    graph.add_node(
        "access",
        "access_event",
        {
            "actual_episode": actual_episode,
            "allowed_episode": 3,
            "visible_from": 1,
            "critical": True,
            "atomic_correct": True,
        },
    )
    graph.add_node(
        "outcome",
        "observation",
        {"value": round(0.4 + seed * 0.001, 4), "visible_from": 1, "salient": True},
    )
    graph.add_node(
        "claim",
        "claim",
        {
            "status": "pending_classification" if redesigned else "confirmatory",
            "visible_from": 3,
            "atomic_correct": True,
        },
    )
    if direct_state:
        blinding_state = "compromised" if premature else "intact"
        counterfactual_blinding_state = "intact" if premature else "compromised"
    else:
        blinding_state = "COMPROMISED" if premature else "INTACT"
        counterfactual_blinding_state = "INTACT" if premature else "COMPROMISED"
    state_edge = None
    if redesigned:
        graph.add_node(
            "blinding_state",
            "blinding_state",
            {
                "value": blinding_state,
                "derivation": (
                    "compromised iff actual_episode < allowed_episode"
                    if direct_state
                    else "COMPROMISED iff actual_episode < allowed_episode"
                ),
                "visible_from": 1,
                "critical": True,
                "atomic_correct": True,
            },
        )
        state_edge = graph.add_edge(
            "access",
            "blinding_state",
            "DERIVED_AS",
            {"visible_from": 1},
        )
    graph.add_node("truth", "hidden_truth", {"premature": premature, "oracle_only": True})
    sealed_edge = graph.add_edge("outcome", "plan", "SEALED_UNTIL", {"episode": 3})
    graph.add_edge("claim", "outcome", "USES_EVIDENCE", {"visible_from": 3})
    events = [
        event(spec, seed, 0, EventType.PLAN, "agent", ("plan",), {"locked_at": 3}, episode=0),
        event(
            spec,
            seed,
            1,
            EventType.ACCESS,
            "agent",
            ("access", "outcome"),
            {"actual_episode": actual_episode},
            episode=1,
        ),
        event(
            spec,
            seed,
            2,
            EventType.DECIDE,
            "agent",
            ("claim",),
            (
                {"requested_assessment": "classify_analysis_validity"}
                if redesigned
                else {"requested_status": "confirmatory"}
            ),
            episode=3,
        ),
        event(
            spec,
            seed,
            3,
            EventType.OBSERVE,
            "validator",
            ("truth",),
            {"premature": premature},
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
        compromised_choice if premature else intact_choice,
        intact_choice,
        {
            "required_nodes": (
                ["plan", "access", "blinding_state"]
                if redesigned
                else ["plan", "access"]
            ),
            "required_edges": (
                [sealed_edge, state_edge] if state_edge is not None else [sealed_edge]
            ),
            "primary_node": "access",
            "primary_edge": sealed_edge,
            "relabel_node": "claim",
            "merge_node": "outcome",
            "duplicate_node": "outcome",
            "decision_primitive": "disclosure_timing",
            "counterfactual_patches": [
                {
                    "kind": "node",
                    "id": "access",
                    "attribute": "actual_episode",
                    "value": counterfactual_episode,
                },
                *(
                    [
                        {
                            "kind": "node",
                            "id": "blinding_state",
                            "attribute": "value",
                            "value": counterfactual_blinding_state,
                        }
                    ]
                    if redesigned
                    else []
                ),
            ],
            "counterfactual_oracle_decision": (
                intact_choice if premature else compromised_choice
            ),
            "counterfactual_expectation": "flip",
            **(
                {
                    "allowed_choices": [intact_choice, compromised_choice],
                    "compromised_choice": compromised_choice,
                    "direct_state_choice": direct_state,
                    "decision_rule": (
                        (
                            "Return the exact value of the recovered blinding_state linked "
                            'to the access record: "intact" or "compromised". Choose '
                            '"compromised" when that derived state/link is missing. The '
                            "current request does not itself establish the state."
                        )
                        if direct_state
                        else (
                            'Use the recovered blinding_state linked to the access record. '
                            f'Choose "{intact_choice}" only for value=INTACT. Choose '
                            f'"{compromised_choice}" for value=COMPROMISED or when that '
                            "derived state/link is missing. The current request does not "
                            "itself establish analysis validity."
                        )
                    ),
                    "intact_choice": intact_choice,
                }
                if redesigned
                else {}
            ),
        },
    )
