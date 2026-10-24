"""Canonical, byte-stable events shared by every benchmark domain."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

SCHEMA_VERSION = "0.1.0"


class EventType(str, Enum):
    PLAN = "PLAN"
    RUN = "RUN"
    OBSERVE = "OBSERVE"
    ACCESS = "ACCESS"
    WRITE = "WRITE"
    RETRIEVE = "RETRIEVE"
    DECIDE = "DECIDE"


class Visibility(str, Enum):
    PUBLIC = "public"
    SEALED = "sealed"
    ORACLE = "oracle"


def _json_safe(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_safe(item) for item in value]
    return value


@dataclass(frozen=True)
class CanonicalEvent:
    """A versioned event whose canonical serialization is reproducible."""

    event_id: str
    world_id: str
    episode_id: str
    event_type: EventType
    actor: str
    sequence: int
    objects: tuple[str, ...] = ()
    payload: dict[str, Any] = field(default_factory=dict)
    visibility: Visibility = Visibility.PUBLIC
    visible_from: int = 0
    cost: dict[str, float] = field(default_factory=dict)
    provenance: dict[str, Any] = field(default_factory=dict)
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not self.event_id or not self.world_id or not self.episode_id:
            raise ValueError("event_id, world_id, and episode_id are required")
        if self.sequence < 0 or self.visible_from < 0:
            raise ValueError("sequence and visible_from must be non-negative")

    def to_dict(self) -> dict[str, Any]:
        return {
            "actor": self.actor,
            "cost": {str(key): float(value) for key, value in self.cost.items()},
            "episode_id": self.episode_id,
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "objects": list(self.objects),
            "payload": _json_safe(self.payload),
            "provenance": _json_safe(self.provenance),
            "schema_version": self.schema_version,
            "sequence": self.sequence,
            "visibility": self.visibility.value,
            "visible_from": self.visible_from,
            "world_id": self.world_id,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> CanonicalEvent:
        return cls(
            event_id=str(value["event_id"]),
            world_id=str(value["world_id"]),
            episode_id=str(value["episode_id"]),
            event_type=EventType(value["event_type"]),
            actor=str(value["actor"]),
            sequence=int(value["sequence"]),
            objects=tuple(str(item) for item in value.get("objects", ())),
            payload=dict(value.get("payload", {})),
            visibility=Visibility(value.get("visibility", Visibility.PUBLIC.value)),
            visible_from=int(value.get("visible_from", 0)),
            cost={str(k): float(v) for k, v in value.get("cost", {}).items()},
            provenance=dict(value.get("provenance", {})),
            schema_version=str(value.get("schema_version", SCHEMA_VERSION)),
        )

    def canonical_json(self) -> str:
        return json.dumps(
            self.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )

    @property
    def content_hash(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()
