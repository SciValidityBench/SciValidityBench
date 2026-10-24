"""A small deterministic Scientific State Graph with reversible patches."""

from __future__ import annotations

import copy
import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any


@dataclass
class GraphNode:
    node_id: str
    node_type: str
    attributes: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "attributes": copy.deepcopy(self.attributes),
            "node_id": self.node_id,
            "node_type": self.node_type,
        }


@dataclass
class GraphEdge:
    edge_id: str
    source: str
    target: str
    edge_type: str
    attributes: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "attributes": copy.deepcopy(self.attributes),
            "edge_id": self.edge_id,
            "edge_type": self.edge_type,
            "source": self.source,
            "target": self.target,
        }


@dataclass(frozen=True)
class GraphPatch:
    operation: str
    target_id: str
    payload: dict[str, Any] = field(default_factory=dict)
    reason: str = ""

    @classmethod
    def omit_node(cls, node_id: str, reason: str = "") -> GraphPatch:
        return cls("REMOVE_NODE", node_id, reason=reason)

    @classmethod
    def update_node(
        cls, node_id: str, attributes: Mapping[str, Any], reason: str = ""
    ) -> GraphPatch:
        return cls("UPDATE_NODE", node_id, {"attributes": dict(attributes)}, reason)

    @classmethod
    def remove_edge(cls, edge_id: str, reason: str = "") -> GraphPatch:
        return cls("REMOVE_EDGE", edge_id, reason=reason)

    @classmethod
    def update_edge(
        cls, edge_id: str, attributes: Mapping[str, Any], reason: str = ""
    ) -> GraphPatch:
        return cls("UPDATE_EDGE", edge_id, {"attributes": dict(attributes)}, reason)


