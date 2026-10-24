from __future__ import annotations

import json

import pytest

from scivaliditybench.pipeline.catalog import load_task_catalog
from scivaliditybench.pipeline.representations import (
    MEMORY_CONDITIONS,
    memory_projection,
    render_memory,
)
from scivaliditybench.pipeline.reader import (
    build_reader_messages,
    decision_choices,
    parse_reader_choice,
)
from scivaliditybench.pipeline.registry import get_domain_adapter


def _world():
    spec = next(task for task in load_task_catalog() if task.template_id == "IL-ML-01")
    return get_domain_adapter(spec.domain).generate(spec, seed=7)


def test_five_views_are_deterministic_and_oracle_free() -> None:
    world = _world()
    rendered = {
        condition: render_memory(world, condition)
        for condition in MEMORY_CONDITIONS
    }
    assert len(set(rendered.values())) == len(MEMORY_CONDITIONS)
    assert all("oracle_only" not in value for value in rendered.values())
    assert all("hidden_truth" not in value for value in rendered.values())


def test_flat_and_typed_views_share_content_not_serialization() -> None:
    world = _world()
    flat = memory_projection(world, "FLAT_SSG")
    typed = memory_projection(world, "SVL")
    assert flat.graph.to_dict() == typed.graph.to_dict()
    assert render_memory(world, "FLAT_SSG") != render_memory(world, "SVL")


def test_reader_contract_is_answer_neutral_and_strict() -> None:
    world = _world()
    messages = build_reader_messages(world, "SVL")
    payload = json.loads(messages[1]["content"])
    assert "oracle_decision" not in payload
    assert "hidden_truth" not in messages[1]["content"]
    response = json.dumps({"choice": world.oracle_decision})
    assert parse_reader_choice(response, decision_choices(world)) == world.oracle_decision
    with pytest.raises(ValueError):
        parse_reader_choice(
            json.dumps({"choice": world.oracle_decision, "reason": "extra"}),
            decision_choices(world),
        )
