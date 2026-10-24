"""Inferential Ledger worlds with distributed search and stopping history."""

from __future__ import annotations

from collections.abc import Mapping

from scivaliditybench.core.events import EventType, Visibility
from scivaliditybench.core.specs import TaskSpec
from scivaliditybench.states.common import base_graph, event, finalize


def _build_source_independence_world(
    spec: TaskSpec, seed: int, surface: Mapping[str, str]
):
    graph = base_graph(spec, seed, surface)
    sufficient = seed % 2 == 0
    unique_sources = 2 if sufficient else 1
    counterfactual_sources = 1 if sufficient else 2
    graph.add_node(
        "plan",
        "analysis_plan",
        {"required_independent_sources": 2, "visible_from": 0, "critical": True},
    )
    graph.add_node(
        "evidence_registry",
        "evidence_registry",
        {
            "unique_sources": unique_sources,
            "atomic_correct": True,
            "visible_from": 2,
            "critical": True,
        },
    )
    graph.add_node(
        "selected_observation",
        "observation",
        {"record_id": "candidate-record", "visible_from": 2, "salient": True},
    )
    graph.add_node(
        "claim",
        "claim",
        {"status": "pending_source_audit", "visible_from": 3},
    )
    graph.add_node(
        "truth", "hidden_truth", {"sufficient": sufficient, "oracle_only": True}
    )
    registry_edge = graph.add_edge(
        "selected_observation",
        "evidence_registry",
        "REGISTERED_WITH",
        {"visible_from": 2},
    )
    plan_edge = graph.add_edge(
        "evidence_registry", "plan", "ASSESSED_UNDER", {"visible_from": 2}
    )
    graph.add_edge("claim", "selected_observation", "USES_EVIDENCE", {"visible_from": 3})
    events = [
        event(
            spec,
            seed,
            0,
            EventType.PLAN,
            "agent",
            ("plan",),
            {"required_independent_sources": 2},
            episode=0,
        ),
        event(
            spec,
            seed,
            1,
            EventType.OBSERVE,
            "environment",
            ("evidence_registry", "selected_observation"),
            {"unique_sources": unique_sources, "record_id": "candidate-record"},
            episode=2,
        ),
        event(
            spec,
            seed,
            2,
            EventType.DECIDE,
            "agent",
            ("claim", "selected_observation"),
            {"record_id": "candidate-record"},
            episode=3,
        ),
        event(
            spec,
            seed,
            3,
            EventType.OBSERVE,
            "validator",
            ("truth",),
            {"sufficient": sufficient},
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
        "confirm" if sufficient else "exploratory",
        "exploratory",
        {
            "required_nodes": ["plan", "evidence_registry"],
            "required_edges": [registry_edge, plan_edge],
            "primary_node": "evidence_registry",
            "primary_edge": registry_edge,
            "relabel_node": "evidence_registry",
            "merge_node": "evidence_registry",
            "duplicate_node": "selected_observation",
            "decision_primitive": "source_independence",
            "counterfactual_patches": [
                {
                    "kind": "node",
                    "id": "evidence_registry",
                    "attribute": "unique_sources",
                    "value": counterfactual_sources,
                }
            ],
            "counterfactual_oracle_decision": (
                "exploratory" if sufficient else "confirm"
            ),
            "counterfactual_expectation": "flip",
        },
    )


def _build_scope_membership_world(
    spec: TaskSpec, seed: int, surface: Mapping[str, str]
):
    graph = base_graph(spec, seed, surface)
    authorized = seed % 2 == 0
    allowed_scopes = ["primary"] if authorized else ["secondary"]
    counterfactual_scopes = ["secondary"] if authorized else ["primary"]
    graph.add_node(
        "plan",
        "analysis_plan",
        {"allowed_scopes": allowed_scopes, "visible_from": 0, "critical": True},
    )
    graph.add_node(
        "claim_scope",
        "claim_scope",
        {"requested_scope": "primary", "visible_from": 2, "critical": True},
    )
    graph.add_node(
        "claim", "claim", {"status": "pending_scope_audit", "visible_from": 3}
    )
    graph.add_node(
        "truth", "hidden_truth", {"authorized": authorized, "oracle_only": True}
    )
    authorization_edge = graph.add_edge(
        "claim_scope", "plan", "AUTHORIZED_BY", {"visible_from": 2}
    )
    graph.add_edge("claim", "claim_scope", "DECLARES_SCOPE", {"visible_from": 3})
    events = [
        event(
            spec,
            seed,
            0,
            EventType.PLAN,
            "agent",
            ("plan",),
            {"allowed_scopes": allowed_scopes},
            episode=0,
        ),
        event(
            spec,
            seed,
            1,
            EventType.OBSERVE,
            "environment",
            ("claim_scope",),
            {"requested_scope": "primary"},
            episode=2,
        ),
        event(
            spec,
            seed,
            2,
            EventType.DECIDE,
            "agent",
            ("claim", "claim_scope"),
            {"requested_scope": "primary"},
            episode=3,
        ),
        event(
            spec,
            seed,
            3,
            EventType.OBSERVE,
            "validator",
            ("truth",),
            {"authorized": authorized},
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
        "confirm" if authorized else "exploratory",
        "exploratory",
        {
            "required_nodes": ["plan", "claim_scope"],
            "required_edges": [authorization_edge],
            "primary_node": "plan",
            "primary_edge": authorization_edge,
            "relabel_node": "plan",
            "merge_node": "claim_scope",
            "duplicate_node": "claim_scope",
            "decision_primitive": "scope_membership",
            "counterfactual_patches": [
                {
                    "kind": "node",
                    "id": "plan",
                    "attribute": "allowed_scopes",
                    "value": counterfactual_scopes,
                }
            ],
            "counterfactual_oracle_decision": (
                "exploratory" if authorized else "confirm"
            ),
            "counterfactual_expectation": "flip",
        },
    )


def build_inferential_world(spec: TaskSpec, seed: int, surface: Mapping[str, str]):
    design = spec.generator.get("design_version")
    if design == "inferential_source_independence_v5":
        return _build_source_independence_world(spec, seed, surface)
    if design == "inferential_scope_membership_v6":
        return _build_scope_membership_world(spec, seed, surface)
    graph = base_graph(spec, seed, surface)
    # V3 orthogonalizes a direct categorical lookup from an integer comparison.
    # The four seed residues form a balanced primitive x oracle factorial.  The
    # current request stays constant, so only linked historical content can
    # distinguish the correct instance action.
    residue = seed % 4
    decision_primitive = "categorical" if residue in {0, 1} else "integer_limit"
    valid_confirmatory = residue in {0, 2}
    observed_exceedances = 8
    surface_transfer = (
        spec.generator.get("design_version")
        == "inferential_categorical_surface_transfer_v4"
    )
    confirm_code = "A7" if surface_transfer else "K"
    exploratory_code = "B4" if surface_transfer else "M"
    plan_attributes: dict[str, object] = {
        "decision_basis": decision_primitive,
        "locked": True,
        "visible_from": 0,
        "critical": True,
    }
    if decision_primitive == "categorical":
        plan_attributes["authorization_code"] = (
            confirm_code if valid_confirmatory else exploratory_code
        )
        counterfactual_attribute = "authorization_code"
        counterfactual_value = (
            exploratory_code if valid_confirmatory else confirm_code
        )
    else:
        plan_attributes["max_exceedances"] = 10 if valid_confirmatory else 6
        counterfactual_attribute = "max_exceedances"
        counterfactual_value = 6 if valid_confirmatory else 10
    # Hidden truth remains available for error-control summaries, but it does
    # not determine the instance-level programmatic action label.
    is_null = (seed * 17 + 3) % 5 < 2

    graph.add_node(
        "plan",
        "analysis_plan",
        plan_attributes,
    )
    graph.add_node(
        "ledger",
        "inferential_ledger",
        {
            "audit_window": 12,
            "evidence_identity": "candidate-record",
            "visible_from": 2,
            "critical": True,
        },
    )
    graph.add_node(
        "selected_observation",
        "observation",
        {
            "observed_exceedances": observed_exceedances,
            "atomic_correct": True,
            "visible_from": 2,
            "salient": True,
        },
    )
    graph.add_node(
        "claim",
        "claim",
        {
            "status": "candidate_confirmatory",
            "atomic_correct": True,
            "visible_from": 3,
            "salient": True,
        },
    )
    graph.add_node(
        "truth",
        "hidden_truth",
        {
            "false_positive_if_confirmed": is_null,
            "is_null": is_null,
            "oracle_only": True,
        },
    )
    selected_edge = graph.add_edge(
        "selected_observation", "ledger", "SELECTED_FROM", {"visible_from": 2}
    )
    plan_edge = graph.add_edge("ledger", "plan", "STOPPED_AFTER", {"visible_from": 2})
    graph.add_edge("claim", "selected_observation", "USES_EVIDENCE", {"visible_from": 3})

    events = [
        event(
            spec,
            seed,
            0,
            EventType.PLAN,
            "agent",
            ("plan",),
            {"decision_basis": decision_primitive},
            episode=0,
        ),
        event(
            spec,
            seed,
            1,
            EventType.OBSERVE,
            "environment",
            ("candidate-record", "ledger"),
            {
                "observed_exceedances": observed_exceedances,
                "atomic_correct": True,
            },
            episode=2,
            cost={"samples": 25},
        ),
    ]
    events.extend(
        [
            event(
                spec,
                seed,
                2,
                EventType.DECIDE,
                "agent",
                ("claim", "selected_observation"),
                {
                    "observed_exceedances": observed_exceedances,
                    "record_id": "candidate-record",
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
                {"oracle_decision": "confirm" if valid_confirmatory else "exploratory"},
                episode=3,
                visibility=Visibility.ORACLE,
            ),
        ]
    )
    return finalize(
        spec,
        seed,
        surface,
        events,
        graph,
        "confirm" if valid_confirmatory else "exploratory",
        "exploratory",
        {
            "required_nodes": ["plan", "ledger"],
            "required_edges": [selected_edge, plan_edge],
            "primary_node": "ledger",
            "primary_edge": selected_edge,
            "relabel_node": "claim",
            "merge_node": "selected_observation",
            "duplicate_node": "selected_observation",
            "decision_primitive": decision_primitive,
            "confirm_authorization_code": confirm_code,
            "exploratory_authorization_code": exploratory_code,
            "counterfactual_node": "plan",
            "counterfactual_attribute": counterfactual_attribute,
            "counterfactual_value": counterfactual_value,
        },
    )
