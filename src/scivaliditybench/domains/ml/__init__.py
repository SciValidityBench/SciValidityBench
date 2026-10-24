from typing import ClassVar

from scivaliditybench.core.specs import Domain
from scivaliditybench.domains.base import GeneratedDomainAdapter


class MLAdapter(GeneratedDomainAdapter):
    domain = Domain.ML
    surface: ClassVar[dict[str, str]] = {
        "unit": "seed run",
        "artifact": "holdout",
        "metric": "score",
    }
    phenomenon_surfaces: ClassVar[dict[str, dict[str, str]]] = {
        "holdout_reuse": {
            "unit": "evaluation round",
            "artifact": "sealed holdout",
            "metric": "generalization score",
            "selection": "holdout reuse decision",
        }
    }
    actions = ("train", "evaluate", "select_metric", "reuse_holdout", "decide")
