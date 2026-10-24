from typing import ClassVar

from scivaliditybench.core.specs import Domain
from scivaliditybench.domains.base import GeneratedDomainAdapter


class ClinicalAdapter(GeneratedDomainAdapter):
    domain = Domain.CLINICAL
    surface: ClassVar[dict[str, str]] = {
        "unit": "participant",
        "artifact": "trial arm",
        "metric": "endpoint",
    }
    phenomenon_surfaces: ClassVar[dict[str, dict[str, str]]] = {
        "subgroup_search": {
            "unit": "participant subgroup",
            "artifact": "subgroup analysis",
            "metric": "treatment response",
            "selection": "subgroup selection",
        }
    }
    actions = ("enroll", "measure", "unblind", "select_endpoint", "decide")
