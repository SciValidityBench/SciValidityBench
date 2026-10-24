"""Shared implementation for deterministic domain adapters."""

from __future__ import annotations

from scivaliditybench.core.specs import Domain, TaskSpec
from scivaliditybench.pipeline.domain import DomainAdapter, GeneratedWorld
from scivaliditybench.states import STATE_BUILDERS


class GeneratedDomainAdapter(DomainAdapter):
    domain: Domain
    surface: dict[str, str]
    phenomenon_surfaces: dict[str, dict[str, str]] = {}
    actions: tuple[str, ...]

    def generate(self, spec: TaskSpec, seed: int) -> GeneratedWorld:
        if spec.domain is not self.domain:
            raise ValueError(f"{self.domain.value} adapter cannot generate {spec.domain.value}")
        builder = STATE_BUILDERS[spec.module.value]
        phenomenon = str(spec.generator["phenomenon"])
        surface = self.phenomenon_surfaces.get(phenomenon, self.surface)
        return builder(spec, seed, surface)

    def available_actions(self) -> tuple[str, ...]:
        return self.actions
