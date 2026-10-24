"""Config-driven domain registry without environment-specific branching."""

from __future__ import annotations

from scivaliditybench.core.specs import Domain
from scivaliditybench.domains import (
    ABTestingAdapter,
    BioinformaticsAdapter,
    CausalAdapter,
    ClinicalAdapter,
    MLAdapter,
    SystemsAdapter,
)
from scivaliditybench.pipeline.domain import DomainAdapter

_DOMAIN_ADAPTERS: dict[Domain, DomainAdapter] = {
    Domain.ML: MLAdapter(),
    Domain.AB_TESTING: ABTestingAdapter(),
    Domain.CLINICAL: ClinicalAdapter(),
    Domain.BIOINFORMATICS: BioinformaticsAdapter(),
    Domain.SYSTEMS: SystemsAdapter(),
    Domain.CAUSAL: CausalAdapter(),
}


def get_domain_adapter(domain: Domain | str) -> DomainAdapter:
    normalized = domain if isinstance(domain, Domain) else Domain(domain)
    return _DOMAIN_ADAPTERS[normalized]


def list_domain_adapters() -> dict[Domain, DomainAdapter]:
    return dict(_DOMAIN_ADAPTERS)
