"""Answer-neutral reader interface used by the benchmark."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence

from scivaliditybench.core.specs import StateModule
from scivaliditybench.pipeline.domain import GeneratedWorld
from scivaliditybench.pipeline.representations import render_memory


SYSTEM_MESSAGE = (
    "Execute the decision_function supplied in the user JSON. For a mapping, "
    "read the specified public input and return its mapped choice. For an "
    "operation, calculate the boolean result first, serialize that result as "
    "the string true or false, and then look it up in result_to_choice. Never "
    "invert or reinterpret the selected branch. Verify required relations and "
    "do not invent missing state. Return exactly one JSON object with exactly "
    'one field and no markdown or explanation: {"choice":"<allowed choice>"}.'
)

_DEFAULT_CHOICES: dict[StateModule, tuple[str, ...]] = {
    StateModule.INFERENTIAL: ("confirm", "exploratory"),
    StateModule.DISCLOSURE: ("confirmatory", "exploratory"),
    StateModule.CONSTRUCT: ("pool", "separate"),
    StateModule.ABSENCE: ("run", "rerun", "record_zero", "censored_model"),
    StateModule.RELEVANCE: ("project_a", "project_b"),
}


def decision_choices(world: GeneratedWorld) -> tuple[str, ...]:
    """Return the exact legal-choice contract shared by prompting and scoring."""

    raw = world.critical_state.get(
        "allowed_choices",
        _DEFAULT_CHOICES[world.spec.module],
    )
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ValueError("allowed_choices must be a sequence of strings")
    choices = tuple(str(item) for item in raw)
    normalized = [item.strip().lower() for item in choices]
    if (
        not choices
        or any(not item for item in normalized)
        or len(normalized) != len(set(normalized))
    ):
        raise ValueError("allowed_choices must be non-empty and unique")
    return choices


def _current_request(world: GeneratedWorld) -> dict[str, object]:
    decisions = [
        event
        for event in world.events
        if event.event_type.value == "DECIDE" and event.visibility.value != "oracle"
    ]
    if not decisions:
        return {}
    event = decisions[-1]
    return {"objects": list(event.objects), "request": dict(event.payload)}


def _decision_function(world: GeneratedWorld) -> dict[str, object]:
    module = world.spec.module
    if module is StateModule.INFERENTIAL:
        primitive = str(world.critical_state.get("decision_primitive", "categorical"))
        if primitive == "source_independence":
            return {
                "left_input_path": "evidence_registry.attributes.unique_sources",
                "operation": "greater_than_or_equal",
                "required_relations": ["REGISTERED_WITH", "ASSESSED_UNDER"],
                "result_to_choice": {"false": "exploratory", "true": "confirm"},
                "right_input_path": "plan.attributes.required_independent_sources",
            }
        if primitive == "scope_membership":
            return {
                "item_input_path": "current_request.request.requested_scope",
                "list_input_path": "plan.attributes.allowed_scopes",
                "operation": "item_in_list",
                "required_relations": ["AUTHORIZED_BY"],
                "result_to_choice": {"false": "exploratory", "true": "confirm"},
            }
        required = ["SELECTED_FROM", "STOPPED_AFTER"]
        if primitive == "categorical":
            confirm_code = str(
                world.critical_state.get("confirm_authorization_code", "K")
            )
            exploratory_code = str(
                world.critical_state.get("exploratory_authorization_code", "M")
            )
            return {
                "input_path": "plan.attributes.authorization_code",
                "mapping": {
                    confirm_code: "confirm",
                    exploratory_code: "exploratory",
                },
                "missing_or_unlinked_choice": "exploratory",
                "primitive": "categorical",
                "required_relations": required,
            }
        if primitive == "integer_limit":
            return {
                "left_input_path": "selected_observation.attributes.observed_exceedances",
                "operation": "less_than_or_equal",
                "required_relations": required,
                "result_to_choice": {"false": "exploratory", "true": "confirm"},
                "right_input_path": "plan.attributes.max_exceedances",
            }
        raise ValueError(f"unsupported inferential primitive: {primitive}")

    if module is StateModule.DISCLOSURE:
        intact = str(world.critical_state.get("intact_choice", "confirmatory"))
        compromised = str(
            world.critical_state.get("compromised_choice", "exploratory")
        )
        if bool(world.critical_state.get("direct_state_choice")):
            return {
                "input_path": "blinding_state.attributes.value",
                "missing_or_unlinked_choice": compromised,
                "operation": "return_value",
                "required_relations": ["DERIVED_AS", "SEALED_UNTIL"],
            }
        return {
            "input_path": "blinding_state.attributes.value",
            "mapping": {"COMPROMISED": compromised, "INTACT": intact},
            "missing_or_unlinked_choice": compromised,
            "required_relations": ["DERIVED_AS", "SEALED_UNTIL"],
        }

    if module is StateModule.CONSTRUCT:
        if world.critical_state.get("decision_primitive") == "construct_harmonization":
            return {
                "input_path": "harmonization_state.attributes.value",
                "mapping": {
                    "CONVERTIBLE": "transform_then_pool",
                    "IDENTICAL": "pool_without_transform",
                    "INCOMMENSURATE": "keep_separate",
                },
                "missing_or_unlinked_choice": "keep_separate",
                "required_relations": ["HARMONIZES_WITH", "APPLIES_TO"],
            }
        return {
            "input_path": "COMPARABLE_WITH.attributes.value",
            "mapping": {"false": "separate", "true": "pool"},
            "missing_or_unlinked_choice": "separate",
            "required_relations": ["COMPARABLE_WITH"],
        }

    if module is StateModule.ABSENCE:
        choices = decision_choices(world)
        if len(choices) != 4:
            raise ValueError("absence tasks require four choices")
        evidence_chain = (
            world.critical_state.get("decision_primitive") == "absence_evidence_chain"
        )
        return {
            "input_path": (
                "absence_state.attributes.value"
                if evidence_chain
                else "ABSENT_BECAUSE.attributes.mechanism"
            ),
            "mapping": {
                "BELOW_DETECTION": choices[3],
                "FAILED": choices[1],
                "NOT_RUN": choices[0],
                "TRUE_ZERO": choices[2],
            },
            "missing_or_unlinked_choice": choices[0],
            "required_relations": ["DERIVED_AS" if evidence_chain else "ABSENT_BECAUSE"],
        }

    if module is StateModule.RELEVANCE:
        if world.critical_state.get("decision_primitive") == "prospective_net_value":
            return {
                "left_expression": (
                    "current_request.request.future_a - "
                    "current_request.request.prospective_cost_a"
                ),
                "operation": "greater_than",
                "result_to_choice": {"false": "project_b", "true": "project_a"},
                "right_expression": (
                    "current_request.request.future_b - "
                    "current_request.request.prospective_cost_b"
                ),
                "ignore_memory_fields": ["historical_cost", "sunk_amount"],
                "invariance": "changing only ignored history must not change choice",
            }
        return {
            "comparison": (
                "current_request.project_a_future_value > "
                "current_request.project_b_future_value"
            ),
            "false_choice": "project_b",
            "ignore_memory_fields": ["historical_cost", "sunk_amount"],
            "invariance": "changing only ignored history must not change choice",
            "true_choice": "project_a",
        }
    raise ValueError(f"unsupported module: {module.value}")


def build_reader_messages(
    world: GeneratedWorld,
    condition: str,
    intervention: str = "original",
) -> list[dict[str, str]]:
    """Build the final reader messages without exposing oracle-only fields."""

    current_request = _current_request(world)
    if (
        world.spec.module is StateModule.INFERENTIAL
        and str(world.critical_state.get("decision_primitive", "categorical"))
        == "categorical"
    ):
        current_request = {
            **current_request,
            "request": {
                key: value
                for key, value in dict(current_request.get("request", {})).items()
                if key != "observed_exceedances"
            },
        }
    payload = {
        "allowed_choices": list(decision_choices(world)),
        "current_request": current_request,
        "decision_function": _decision_function(world),
        "domain": world.spec.domain.value,
        "domain_context": world.surface,
        "memory_interface": "long_term_memory",
        "memory_readout": render_memory(world, condition, intervention),
        "phenomenon": world.spec.generator["phenomenon"],
        "task_id": world.spec.template_id,
    }
    return [
        {"role": "system", "content": SYSTEM_MESSAGE},
        {
            "role": "user",
            "content": json.dumps(
                payload,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ),
        },
    ]


def parse_reader_choice(
    response: str,
    allowed_choices: Sequence[str],
) -> str:
    """Validate the one-field JSON output contract and return its choice."""

    value = json.loads(response)
    if not isinstance(value, Mapping) or set(value) != {"choice"}:
        raise ValueError('reader output must contain exactly one field: "choice"')
    choice = str(value["choice"])
    if choice not in allowed_choices:
        raise ValueError("reader choice is outside the registered action space")
    return choice


__all__ = [
    "SYSTEM_MESSAGE",
    "build_reader_messages",
    "decision_choices",
    "parse_reader_choice",
]
