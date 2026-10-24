"""Reversible Scientific State Graph corruption operators."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum

from scivaliditybench.core.state_graph import GraphPatch, ScientificStateGraph


class CorruptionOperator(str, Enum):
    OMIT = "OMIT"
    UNLINK = "UNLINK"
    MERGE = "MERGE"
    RELABEL = "RELABEL"
    INJECT = "INJECT"
    DUPLICATE = "DUPLICATE"


@dataclass(frozen=True)
class AppliedCorruption:
    operator: CorruptionOperator
    inverse: GraphPatch
    affected_id: str


def apply_corruption(
    graph: ScientificStateGraph,
    operator: CorruptionOperator | str,
    critical_state: Mapping[str, object],
) -> AppliedCorruption | None:
    normalized = operator if isinstance(operator, CorruptionOperator) else CorruptionOperator(operator)
    primary_node = str(critical_state.get("primary_node", ""))
    primary_edge = str(critical_state.get("primary_edge", ""))

    if normalized is CorruptionOperator.OMIT:
        if primary_node not in graph.nodes:
            return None
        inverse = graph.apply_patch(GraphPatch.omit_node(primary_node, "OMIT"))
        return AppliedCorruption(normalized, inverse, primary_node)

    if normalized is CorruptionOperator.UNLINK:
        if primary_edge not in graph.edges:
            return None
        inverse = graph.apply_patch(GraphPatch.remove_edge(primary_edge, "UNLINK"))
        return AppliedCorruption(normalized, inverse, primary_edge)

    if normalized is CorruptionOperator.MERGE:
        target = str(critical_state.get("merge_node", primary_node))
        if target not in graph.nodes:
            return None
        inverse = graph.apply_patch(
            GraphPatch.update_node(
                target,
                {"identity_collapsed": True, "merged_with": "distinct-object"},
                "MERGE",
            )
        )
        return AppliedCorruption(normalized, inverse, target)

    if normalized is CorruptionOperator.RELABEL:
        target = str(critical_state.get("relabel_node", primary_node))
        if target not in graph.nodes:
            return None
        inverse = graph.apply_patch(
            GraphPatch.update_node(target, {"corrupted_label": "confirmatory"}, "RELABEL")
        )
        return AppliedCorruption(normalized, inverse, target)

    if normalized is CorruptionOperator.INJECT:
        target = "injected_irrelevant_cost"
        if target in graph.nodes or "world" not in graph.nodes:
            return None
        graph.add_node(
            target,
            "cost_event",
            {"amount": 10000, "sunk": True, "normatively_irrelevant": True},
        )
        graph.add_edge(target, "world", "INJECTED_INTO", {})
        return AppliedCorruption(normalized, GraphPatch.omit_node(target, "INJECT inverse"), target)

    if normalized is CorruptionOperator.DUPLICATE:
        source = str(critical_state.get("duplicate_node", primary_node))
        target = f"{source}__duplicate"
        if source not in graph.nodes or target in graph.nodes:
            return None
        original = graph.nodes[source]
        attributes = dict(original.attributes)
        attributes["duplicate_of"] = source
        graph.add_node(target, original.node_type, attributes)
        graph.add_edge(target, source, "DUPLICATE_OF", {})
        return AppliedCorruption(normalized, GraphPatch.omit_node(target, "DUPLICATE inverse"), target)

    raise AssertionError("unreachable")


__all__ = ["AppliedCorruption", "CorruptionOperator", "apply_corruption"]
