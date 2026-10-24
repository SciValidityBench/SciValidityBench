"""Domain adapter contract and generated-world data model."""

from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass

from scivaliditybench.core.events import CanonicalEvent, Visibility
from scivaliditybench.core.specs import Domain, TaskSpec
from scivaliditybench.core.state_graph import ScientificStateGraph


@dataclass(frozen=True)
class GeneratedWorld:
    spec: TaskSpec
    seed: int
    world_id: str
    events: tuple[CanonicalEvent, ...]
    oracle_graph: ScientificStateGraph
    visible_graph: ScientificStateGraph
    oracle_decision: str
    naive_decision: str
    critical_state: dict[str, object]
    surface: dict[str, str]

    @property
    def observable_event_ids(self) -> tuple[str, ...]:
        return tuple(
            event.event_id
            for event in self.events
            if event.visibility is not Visibility.ORACLE
        )

    @property
    def event_log_hash(self) -> str:
        joined = "\n".join(event.canonical_json() for event in self.events)
        return hashlib.sha256(joined.encode("utf-8")).hexdigest()


class DomainAdapter(ABC):
    domain: Domain

    @abstractmethod
    def generate(self, spec: TaskSpec, seed: int) -> GeneratedWorld:
        """Generate a deterministic paired world for one task template."""

    @abstractmethod
    def available_actions(self) -> tuple[str, ...]:
        """Return the domain-specific scientific actions available to every condition."""
