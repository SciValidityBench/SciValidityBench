from typing import ClassVar

from scivaliditybench.core.specs import Domain
from scivaliditybench.domains.base import GeneratedDomainAdapter


class ABTestingAdapter(GeneratedDomainAdapter):
    domain = Domain.AB_TESTING
    surface: ClassVar[dict[str, str]] = {
        "unit": "visitor",
        "artifact": "cohort",
        "metric": "conversion",
    }
    phenomenon_surfaces: ClassVar[dict[str, dict[str, str]]] = {
        "metric_family": {
            "unit": "visitor cohort",
            "artifact": "metric family",
            "metric": "family-adjusted conversion",
            "selection": "metric-family selection",
        }
    }
    actions = ("assign", "peek", "extend_sample", "select_metric", "decide")