class ScientificStateGraph:
    """Typed graph with stable JSON, visible projections and inverse patches."""

    schema_version = "0.1.0"

    def __init__(self, world_id: str):
        if not world_id:
            raise ValueError("world_id is required")
        self.world_id = world_id
        self.nodes: dict[str, GraphNode] = {}
        self.edges: dict[str, GraphEdge] = {}

    @staticmethod
    def edge_id(source: str, target: str, edge_type: str) -> str:
        return f"{source}|{edge_type}|{target}"

    def add_node(
        self, node_id: str, node_type: str, attributes: Mapping[str, Any] | None = None
    ) -> None:
        if node_id in self.nodes:
            raise ValueError(f"duplicate node: {node_id}")
        self.nodes[node_id] = GraphNode(node_id, node_type, dict(attributes or {}))

    def add_edge(
        self,
        source: str,
        target: str,
        edge_type: str,
        attributes: Mapping[str, Any] | None = None,
    ) -> str:
        if source not in self.nodes or target not in self.nodes:
            raise KeyError("both edge endpoints must exist")
        edge_id = self.edge_id(source, target, edge_type)
        if edge_id in self.edges:
            raise ValueError(f"duplicate edge: {edge_id}")
        self.edges[edge_id] = GraphEdge(
            edge_id, source, target, edge_type, dict(attributes or {})
        )
        return edge_id

    def to_dict(self) -> dict[str, Any]:
        return {
            "edges": [self.edges[key].to_dict() for key in sorted(self.edges)],
            "nodes": [self.nodes[key].to_dict() for key in sorted(self.nodes)],
            "schema_version": self.schema_version,
            "world_id": self.world_id,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> ScientificStateGraph:
        graph = cls(str(value["world_id"]))
        for node in value.get("nodes", []):
            graph.add_node(node["node_id"], node["node_type"], node.get("attributes"))
        for edge in value.get("edges", []):
            edge_id = graph.add_edge(
                edge["source"], edge["target"], edge["edge_type"], edge.get("attributes")
            )
            if edge_id != edge["edge_id"]:
                raise ValueError("edge_id is not canonical")
        return graph

    @property
    def graph_hash(self) -> str:
        encoded = json.dumps(
            self.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def clone(self) -> ScientificStateGraph:
        return self.from_dict(self.to_dict())

    def visible_view(self, episode: int) -> ScientificStateGraph:
        visible = ScientificStateGraph(self.world_id)
        for node_id in sorted(self.nodes):
            node = self.nodes[node_id]
            attrs = node.attributes
            if attrs.get("oracle_only", False):
                continue
            if int(attrs.get("visible_from", 0)) > episode:
                continue
            visible.add_node(node.node_id, node.node_type, attrs)
        for edge_id in sorted(self.edges):
            edge = self.edges[edge_id]
            if edge.source not in visible.nodes or edge.target not in visible.nodes:
                continue
            if edge.attributes.get("oracle_only", False):
                continue
            if int(edge.attributes.get("visible_from", 0)) > episode:
                continue
            visible.add_edge(edge.source, edge.target, edge.edge_type, edge.attributes)
        return visible

    def apply_patch(self, patch: GraphPatch) -> GraphPatch:
        if patch.operation == "REMOVE_NODE":
            node = self.nodes.pop(patch.target_id)
            removed_edges = [
                edge.to_dict()
                for edge in self.edges.values()
                if edge.source == patch.target_id or edge.target == patch.target_id
            ]
            for edge in removed_edges:
                self.edges.pop(edge["edge_id"])
            return GraphPatch(
                "RESTORE_NODE",
                patch.target_id,
                {"node": node.to_dict(), "edges": removed_edges},
                patch.reason,
            )
        if patch.operation == "RESTORE_NODE":
            node = patch.payload["node"]
            self.add_node(node["node_id"], node["node_type"], node["attributes"])
            for edge in patch.payload.get("edges", []):
                self.add_edge(
                    edge["source"], edge["target"], edge["edge_type"], edge["attributes"]
                )
            return GraphPatch.omit_node(patch.target_id, patch.reason)
        if patch.operation == "UPDATE_NODE":
            node = self.nodes[patch.target_id]
            before = copy.deepcopy(node.attributes)
            node.attributes.update(copy.deepcopy(patch.payload.get("attributes", {})))
            return GraphPatch("REPLACE_NODE_ATTRIBUTES", patch.target_id, {"attributes": before})
        if patch.operation == "REPLACE_NODE_ATTRIBUTES":
            node = self.nodes[patch.target_id]
            before = copy.deepcopy(node.attributes)
            node.attributes = copy.deepcopy(patch.payload["attributes"])
            return GraphPatch("REPLACE_NODE_ATTRIBUTES", patch.target_id, {"attributes": before})
        if patch.operation == "REMOVE_EDGE":
            edge = self.edges.pop(patch.target_id)
            return GraphPatch("RESTORE_EDGE", patch.target_id, {"edge": edge.to_dict()})
        if patch.operation == "RESTORE_EDGE":
            edge = patch.payload["edge"]
            self.add_edge(
                edge["source"], edge["target"], edge["edge_type"], edge["attributes"]
            )
            return GraphPatch.remove_edge(patch.target_id)
        if patch.operation == "UPDATE_EDGE":
            edge = self.edges[patch.target_id]
            before = copy.deepcopy(edge.attributes)
            edge.attributes.update(copy.deepcopy(patch.payload.get("attributes", {})))
            return GraphPatch(
                "REPLACE_EDGE_ATTRIBUTES",
                patch.target_id,
                {"attributes": before},
                patch.reason,
            )
        if patch.operation == "REPLACE_EDGE_ATTRIBUTES":
            edge = self.edges[patch.target_id]
            before = copy.deepcopy(edge.attributes)
            edge.attributes = copy.deepcopy(patch.payload["attributes"])
            return GraphPatch(
                "REPLACE_EDGE_ATTRIBUTES",
                patch.target_id,
                {"attributes": before},
                patch.reason,
            )
        raise ValueError(f"unknown graph patch operation: {patch.operation}")

    def diff(self, other: ScientificStateGraph) -> dict[str, list[str]]:
        return {
            "nodes_added": sorted(set(other.nodes) - set(self.nodes)),
            "nodes_removed": sorted(set(self.nodes) - set(other.nodes)),
            "nodes_changed": sorted(
                key
                for key in set(self.nodes) & set(other.nodes)
                if self.nodes[key].to_dict() != other.nodes[key].to_dict()
            ),
            "edges_added": sorted(set(other.edges) - set(self.edges)),
            "edges_removed": sorted(set(self.edges) - set(other.edges)),
            "edges_changed": sorted(
                key
                for key in set(self.edges) & set(other.edges)
                if self.edges[key].to_dict() != other.edges[key].to_dict()
            ),
        }
