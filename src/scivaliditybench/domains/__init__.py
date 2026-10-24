"""Six domain adapters used by SciValidityBench."""

from scivaliditybench.domains.ab_testing import ABTestingAdapter
from scivaliditybench.domains.bioinformatics import BioinformaticsAdapter
from scivaliditybench.domains.causal import CausalAdapter
from scivaliditybench.domains.clinical import ClinicalAdapter
from scivaliditybench.domains.ml import MLAdapter
from scivaliditybench.domains.systems import SystemsAdapter

__all__ = [
    "ABTestingAdapter",
    "BioinformaticsAdapter",
    "CausalAdapter",
    "ClinicalAdapter",
    "MLAdapter",
    "SystemsAdapter",
]
