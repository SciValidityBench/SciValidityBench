"""Deterministic memory representations used in the main evaluation.

The module is model-free and separates three representation questions:

* retrieval from public canonical events;
* generic event-graph organization without scientific governing relations;
* representation of identical compiled state as flat records versus an SSG.
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from scivaliditybench.core.events import CanonicalEvent, Visibility
from scivaliditybench.core.state_graph import ScientificStateGraph
from scivaliditybench.pipeline.domain import GeneratedWorld
from scivaliditybench.pipeline.projections import (
    MemoryProjection,
    counterfactual_state,
    project_compiled_state,
)


MEMORY_CONDITIONS: tuple[str, ...] = (
    "RAW_EVENTS",
    "BM25_EVENTS",
    "EVENT_GRAPH",
    "FLAT_SSG",
    "SVL",
)
COUNTERFACTUAL_CONDITIONS: tuple[str, ...] = ("FLAT_SSG", "SVL")
BM25_TOP_K = 5
BM25_BYTE_BUDGET = 4096
BM25_K1 = 1.2
BM25_B = 0.75

_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_]+")
_INTERNAL_ATTRIBUTE_KEYS = {
    "atomic_correct",
    "critical",
    "oracle_only",
    "salient",
    "seed",
    "visible_from",
}


@dataclass(frozen=True)
class BM25Hit:
    event: CanonicalEvent
    score: float


def _stable_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def public_events(world: GeneratedWorld) -> tuple[CanonicalEvent, ...]:
    """Return the complete non-oracle stream in canonical sequence order."""

    return tuple(
        sorted(
            (
                event
                for event in world.events
                if event.visibility is not Visibility.ORACLE
            ),
            key=lambda event: (event.sequence, event.event_id),
        )
    )


def _public_event_record(event: CanonicalEvent) -> dict[str, Any]:
    record = event.to_dict()
    record.pop("world_id", None)
    record.pop("schema_version", None)
    return record


def _tokens(value: object) -> list[str]:
    return [token.lower() for token in _TOKEN_PATTERN.findall(_stable_json(value))]


def bm25_query(world: GeneratedWorld) -> dict[str, object]:
    """Compile an oracle-free, task-independent query from the current request."""

    decisions = [
        event
        for event in public_events(world)
        if event.event_type.value == "DECIDE"
    ]
    current = decisions[-1] if decisions else None
    return {
        "allowed_choices": list(world.critical_state.get("allowed_choices", ())),
        "current_objects": list(current.objects) if current else [],
        "current_request": dict(current.payload) if current else {},
        "domain": world.spec.domain.value,
        "phenomenon": str(world.spec.generator.get("phenomenon", "")),
    }


def bm25_hits(world: GeneratedWorld) -> tuple[BM25Hit, ...]:
    """Rank one-event chunks with frozen BM25 parameters and ordering."""

    events = public_events(world)
    if not events:
        return ()
    documents = [_tokens(_public_event_record(event)) for event in events]
    query = Counter(_tokens(bm25_query(world)))
    document_frequencies = Counter(
        token for document in documents for token in set(document)
    )
    average_length = sum(len(document) for document in documents) / len(documents)
    hits: list[BM25Hit] = []
    for event, document in zip(events, documents, strict=True):
        frequencies = Counter(document)
        score = 0.0
        for token, query_frequency in query.items():
            frequency = frequencies[token]
            if not frequency:
                continue
            document_frequency = document_frequencies[token]
            inverse_document_frequency = math.log(
                1.0
                + (len(documents) - document_frequency + 0.5)
                / (document_frequency + 0.5)
            )
            denominator = frequency + BM25_K1 * (
                1.0 - BM25_B + BM25_B * len(document) / max(average_length, 1.0)
            )
            score += (
                query_frequency
                * inverse_document_frequency
                * frequency
                * (BM25_K1 + 1.0)
                / denominator
            )
        hits.append(BM25Hit(event=event, score=score))
    ranked = sorted(hits, key=lambda hit: (-hit.score, hit.event.sequence, hit.event.event_id))
    selected: list[BM25Hit] = []
    consumed = 0
    for hit in ranked[:BM25_TOP_K]:
        encoded = _stable_json(_public_event_record(hit.event)).encode("utf-8")
        separator = 1 if selected else 0
        if consumed + separator + len(encoded) > BM25_BYTE_BUDGET:
            continue
        selected.append(hit)
        consumed += separator + len(encoded)
    return tuple(selected)


def _event_graph(
    world: GeneratedWorld,
    events: Sequence[CanonicalEvent],
) -> ScientificStateGraph:
    """Build a generic event/object graph with no scientific relation compiler."""

    graph = ScientificStateGraph(world.world_id + ":generic-events")
    for event in events:
        graph.add_node(
            "event:" + event.event_id,
            "canonical_event",
            {
                "actor": event.actor,
                "cost": dict(event.cost),
                "episode_id": event.episode_id,
                "event_type": event.event_type.value,
                "payload": dict(event.payload),
                "provenance": dict(event.provenance),
                "sequence": event.sequence,
                "visibility": event.visibility.value,
            },
        )
    object_ids = sorted({object_id for event in events for object_id in event.objects})
    for object_id in object_ids:
        graph.add_node("object:" + object_id, "mentioned_object", {"id": object_id})
    for event in events:
        event_node = "event:" + event.event_id
        for object_id in event.objects:
            graph.add_edge(event_node, "object:" + object_id, "MENTIONS")
    ordered = sorted(events, key=lambda event: (event.sequence, event.event_id))
    for before, after in zip(ordered, ordered[1:]):
        graph.add_edge(
            "event:" + before.event_id,
            "event:" + after.event_id,
            "NEXT_EVENT",
        )
    return graph


def memory_projection(
    world: GeneratedWorld,
    condition: str,
    intervention: str = "original",
) -> MemoryProjection:
    normalized = condition.upper()
    if normalized not in MEMORY_CONDITIONS:
        raise ValueError(f"unknown memory condition: {condition}")

    if normalized in {"FLAT_SSG", "SVL"}:
        projection = project_compiled_state(world, normalized)
        projection = MemoryProjection(
            condition=normalized,
            graph=projection.graph,
            observable_event_ids=projection.observable_event_ids,
            atomic_correctness=projection.atomic_correctness,
        )
        if intervention == "counterfactual_state":
            return counterfactual_state(world, projection)
        if intervention != "original":
            raise ValueError(f"unsupported memory intervention: {intervention}")
        return projection

    if intervention != "original":
        raise ValueError(
            f"{normalized} is not registered for counterfactual intervention"
        )
    selected = (
        tuple(hit.event for hit in bm25_hits(world))
        if normalized == "BM25_EVENTS"
        else public_events(world)
    )
    graph = _event_graph(world, selected)
    return MemoryProjection(
        condition=normalized,
        graph=graph,
        observable_event_ids=tuple(event.event_id for event in selected),
        atomic_correctness=True,
    )


def _public_graph(graph: ScientificStateGraph) -> dict[str, object]:
    return {
        "nodes": [
            {
                "id": node.node_id,
                "type": node.node_type,
                "attributes": {
                    key: value
                    for key, value in sorted(node.attributes.items())
                    if key not in _INTERNAL_ATTRIBUTE_KEYS
                },
            }
            for node in sorted(graph.nodes.values(), key=lambda item: item.node_id)
            if node.node_id != "world"
        ],
        "relations": [
            {
                "source": edge.source,
                "relation": edge.edge_type,
                "target": edge.target,
                "attributes": {
                    key: value
                    for key, value in sorted(edge.attributes.items())
                    if key not in _INTERNAL_ATTRIBUTE_KEYS
                },
            }
            for edge in sorted(graph.edges.values(), key=lambda item: item.edge_id)
            if edge.source != "world" and edge.target != "world"
        ],
    }


def _render_flat_ssg(graph: ScientificStateGraph) -> str:
    public = _public_graph(graph)
    lines = ["Flat compiled-state records (unordered record semantics):"]
    for node in public["nodes"]:
        lines.append(
            "NODE\t"
            + _stable_json(
                {
                    "attributes": node["attributes"],
                    "id": node["id"],
                    "type": node["type"],
                }
            )
        )
    for edge in public["relations"]:
        lines.append(
            "RELATION\t"
            + _stable_json(
                {
                    "attributes": edge["attributes"],
                    "relation": edge["relation"],
                    "source": edge["source"],
                    "target": edge["target"],
                }
            )
        )
    return "\n".join(lines)


def render_memory(
    world: GeneratedWorld,
    condition: str,
    intervention: str = "original",
) -> str:
    normalized = condition.upper()
    projection = memory_projection(world, normalized, intervention)
    if normalized == "RAW_EVENTS":
        records = [_public_event_record(event) for event in public_events(world)]
        return "Complete public canonical event stream:\n" + "\n".join(
            _stable_json(record) for record in records
        )
    if normalized == "BM25_EVENTS":
        hits = bm25_hits(world)
        header = (
            "BM25 event retrieval: one-event chunks; top_k=5; byte_budget=4096; "
            "k1=1.2; b=0.75; ordering=score_desc_then_sequence_asc."
        )
        return header + "\n" + "\n".join(
            _stable_json(
                {
                    "event": _public_event_record(hit.event),
                    "rank": rank,
                    "score": round(hit.score, 8),
                }
            )
            for rank, hit in enumerate(hits, start=1)
        )
    if normalized == "EVENT_GRAPH":
        return "Generic event graph (no scientific governing relations):\n" + _stable_json(
            _public_graph(projection.graph)
        )
    if normalized == "FLAT_SSG":
        return _render_flat_ssg(projection.graph)
    if normalized == "SVL":
        return "Typed Scientific State Graph:\n" + _stable_json(
            _public_graph(projection.graph)
        )
    raise ValueError(f"unknown memory condition: {condition}")


def representation_contract() -> dict[str, object]:
    """Return the exact model-facing representation contract."""

    return {
        "BM25_EVENTS": {
            "b": BM25_B,
            "byte_budget": BM25_BYTE_BUDGET,
            "chunking": "one_public_canonical_event_per_chunk",
            "k1": BM25_K1,
            "ordering": "score_desc_then_sequence_asc",
            "query": "current_request+objects+domain+phenomenon+allowed_choices",
            "top_k": BM25_TOP_K,
        },
        "EVENT_GRAPH": {
            "edges": ["MENTIONS", "NEXT_EVENT"],
            "nodes": ["canonical_event", "mentioned_object"],
            "scientific_governing_relations": False,
        },
        "FLAT_SSG": {
            "content_identity_with": "SVL",
            "ordering_semantics": "flat_records",
        },
        "RAW_EVENTS": {
            "coverage": "complete_non_oracle_canonical_event_stream",
            "ordering": "sequence_asc_then_event_id",
        },
        "SVL": {
            "content_identity_with": "FLAT_SSG",
            "ordering_semantics": "typed_nodes_and_relations",
        },
    }


__all__ = [
    "BM25_B",
    "BM25_BYTE_BUDGET",
    "BM25_K1",
    "BM25_TOP_K",
    "MEMORY_CONDITIONS",
    "COUNTERFACTUAL_CONDITIONS",
    "bm25_hits",
    "bm25_query",
    "memory_projection",
    "public_events",
    "render_memory",
    "representation_contract",
]
