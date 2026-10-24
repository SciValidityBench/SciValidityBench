"""Load the final 64-TaskSpec SciValidityBench catalog."""

from __future__ import annotations

from functools import lru_cache
from importlib.resources import files
from pathlib import Path

import yaml

from scivaliditybench.core.specs import Domain, StateModule, TaskSpec


_DEFAULT_CORRUPTIONS = {
    StateModule.INFERENTIAL: ("OMIT", "UNLINK", "DUPLICATE"),
    StateModule.DISCLOSURE: ("OMIT", "RELABEL"),
    StateModule.CONSTRUCT: ("UNLINK", "MERGE", "RELABEL"),
    StateModule.ABSENCE: ("OMIT", "RELABEL"),
    StateModule.RELEVANCE: ("INJECT", "UNLINK"),
}


def _catalog_text(path: str | Path | None) -> str:
    if path is not None:
        return Path(path).read_text(encoding="utf-8")
    return (
        files("scivaliditybench")
        .joinpath("task_catalog.yaml")
        .read_text(encoding="utf-8")
    )


@lru_cache(maxsize=2)
def load_task_catalog(path: str | Path | None = None) -> list[TaskSpec]:
    """Return the ordered final catalog of 64 active TaskSpecs."""

    raw = yaml.safe_load(_catalog_text(path))
    if raw.get("schema_version") != "0.1.0":
        raise ValueError("unsupported task catalog schema")
    if int(raw.get("expected_active_templates", 0)) != 64:
        raise ValueError("catalog must declare 64 active templates")

    specs: list[TaskSpec] = []
    for entry in raw.get("tasks", []):
        if str(entry.get("catalog_status", "active")) != "active":
            raise ValueError("the release catalog may contain only active templates")
        module = StateModule(entry["module"])
        generator: dict[str, object] = {
            "phenomenon": entry["phenomenon"],
            "null_probability": 0.5,
            "difficulty": "calibrated",
            "catalog_status": "active",
        }
        if entry.get("design_version"):
            generator["design_version"] = entry["design_version"]
        if entry.get("executable_workflow"):
            generator["executable_workflow"] = entry["executable_workflow"]
        specs.append(
            TaskSpec(
                template_id=entry["template_id"],
                module=module,
                domain=Domain(entry["domain"]),
                version=str(entry.get("version", "1.0.0")),
                generator=generator,
                action_space=("inspect", "experiment", "record", "decide"),
                budget={"experiments": 6, "tool_calls": 12},
                episodes=3,
                decision_schema={
                    "type": "scientific_action",
                    "required": ["choice"],
                },
                validator=module.value,
                required_corruptions=_DEFAULT_CORRUPTIONS[module],
                calibration={"target_gap": 0.15, "ceiling": 0.90, "floor": 0.10},
                split_policy={
                    "strategy": "seed_ranges",
                    "development": [0, 999],
                    "hidden": [10000, 19999],
                },
            )
        )

    if len(specs) != 64 or len({spec.template_id for spec in specs}) != 64:
        raise ValueError("catalog must contain 64 unique active templates")
    return specs


__all__ = ["load_task_catalog"]
