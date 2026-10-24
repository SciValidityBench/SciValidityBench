"""Versioned task specifications used by generators and runners."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Domain(str, Enum):
    ML = "ml"
    AB_TESTING = "ab_testing"
    CLINICAL = "clinical"
    BIOINFORMATICS = "bioinformatics"
    SYSTEMS = "systems"
    CAUSAL = "causal"


class StateModule(str, Enum):
    INFERENTIAL = "inferential"
    DISCLOSURE = "blind"
    CONSTRUCT = "construct"
    ABSENCE = "absence"
    RELEVANCE = "sunk_cost"


@dataclass(frozen=True)
class TaskSpec:
    template_id: str
    module: StateModule
    domain: Domain
    version: str
    generator: dict[str, Any]
    action_space: tuple[str, ...]
    budget: dict[str, float]
    episodes: int
    decision_schema: dict[str, Any]
    validator: str
    required_corruptions: tuple[str, ...] = ()
    calibration: dict[str, Any] = field(default_factory=dict)
    split_policy: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.template_id or not self.version or not self.validator:
            raise ValueError("template_id, version, and validator are required")
        if self.episodes < 2:
            raise ValueError("SciValidityBench tasks require at least two episodes")
        if not self.action_space:
            raise ValueError("action_space cannot be empty")
        if any(value < 0 for value in self.budget.values()):
            raise ValueError("budgets must be non-negative")

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_space": list(self.action_space),
            "budget": dict(self.budget),
            "calibration": dict(self.calibration),
            "decision_schema": dict(self.decision_schema),
            "domain": self.domain.value,
            "episodes": self.episodes,
            "generator": dict(self.generator),
            "module": self.module.value,
            "required_corruptions": list(self.required_corruptions),
            "split_policy": dict(self.split_policy),
            "template_id": self.template_id,
            "validator": self.validator,
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> TaskSpec:
        return cls(
            template_id=str(value["template_id"]),
            module=StateModule(value["module"]),
            domain=Domain(value["domain"]),
            version=str(value["version"]),
            generator=dict(value.get("generator", {})),
            action_space=tuple(value.get("action_space", ())),
            budget={str(k): float(v) for k, v in value.get("budget", {}).items()},
            episodes=int(value["episodes"]),
            decision_schema=dict(value.get("decision_schema", {})),
            validator=str(value["validator"]),
            required_corruptions=tuple(value.get("required_corruptions", ())),
            calibration=dict(value.get("calibration", {})),
            split_policy=dict(value.get("split_policy", {})),
        )
