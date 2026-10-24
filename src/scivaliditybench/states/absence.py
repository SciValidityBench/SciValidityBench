"""Absence-algebra worlds with explicit missingness mechanisms."""

from __future__ import annotations

from collections.abc import Mapping

from scivaliditybench.core.events import EventType, Visibility
from scivaliditybench.core.specs import TaskSpec
from scivaliditybench.states.common import base_graph, event, finalize

_MECHANISMS = ("NOT_RUN", "FAILED", "TRUE_ZERO", "BELOW_DETECTION")
_DECISIONS = {
    "NOT_RUN": "run",
    "FAILED": "rerun",
    "TRUE_ZERO": "record_zero",
    "BELOW_DETECTION": "censored_model",
}
_COUNTERFACTUAL_MECHANISMS = {
    "NOT_RUN": "FAILED",
    "FAILED": "NOT_RUN",
    "TRUE_ZERO": "BELOW_DETECTION",
    "BELOW_DETECTION": "TRUE_ZERO",
}

_REDESIGNED_DECISIONS = {
    "NOT_RUN": "initiate_first_measurement",
    "FAILED": "repeat_failed_measurement",
    "TRUE_ZERO": "record_confirmed_zero",
    "BELOW_DETECTION": "fit_censored_observation_model",
}


def _build_evidence_chain_world(
    spec: TaskSpec, seed: int, surface: Mapping[str, str]
):
    graph = base_graph(spec, seed, surface)
    mechanism = _MECHANISMS[seed % len(_MECHANISMS)]
    counterfactual_mechanism = _COUNTERFACTUAL_MECHANISMS[mechanism]
    attempt_status = "not_started" if mechanism == "NOT_RUN" else "completed"
    instrument_status = {
        "NOT_RUN": "not_applicable",
        "FAILED": "error",
        "TRUE_ZERO": "validated",
        "BELOW_DETECTION": "below_limit",
    }[mechanism]
    graph.add_node(
        "attempt",
        "measurement_attempt",
        {"status": attempt_status, "visible_from": 1, "atomic_correct": True},
    )
    graph.add_node(
        "instrument",
        "instrument_state",
        {"status": instrument_status, "visible_from": 1, "atomic_correct": True},
    )
    graph.add_node(
        "absence_state",
        "absence_state",
        {"value": mechanism, "visible_from": 2, "critical": True, "atomic_correct": True},
    )
    graph.add_node(
        "artifact", "artifact", {"identity": f"sample-{seed}", "visible_from": 1}
    )
    graph.add_node(
        "claim", "claim", {"status": "pending_missingness_triage", "visible_from": 3}
    )
    graph.add_node("truth", "hidden_truth", {"mechanism": mechanism, "oracle_only": True})
    attempt_edge = graph.add_edge(
        "attempt", "absence_state", "DERIVED_AS", {"visible_from": 2}
    )
    instrument_edge = graph.add_edge(
        "instrument", "absence_state", "DERIVED_AS", {"visible_from": 2}
    )
    graph.add_edge("artifact", "absence_state", "HAS_ABSENCE_STATE", {"visible_from": 2})
    events = [
        event(
            spec,
            seed,
            0,
            EventType.RUN,
            "environment",
            ("attempt", "artifact"),
            {"attempt_status": attempt_status},
            episode=1,
        ),
        event(
            spec,
            seed,
            1,
            EventType.OBSERVE,
            "environment",
            ("instrument", "absence_state"),
            {"instrument_status": instrument_status, "derived_state": mechanism},
            episode=2,
        ),
        event(
            spec,
            seed,
            2,
            EventType.DECIDE,
            "agent",
            ("claim",),
            {"requested_assessment": "select_registered_missingness_action"},
            episode=3,
        ),
        event(
            spec,
            seed,
            3,
            EventType.OBSERVE,
            "validator",
            ("truth",),
            {"mechanism": mechanism},
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
        _REDESIGNED_DECISIONS[mechanism],
        "initiate_first_measurement",
        {
            "required_nodes": ["attempt", "instrument", "absence_state"],
            "required_edges": [attempt_edge, instrument_edge],
            "primary_node": "absence_state",
            "primary_edge": attempt_edge,
            "relabel_node": "absence_state",
            "merge_node": "attempt",
            "duplicate_node": "artifact",
            "decision_primitive": "absence_evidence_chain",
            "allowed_choices": list(_REDESIGNED_DECISIONS.values()),
            "counterfactual_patches": [
                {
                    "kind": "node",
                    "id": "absence_state",
                    "attribute": "value",
                    "value": counterfactual_mechanism,
                }
            ],
            "counterfactual_oracle_decision": _REDESIGNED_DECISIONS[
                counterfactual_mechanism
            ],
            "counterfactual_expectation": "flip",
        },
    )


def build_absence_world(spec: TaskSpec, seed: int, surface: Mapping[str, str]):
    if spec.generator.get("design_version") == "absence_evidence_chain_v3":
        return _build_evidence_chain_world(spec, seed, surface)
    graph = base_graph(spec, seed, surface)
    redesigned = (
        spec.generator.get("design_version")
        == "absence_unambiguous_actions_v2"
    )
    decisions = _REDESIGNED_DECISIONS if redesigned else _DECISIONS
    mechanism = _MECHANISMS[seed % len(_MECHANISMS)]
    counterfactual_mechanism = _COUNTERFACTUAL_MECHANISMS[mechanism]
    graph.add_node(
        "absence",
        "absence_event",
        {
            "mechanism": mechanism,
            "visible_from": 1,
            "critical": True,
            "atomic_correct": True,
        },
    )
    graph.add_node("artifact", "artifact", {"identity": f"sample-{seed}", "visible_from": 1})
    graph.add_node(
        "claim",
        "claim",
        {
            "status": "pending_missingness_triage" if redesigned else "missing_as_zero",
            "visible_from": 3,
        },
    )
    graph.add_node("truth", "hidden_truth", {"mechanism": mechanism, "oracle_only": True})
    absence_edge = graph.add_edge(
        "artifact", "absence", "ABSENT_BECAUSE", {"mechanism": mechanism, "visible_from": 1}
    )
    events = [
        event(
            spec,
            seed,
            0,
            EventType.RUN,
            "environment",
            ("artifact",),
            {"attempted": mechanism != "NOT_RUN"},
            episode=1,
        ),
        event(
            spec,
            seed,
            1,
            EventType.OBSERVE,
            "environment",
            ("absence", "artifact"),
            {"mechanism": mechanism},
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
                {"requested_assessment": "select_registered_missingness_action"}
                if redesigned
                else {"missing_value": None}
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
            {"mechanism": mechanism},
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
        decisions[mechanism],
        (
            "repeat_failed_measurement"
            if redesigned
            else "record_zero"
        ),
        {
            "required_nodes": ["absence"],
            "required_edges": [absence_edge],
            "primary_node": "absence",
            "primary_edge": absence_edge,
            "relabel_node": "absence",
            "merge_node": "artifact",
            "duplicate_node": "artifact",
            "decision_primitive": "absence_mechanism",
            "counterfactual_patches": [
                {
                    "kind": "node",
                    "id": "absence",
                    "attribute": "mechanism",
                    "value": counterfactual_mechanism,
                },
                {
                    "kind": "edge",
                    "id": absence_edge,
                    "attribute": "mechanism",
                    "value": counterfactual_mechanism,
                },
            ],
            "counterfactual_oracle_decision": decisions[counterfactual_mechanism],
            "counterfactual_expectation": "flip",
            **(
                {
                    "allowed_choices": list(_REDESIGNED_DECISIONS.values()),
                    "decision_rule": (
                        "Use only the recovered ABSENT_BECAUSE mechanism and the exact "
                        "registered mapping: NOT_RUN -> initiate_first_measurement; "
                        "FAILED -> repeat_failed_measurement; TRUE_ZERO -> "
                        "record_confirmed_zero; BELOW_DETECTION -> "
                        "fit_censored_observation_model. The four action codes are "
                        "distinct; do not replace initiate_first_measurement with "
                        "repeat_failed_measurement."
                    ),
                }
                if redesigned
                else {}
            ),
        },
    )
