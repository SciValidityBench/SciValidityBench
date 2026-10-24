"""Operator-specific corruption and equal-edit repair projections."""

from __future__ import annotations

import copy
from collections.abc import Iterable, Mapping

from scivaliditybench.core.state_graph import GraphPatch, ScientificStateGraph
from scivaliditybench.corruptions import CorruptionOperator, apply_corruption
from scivaliditybench.pipeline.domain import GeneratedWorld
from scivaliditybench.pipeline.projections import MemoryProjection

MECHANISM_INTERVENTIONS: tuple[str, ...] = (
    "corrupted",
    "target_repair",
    "matched_repair",
)

_DIFF_KEYS = (
    "nodes_added",
    "nodes_removed",
    "nodes_changed",
    "edges_added",
    "edges_removed",
    "edges_changed",
)


def mechanism_edit_signature(
    left: ScientificStateGraph, right: ScientificStateGraph
) -> tuple[int, ...]:
    diff = left.diff(right)
    return tuple(len(diff[key]) for key in _DIFF_KEYS)


def _counterfactual_patches(world: GeneratedWorld) -> list[Mapping[str, object]]:
    raw = world.critical_state.get("counterfactual_patches")
    if isinstance(raw, list) and raw:
        return [value for value in raw if isinstance(value, Mapping)]
    node_id = str(world.critical_state.get("counterfactual_node", ""))
    attribute = str(world.critical_state.get("counterfactual_attribute", ""))
    if node_id and attribute and "counterfactual_value" in world.critical_state:
        return [
            {
                "kind": "node",
                "id": node_id,
                "attribute": attribute,
                "value": world.critical_state["counterfactual_value"],
            }
        ]
    return []


def _apply_semantic_patch(
    graph: ScientificStateGraph,
    value: Mapping[str, object],
    *,
    ambiguous: bool = False,
) -> GraphPatch:
    kind = str(value["kind"])
    target_id = str(value["id"])
    attribute = str(value["attribute"])
    replacement: object = value["value"]
    if ambiguous:
        replacement = "AMBIGUOUS" if kind == "node" else None
    if kind == "node":
        return graph.apply_patch(
            GraphPatch.update_node(
                target_id,
                {attribute: copy.deepcopy(replacement)},
                "mechanism corruption",
            )
        )
    if kind == "edge":
        return graph.apply_patch(
            GraphPatch.update_edge(
                target_id,
                {attribute: copy.deepcopy(replacement)},
                "mechanism corruption",
            )
        )
    raise ValueError("counterfactual patch kind must be node or edge")


def _corrupt(
    world: GeneratedWorld,
    projection: MemoryProjection,
    operator: CorruptionOperator,
) -> tuple[ScientificStateGraph, list[GraphPatch]]:
    graph = projection.graph.clone()
    inverses: list[GraphPatch] = []
    semantic = _counterfactual_patches(world)
    if operator is CorruptionOperator.RELABEL and semantic:
        inverses.extend(_apply_semantic_patch(graph, value) for value in semantic)
    elif operator is CorruptionOperator.MERGE and semantic:
        inverses.append(_apply_semantic_patch(graph, semantic[0], ambiguous=True))
    else:
        applied = apply_corruption(graph, operator, world.critical_state)
        if applied is None:
            raise ValueError(
                f"operator {operator.value} is not applicable to {world.spec.template_id}"
            )
        inverses.append(applied.inverse)
    return graph, inverses


def _target_repair(
    corrupted: ScientificStateGraph, inverses: Iterable[GraphPatch]
) -> ScientificStateGraph:
    graph = corrupted.clone()
    for patch in reversed(tuple(inverses)):
        graph.apply_patch(patch)
    return graph


def _candidate_nodes(
    graph: ScientificStateGraph, world: GeneratedWorld
) -> list[str]:
    required = {str(value) for value in world.critical_state.get("required_nodes", [])}
    preferred = [
        node_id
        for node_id in sorted(graph.nodes)
        if node_id not in required and node_id != "world"
    ]
    fallback = [
        node_id
        for node_id in sorted(graph.nodes)
        if node_id in required and node_id not in preferred
    ]
    return preferred + fallback + (["world"] if "world" in graph.nodes else [])


def _candidate_edges(
    graph: ScientificStateGraph, world: GeneratedWorld
) -> list[str]:
    required = {str(value) for value in world.critical_state.get("required_edges", [])}
    preferred = [edge_id for edge_id in sorted(graph.edges) if edge_id not in required]
    fallback = [edge_id for edge_id in sorted(graph.edges) if edge_id in required]
    return preferred + fallback


