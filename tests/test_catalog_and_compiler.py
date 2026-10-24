from __future__ import annotations

from scivaliditybench.core.specs import Domain, StateModule
from scivaliditybench.pipeline.catalog import load_task_catalog
from scivaliditybench.pipeline.registry import get_domain_adapter


def test_final_catalog_has_64_active_tasks_five_modules_and_six_domains() -> None:
    catalog = load_task_catalog()
    assert len(catalog) == 64
    assert len({task.template_id for task in catalog}) == 64
    assert {task.module for task in catalog} == set(StateModule)
    assert {task.domain for task in catalog} == set(Domain)
    assert all(task.generator["catalog_status"] == "active" for task in catalog)


def test_every_task_generates_deterministically_without_oracle_leakage() -> None:
    for spec in load_task_catalog():
        adapter = get_domain_adapter(spec.domain)
        left = adapter.generate(spec, seed=7)
        right = adapter.generate(spec, seed=7)
        assert left.event_log_hash == right.event_log_hash
        assert left.visible_graph.graph_hash == right.visible_graph.graph_hash
        assert all(
            not node.attributes.get("oracle_only", False)
            for node in left.visible_graph.nodes.values()
        )

