from __future__ import annotations

from dataclasses import replace

from scivaliditybench.corruptions import CorruptionOperator
from scivaliditybench.evaluation.scivalidity import SciValidityValidator
from scivaliditybench.pipeline.catalog import load_task_catalog
from scivaliditybench.pipeline.representations import memory_projection
from scivaliditybench.pipeline.mechanism import (
    apply_mechanism_intervention,
    mechanism_edit_signature,
)
from scivaliditybench.pipeline.projections import counterfactual_oracle_decision
from scivaliditybench.pipeline.registry import get_domain_adapter


def _world():
    spec = next(task for task in load_task_catalog() if task.template_id == "IL-ML-01")
    return get_domain_adapter(spec.domain).generate(spec, seed=7)


def test_counterfactual_pair_preserves_structure_and_changes_registered_action() -> None:
    world = _world()
    original = memory_projection(world, "SVL")
    paired = memory_projection(world, "SVL", "counterfactual_state")
    assert set(original.graph.nodes) == set(paired.graph.nodes)
    assert set(original.graph.edges) == set(paired.graph.edges)
    paired_world = replace(
        world,
        oracle_decision=counterfactual_oracle_decision(world),
    )
    assert paired_world.oracle_decision != world.oracle_decision
    assert SciValidityValidator().validate(
        paired_world,
        paired_world.oracle_decision,
        paired.graph,
    ).valid


def test_target_and_matched_repairs_have_equal_edit_size() -> None:
    world = _world()
    original = memory_projection(world, "SVL")
    operator = world.spec.required_corruptions[0]
    corrupted = apply_mechanism_intervention(world, original, operator, "corrupted")
    target = apply_mechanism_intervention(world, original, operator, "target_repair")
    matched = apply_mechanism_intervention(world, original, operator, "matched_repair")
    assert target.graph.to_dict() == original.graph.to_dict()
    assert mechanism_edit_signature(
        corrupted.graph,
        target.graph,
    ) == mechanism_edit_signature(corrupted.graph, matched.graph)


def test_all_six_corruption_operators_have_a_reversible_task() -> None:
    covered: set[CorruptionOperator] = set()
    for operator in CorruptionOperator:
        for spec in load_task_catalog():
            if operator.value not in spec.required_corruptions:
                continue
            world = get_domain_adapter(spec.domain).generate(spec, seed=7)
            original = memory_projection(world, "SVL")
            try:
                corrupted = apply_mechanism_intervention(
                    world,
                    original,
                    operator,
                    "corrupted",
                )
                target = apply_mechanism_intervention(
                    world,
                    original,
                    operator,
                    "target_repair",
                )
                matched = apply_mechanism_intervention(
                    world,
                    original,
                    operator,
                    "matched_repair",
                )
            except (KeyError, ValueError):
                continue
            assert target.graph.to_dict() == original.graph.to_dict()
            assert mechanism_edit_signature(
                corrupted.graph,
                target.graph,
            ) == mechanism_edit_signature(corrupted.graph, matched.graph)
            covered.add(operator)
            break
    assert covered == set(CorruptionOperator)
