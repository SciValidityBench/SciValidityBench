"""Programmatic validators and metrics for SciValidityBench worlds."""

from __future__ import annotations

from dataclasses import dataclass

from scivaliditybench.core.state_graph import ScientificStateGraph
from scivaliditybench.pipeline.domain import GeneratedWorld


@dataclass(frozen=True)
class SciValidityResult:
    valid: bool
    violations: tuple[str, ...]
    regret: float
    evidence_trace: tuple[str, ...]
    decision: str
    oracle_decision: str


class SciValidityValidator:
    """No-LLM validator whose labels come only from generated hidden truth."""

    def validate(
        self,
        world: GeneratedWorld,
        decision: str,
        used_graph: ScientificStateGraph,
    ) -> SciValidityResult:
        required_nodes = tuple(
            str(item) for item in world.critical_state.get("required_nodes", [])
        )
        required_edges = tuple(
            str(item) for item in world.critical_state.get("required_edges", [])
        )
        evidence_trace = tuple(
            item
            for item in (*required_nodes, *required_edges)
            if item in used_graph.nodes or item in used_graph.edges
        )
        violations = []
        if decision != world.oracle_decision:
            violations.append(f"invalid_{world.spec.module.value}_decision")
        if len(evidence_trace) < len(required_nodes) + len(required_edges):
            violations.append("incomplete_global_state")
        valid = not violations or (
            decision == world.oracle_decision and violations == ["incomplete_global_state"]
        )
        return SciValidityResult(
            valid=valid,
            violations=tuple(violations),
            regret=0.0 if decision == world.oracle_decision else 1.0,
            evidence_trace=evidence_trace,
            decision=decision,
            oracle_decision=world.oracle_decision,
        )


def state_fidelity(
    reference: ScientificStateGraph, candidate: ScientificStateGraph
) -> dict[str, float]:
    node_total = max(1, len(reference.nodes))
    edge_total = max(1, len(reference.edges))
    node_matches = sum(
        node_id in candidate.nodes
        and candidate.nodes[node_id].to_dict() == node.to_dict()
        for node_id, node in reference.nodes.items()
    )
    edge_matches = sum(
        edge_id in candidate.edges
        and candidate.edges[edge_id].to_dict() == edge.to_dict()
        for edge_id, edge in reference.edges.items()
    )
    node_fidelity = node_matches / node_total
    edge_fidelity = edge_matches / edge_total
    return {
        "node_fidelity": node_fidelity,
        "edge_fidelity": edge_fidelity,
        "state_fidelity": (node_matches + edge_matches)
        / max(1, len(reference.nodes) + len(reference.edges)),
    }


def counterfactual_repair_gain(original: SciValidityResult, repaired: SciValidityResult) -> float:
    return float(repaired.valid) - float(original.valid)
