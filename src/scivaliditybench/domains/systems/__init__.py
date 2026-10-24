from typing import ClassVar

from scivaliditybench.core.specs import Domain
from scivaliditybench.domains.base import GeneratedDomainAdapter


class SystemsAdapter(GeneratedDomainAdapter):
    domain = Domain.SYSTEMS
    surface: ClassVar[dict[str, str]] = {
        "unit": "benchmark run",
        "artifact": "workload",
        "metric": "latency",
    }
    phenomenon_surfaces: ClassVar[dict[str, dict[str, str]]] = {
        "stopping_after_fast_run": {
            "unit": "benchmark repetition",
            "artifact": "runtime trace",
            "metric": "tail latency",
            "selection": "stopping decision",
        }
    }
    actions = ("warmup", "benchmark", "change_workload", "repeat", "decide")
