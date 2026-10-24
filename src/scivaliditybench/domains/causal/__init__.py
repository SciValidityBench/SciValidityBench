from typing import ClassVar

from scivaliditybench.core.specs import Domain
from scivaliditybench.domains.base import GeneratedDomainAdapter


class CausalAdapter(GeneratedDomainAdapter):
    domain = Domain.CAUSAL
    surface: ClassVar[dict[str, str]] = {
        "unit": "unit",
        "artifact": "sample",
        "metric": "effect",
    }
    phenomenon_surfaces: ClassVar[dict[str, dict[str, str]]] = {
        "sample_restriction": {
            "unit": "eligible unit",
            "artifact": "restricted sample",
            "metric": "causal effect",
            "selection": "sample restriction",
        }
    }
    actions = ("choose_outcome", "fit_specification", "restrict_sample", "estimate", "decide")
