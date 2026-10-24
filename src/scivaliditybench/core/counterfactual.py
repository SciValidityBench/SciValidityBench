"""Canonical counterfactual-relation vocabulary shared by builders and audits.

The stored value is part of the scientific row contract.  It is deliberately
not normalized through aliases: accepting a second spelling would hide a
generator/analyzer contract drift instead of failing closed.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Final


FLIP: Final = "flip"
INVARIANT: Final = "invariant"
NOT_APPLICABLE: Final = "not_applicable"

COUNTERFACTUAL_EXPECTATION_VOCABULARY: Final = (
    FLIP,
    INVARIANT,
    NOT_APPLICABLE,
)
PAIRED_COUNTERFACTUAL_EXPECTATIONS: Final = frozenset({FLIP, INVARIANT})
COUNTERFACTUAL_EXPECTATION_CONTRACT: Final[Mapping[str, str]] = {
    FLIP: "paired_choice_must_differ_from_original_choice",
    INVARIANT: "paired_choice_must_equal_original_choice",
    NOT_APPLICABLE: "no_registered_counterfactual_pair",
}


def validate_counterfactual_expectation(
    value: object,
    *,
    paired: bool = False,
) -> str:
    """Return one exact canonical token or raise on vocabulary drift."""

    if not isinstance(value, str) or value not in COUNTERFACTUAL_EXPECTATION_VOCABULARY:
        raise ValueError("invalid canonical counterfactual expectation")
    if paired and value not in PAIRED_COUNTERFACTUAL_EXPECTATIONS:
        raise ValueError("counterfactual expectation is not applicable to a pair")
    return value


def counterfactual_relation_satisfied(
    expectation: object,
    original_choice: object,
    paired_choice: object,
) -> bool:
    """Evaluate a parsed pair against the exact registered relation."""

    canonical = validate_counterfactual_expectation(expectation, paired=True)
    same = original_choice == paired_choice
    return same if canonical == INVARIANT else not same


__all__ = [
    "COUNTERFACTUAL_EXPECTATION_CONTRACT",
    "COUNTERFACTUAL_EXPECTATION_VOCABULARY",
    "FLIP",
    "INVARIANT",
    "NOT_APPLICABLE",
    "PAIRED_COUNTERFACTUAL_EXPECTATIONS",
    "counterfactual_relation_satisfied",
    "validate_counterfactual_expectation",
]
