"""Exercise the compiler, reader contract, counterfactual, and repair path."""

from __future__ import annotations

import json
from dataclasses import replace

from scivaliditybench.evaluation.scivalidity import SciValidityValidator
from scivaliditybench.pipeline.catalog import load_task_catalog
from scivaliditybench.pipeline.representations import memory_projection
from scivaliditybench.pipeline.mechanism import (
    apply_mechanism_intervention,
    mechanism_edit_signature,
)
from scivaliditybench.pipeline.projections import counterfactual_oracle_decision
from scivaliditybench.pipeline.reader import (
    build_reader_messages,
    decision_choices,
    parse_reader_choice,
)
from scivaliditybench.pipeline.registry import get_domain_adapter


def main() -> None:
    spec = next(task for task in load_task_catalog() if task.template_id == "IL-ML-01")
    world = get_domain_adapter(spec.domain).generate(spec, seed=7)
    original = memory_projection(world, "SVL")
    paired = memory_projection(world, "SVL", "counterfactual_state")

    messages = build_reader_messages(world, "SVL")
    simulated_response = json.dumps({"choice": world.oracle_decision})
    choice = parse_reader_choice(simulated_response, decision_choices(world))
    original_score = SciValidityValidator().validate(world, choice, original.graph)

    paired_world = replace(
        world,
        oracle_decision=counterfactual_oracle_decision(world),
    )
    paired_score = SciValidityValidator().validate(
        paired_world,
        paired_world.oracle_decision,
        paired.graph,
    )

    operator = spec.required_corruptions[0]
    corrupted = apply_mechanism_intervention(world, original, operator, "corrupted")
    target = apply_mechanism_intervention(world, original, operator, "target_repair")
    matched = apply_mechanism_intervention(world, original, operator, "matched_repair")

    print(
        json.dumps(
            {
                "counterfactual": {
                    "graph_shape_preserved": (
                        set(original.graph.nodes) == set(paired.graph.nodes)
                        and set(original.graph.edges) == set(paired.graph.edges)
                    ),
                    "original_valid": original_score.valid,
                    "paired_valid": paired_score.valid,
                },
                "reader": {
                    "message_count": len(messages),
                    "output_contract": {"choice": "<allowed choice>"},
                },
                "repair": {
                    "matched_edit_signature": mechanism_edit_signature(
                        corrupted.graph,
                        matched.graph,
                    ),
                    "target_edit_signature": mechanism_edit_signature(
                        corrupted.graph,
                        target.graph,
                    ),
                    "target_restores_compiled_state": (
                        target.graph.to_dict() == original.graph.to_dict()
                    ),
                },
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
