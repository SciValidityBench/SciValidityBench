"""Public compiled-state projections and paired-state interventions."""

from __future__ import annotations

import copy
from dataclasses import dataclass

from scivaliditybench.core.state_graph import GraphPatch, ScientificStateGraph
from scivaliditybench.pipeline.domain import GeneratedWorld


@dataclass(frozen=True)
class MemoryProjection:
    """One model-visible projection of a generated scientific world."""

    condition: str
    graph: ScientificStateGraph
    observable_event_ids: tuple[str, ...]
    atomic_correctness: bool


def project_compiled_state(
    world: GeneratedWorld,
    condition: str = "SVL",
) -> MemoryProjection:
    """Expose the complete public scientific state without oracle-only fields."""

    normalized = condition.upper()
    if normalized not in {"FLAT_SSG", "SVL"}:
        raise ValueError("compiled-state condition must be FLAT_SSG or SVL")
    graph = world.visible_graph.clone()
    atomic_correctness = all(
        node.attributes.get("atomic_correct", True) is not False
        for node in graph.nodes.values()
    )
    return MemoryProjection(
        condition=normalized,
        graph=graph,
        observable_event_ids=world.observable_event_ids,
        atomic_correctness=atomic_correctness,
    )


def counterfactual_state(
    world: GeneratedWorld,
    projection: MemoryProjection,
) -> MemoryProjection:
    """Change registered public state values while preserving graph structure."""

    graph = projection.graph.clone()
    raw_patches = world.critical_state.get("counterfactual_patches")
    if raw_patches is None:
        node_id = str(world.critical_state.get("counterfactual_node", ""))
        attribute = str(world.critical_state.get("counterfactual_attribute", ""))
        if (
            not node_id
            or not attribute
            or "counterfactual_value" not in world.critical_state
        ):
            raise ValueError("world does not declare counterfactual patches")
        raw_patches = [
            {
                "kind": "node",
                "id": node_id,
                "attribute": attribute,
                "value": world.critical_state["counterfactual_value"],
            }
        ]
    if not isinstance(raw_patches, list) or not raw_patches:
        raise ValueError("counterfactual patches must be a non-empty list")

    for value in raw_patches:
        if not isinstance(value, dict):
            raise ValueError("counterfactual patch must be an object")
        kind = str(value.get("kind", ""))
        target_id = str(value.get("id", ""))
        attribute = str(value.get("attribute", ""))
        if not target_id or not attribute or "value" not in value:
            raise ValueError("counterfactual patch is incomplete")
        if kind == "node":
            if target_id not in graph.nodes:
                raise ValueError("counterfactual state requires the target node")
            patch = GraphPatch.update_node(
                target_id,
                {attribute: copy.deepcopy(value["value"])},
            )
        elif kind == "edge":
            if target_id not in graph.edges:
                raise ValueError("counterfactual state requires the target edge")
            patch = GraphPatch.update_edge(
                target_id,
                {attribute: copy.deepcopy(value["value"])},
            )
        else:
            raise ValueError("counterfactual patch kind must be node or edge")
        graph.apply_patch(patch)

    return MemoryProjection(
        condition=projection.condition,
        graph=graph,
        observable_event_ids=projection.observable_event_ids,
        atomic_correctness=projection.atomic_correctness,
    )


def counterfactual_oracle_decision(world: GeneratedWorld) -> str:
    """Return the registered action after the public state intervention."""

    registered = world.critical_state.get("counterfactual_oracle_decision")
    if registered is not None:
        return str(registered)
    if "counterfactual_value" not in world.critical_state:
        raise ValueError("world does not declare a counterfactual decision")
    if world.oracle_decision == "confirm":
        return "exploratory"
    if world.oracle_decision == "exploratory":
        return "confirm"
    raise ValueError("world does not declare a counterfactual decision")

