"""Helpers shared by state-specific deterministic generators."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from scivaliditybench.core.events import CanonicalEvent, EventType, Visibility
from scivaliditybench.core.specs import TaskSpec
from scivaliditybench.core.state_graph import ScientificStateGraph
from scivaliditybench.pipeline.domain import GeneratedWorld


def event(
    spec: TaskSpec,
    seed: int,
    sequence: int,
    event_type: EventType,
    actor: str,
    objects: Sequence[str],
    payload: Mapping[str, Any],
    *,
    episode: int,
    visibility: Visibility = Visibility.PUBLIC,
    cost: Mapping[str, float] | None = None,
) -> CanonicalEvent:
    world_id = f"{spec.template_id}:seed-{seed}"
    return CanonicalEvent(
        event_id=f"{world_id}:event-{sequence:03d}",
        world_id=world_id,
        episode_id=f"{world_id}:episode-{episode}",
        event_type=event_type,
        actor=actor,
        sequence=sequence,
        objects=tuple(objects),
        payload=dict(payload),
        visibility=visibility,
        visible_from=episode,
        cost=dict(cost or {}),
        provenance={"generator": spec.module.value, "template": spec.template_id},
    )


def base_graph(spec: TaskSpec, seed: int, surface: Mapping[str, str]) -> ScientificStateGraph:
    graph = ScientificStateGraph(f"{spec.template_id}:seed-{seed}")
    graph.add_node(
        "world",
        "world",
        {
            "domain": spec.domain.value,
            "phenomenon": spec.generator["phenomenon"],
            "seed": seed,
            "surface": dict(surface),
            "visible_from": 0,
        },
    )
    return graph


def finalize(
    spec: TaskSpec,
    seed: int,
    surface: Mapping[str, str],
    events: Iterable[CanonicalEvent],
    graph: ScientificStateGraph,
    oracle_decision: str,
    naive_decision: str,
    critical_state: dict[str, object],
) -> GeneratedWorld:
    return GeneratedWorld(
        spec=spec,
        seed=seed,
        world_id=f"{spec.template_id}:seed-{seed}",
        events=tuple(events),
        oracle_graph=graph,
        visible_graph=graph.visible_view(spec.episodes),
        oracle_decision=oracle_decision,
        naive_decision=naive_decision,
        critical_state=critical_state,
        surface=dict(surface),
    )
