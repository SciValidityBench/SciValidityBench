from typing import ClassVar

from scivaliditybench.core.specs import Domain
from scivaliditybench.domains.base import GeneratedDomainAdapter


class BioinformaticsAdapter(GeneratedDomainAdapter):
    domain = Domain.BIOINFORMATICS
    surface: ClassVar[dict[str, str]] = {
        "unit": "gene",
        "artifact": "assay",
        "metric": "adjusted_p",
    }
    phenomenon_surfaces: ClassVar[dict[str, dict[str, str]]] = {
        "pipeline_search": {
            "unit": "biological sample",
            "artifact": "analysis pipeline",
            "metric": "discovery score",
            "selection": "pipeline selection",
        }
    }
    actions = ("normalize", "test_gene", "change_pipeline", "adjust_fdr", "decide")