def _add_control_edge(
    graph: ScientificStateGraph,
    world: GeneratedWorld,
    index: int,
    edge_type: str = "CONTROL_CONTEXT",
) -> None:
    nodes = [node_id for node_id in sorted(graph.nodes) if node_id != "world"]
    for source in nodes:
        for target in nodes:
            candidate_type = edge_type if index == 0 else f"{edge_type}_{index}"
            edge_id = ScientificStateGraph.edge_id(source, target, candidate_type)
            if edge_id not in graph.edges:
                graph.add_edge(
                    source,
                    target,
                    candidate_type,
                    {"scientifically_relevant": False, "status": "matched_control"},
                )
                return
    raise ValueError("could not create a matched control edge")


def _matched_repair(
    world: GeneratedWorld,
    corrupted: ScientificStateGraph,
    target: ScientificStateGraph,
    operator: CorruptionOperator,
) -> ScientificStateGraph:
    """Apply an irrelevant edit with exactly the target repair's graph signature."""

    graph = corrupted.clone()
    signature = mechanism_edit_signature(corrupted, target)
    target_counts = dict(zip(_DIFF_KEYS, signature, strict=True))

    if target_counts["nodes_added"]:
        for index in range(target_counts["nodes_added"]):
            graph.add_node(
                f"matched_context_{index}",
                "context_record",
                {"scientifically_relevant": False, "status": "archived"},
            )
    if target_counts["edges_added"]:
        for index in range(target_counts["edges_added"]):
            _add_control_edge(graph, world, index)
    if target_counts["nodes_changed"]:
        candidates = _candidate_nodes(graph, world)
        if len(candidates) < target_counts["nodes_changed"]:
            raise ValueError("insufficient nodes for matched repair")
        for index, node_id in enumerate(candidates[: target_counts["nodes_changed"]]):
            graph.apply_patch(
                GraphPatch.update_node(
                    node_id,
                    {f"matched_control_{index}": "irrelevant_annotation"},
                )
            )
    if target_counts["edges_changed"]:
        candidates = _candidate_edges(graph, world)
        if len(candidates) < target_counts["edges_changed"]:
            raise ValueError("insufficient edges for matched repair")
        for index, edge_id in enumerate(candidates[: target_counts["edges_changed"]]):
            graph.apply_patch(
                GraphPatch.update_edge(
                    edge_id,
                    {f"matched_control_{index}": "irrelevant_annotation"},
                )
            )

    # INJECT and DUPLICATE target repairs remove one added node and one edge.
    # Remove an equally shaped but non-target fragment while retaining the damage.
    if target_counts["nodes_removed"]:
        if operator is CorruptionOperator.INJECT and "world" in graph.nodes:
            graph.apply_patch(GraphPatch.omit_node("world"))
        else:
            removable = _candidate_nodes(graph, world)
            node_id = "world" if "world" in removable else removable[-1]
            graph.apply_patch(GraphPatch.omit_node(node_id))
    current = corrupted.diff(graph)
    remaining_edge_removals = target_counts["edges_removed"] - len(
        current["edges_removed"]
    )
    if remaining_edge_removals > 0:
        candidates = _candidate_edges(graph, world)
        if len(candidates) < remaining_edge_removals:
            raise ValueError("insufficient edges for matched removal")
        for edge_id in candidates[:remaining_edge_removals]:
            graph.apply_patch(GraphPatch.remove_edge(edge_id))

    if mechanism_edit_signature(corrupted, graph) != signature:
        raise ValueError("matched repair does not match target edit signature")
    return graph


def apply_mechanism_intervention(
    world: GeneratedWorld,
    projection: MemoryProjection,
    operator: CorruptionOperator | str,
    intervention: str,
) -> MemoryProjection:
    """Return corrupted, exactly repaired, or equal-edit control memory."""

    normalized_operator = (
        operator if isinstance(operator, CorruptionOperator) else CorruptionOperator(operator)
    )
    if normalized_operator.value not in world.spec.required_corruptions:
        raise ValueError("operator is not registered for this task")
    if intervention not in MECHANISM_INTERVENTIONS:
        raise ValueError(f"unknown mechanism intervention: {intervention}")
    corrupted, inverses = _corrupt(world, projection, normalized_operator)
    target = _target_repair(corrupted, inverses)
    if target.graph_hash != projection.graph.graph_hash:
        raise ValueError("target repair failed to restore the original graph")
    if intervention == "corrupted":
        graph = corrupted
    elif intervention == "target_repair":
        graph = target
    else:
        graph = _matched_repair(world, corrupted, target, normalized_operator)
    return MemoryProjection(
        condition=projection.condition,
        graph=graph,
        observable_event_ids=projection.observable_event_ids,
        atomic_correctness=projection.atomic_correctness,
    )


__all__ = [
    "MECHANISM_INTERVENTIONS",
    "apply_mechanism_intervention",
    "mechanism_edit_signature",
]
