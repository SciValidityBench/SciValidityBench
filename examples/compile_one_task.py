"""Compile one TaskSpec into the five memory views used in the paper."""

from __future__ import annotations

import argparse
import json

from scivaliditybench.pipeline.catalog import load_task_catalog
from scivaliditybench.pipeline.representations import (
    MEMORY_CONDITIONS,
    memory_projection,
    render_memory,
)
from scivaliditybench.pipeline.registry import get_domain_adapter


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-id", default="IL-ML-01")
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()

    catalog = {task.template_id: task for task in load_task_catalog()}
    spec = catalog[args.task_id]
    world = get_domain_adapter(spec.domain).generate(spec, args.seed)
    views = {
        condition: {
            "characters": len(render_memory(world, condition)),
            "nodes": len(memory_projection(world, condition).graph.nodes),
            "relations": len(memory_projection(world, condition).graph.edges),
        }
        for condition in MEMORY_CONDITIONS
    }
    flat = memory_projection(world, "FLAT_SSG")
    typed = memory_projection(world, "SVL")
    print(
        json.dumps(
            {
                "domain": spec.domain.value,
                "flat_and_typed_share_content": flat.graph.to_dict()
                == typed.graph.to_dict(),
                "module": spec.module.value,
                "public_events": len(world.observable_event_ids),
                "task_id": spec.template_id,
                "views": views,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
