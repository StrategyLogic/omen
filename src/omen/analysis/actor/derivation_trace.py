"""Actor derivation trace helpers."""

from __future__ import annotations

from typing import Any


REASONING_ORDER: tuple[str, ...] = (
    "seed",
    "constraint_activation",
    "target_or_objective",
    "gap",
    "required_or_warning_or_blocking",
)


def build_hierarchical_step_id(major: int, minor: int) -> str:
    if major < 1 or minor < 1:
        raise ValueError("step id major/minor must be >= 1")
    return f"step_{major}.{minor}"


def is_hierarchical_step_id(step_id: str) -> bool:
    return bool(str(step_id or "").strip())


def validate_reason_chain_step_ids(steps: list[dict[str, Any]]) -> bool:
    if not isinstance(steps, list) or not steps:
        return False
    return all(is_hierarchical_step_id(str(item.get("step_id") or "")) for item in steps)


def reasoning_order_is_valid(step_types: list[str]) -> bool:
    order_index = {name: idx for idx, name in enumerate(REASONING_ORDER)}
    last = -1
    for raw in step_types:
        name = str(raw or "").strip()
        if name not in order_index:
            continue
        current = order_index[name]
        if current < last:
            return False
        last = current
    return True


def blocking_has_activation_links(blocking_item: dict[str, Any]) -> bool:
    if not isinstance(blocking_item, dict):
        return False
    activation_refs = [str(item).strip() for item in (blocking_item.get("activation_step_ids") or []) if str(item).strip()]
    reason_refs = [str(item).strip() for item in (blocking_item.get("reason_step_ids") or []) if str(item).strip()]
    return bool(activation_refs and reason_refs)


def build_linked_evidence_refs(reason_chain: dict[str, Any]) -> list[dict[str, Any]]:
    conclusions = dict(reason_chain.get("conclusions") or {})
    refs: list[dict[str, Any]] = []
    for bucket in ("required", "warning", "blocking"):
        for index, item in enumerate(list(conclusions.get(bucket) or []), start=1):
            if not isinstance(item, dict):
                continue
            reason_ids = [str(x).strip() for x in (item.get("reason_step_ids") or []) if str(x).strip()]
            activation_ids = [str(x).strip() for x in (item.get("activation_step_ids") or []) if str(x).strip()]
            refs.append(
                {
                    "evidence_id": f"{bucket}_{index}",
                    "bucket": bucket,
                    "summary": str(item.get("text") or "").strip(),
                    "reason_step_ids": reason_ids,
                    "activation_step_ids": activation_ids,
                }
            )
    return refs


def _pattern_map_dimension(variable_name: str) -> tuple[str, str]:
    text = str(variable_name or "").strip().lower()
    if text.startswith("standard_") or "standard" in text:
        return "standardization_velocity", "pattern_match: standard_*"
    if text.startswith("integration_") or "integration" in text:
        return "standardization_velocity", "pattern_match: integration_*"
    if text.startswith("adoption_") or "adoption" in text:
        return "market_adoption_velocity", "pattern_match: adoption_*"
    if text.startswith("cost_") or "cost" in text:
        return "cost_efficiency", "pattern_match: cost_*"
    return "unmapped", "pattern_match: none"


def _describe_score(score: float) -> str:
    if score >= 0.75:
        return "high"
    if score <= 0.4:
        return "low"
    return "medium"


def build_scenario_reason_chain(
    *,
    run_id: str,
    scenario_key: str,
    scenario_ontology: dict[str, Any],
    scenario_result: dict[str, Any],
) -> dict[str, Any]:
    variables = list(scenario_ontology.get("variables") or [])
    selected_dimensions = [
        str(item).strip()
        for item in ((scenario_result.get("selected_dimensions") or {}).get("selected_dimension_keys") or [])
        if str(item).strip()
    ]
    capability_scores = dict((scenario_result.get("capability_dilemma_fit") or {}).get("capability_scores") or {})

    dimension_mapping: list[dict[str, Any]] = []
    for variable in variables:
        if isinstance(variable, dict):
            variable_name = str(variable.get("name") or variable.get("variable") or "").strip()
        else:
            variable_name = str(variable).strip()
        if not variable_name:
            continue

        mapped_to, reason = _pattern_map_dimension(variable_name)
        if mapped_to == "unmapped" and selected_dimensions:
            mapped_to = selected_dimensions[0]
            reason = "fallback: selected_dimension_top_1"

        dimension_mapping.append(
            {
                "variable": variable_name,
                "mapped_to": mapped_to,
                "reason": reason,
            }
        )

    value_calculation: list[dict[str, Any]] = []
    for dim in selected_dimensions:
        score = float(capability_scores.get(dim, 0.5))
        value_calculation.append(
            {
                "dimension": dim,
                "method": "inferred_from_variable",
                "raw_description": _describe_score(score),
                "value": round(score, 3),
                "confidence": 0.6,
            }
        )

    strategic_freedom = dict(scenario_result.get("strategic_freedom") or {})
    required_items = [str(item).strip() for item in (strategic_freedom.get("required") or []) if str(item).strip()]
    warning_items = [str(item).strip() for item in (strategic_freedom.get("warning") or []) if str(item).strip()]
    blocking_items = [str(item).strip() for item in (strategic_freedom.get("blocking") or []) if str(item).strip()]
    objective = str(scenario_ontology.get("objective") or "").strip()
    constraints = [str(item).strip() for item in (scenario_ontology.get("constraints") or []) if str(item).strip()]

    steps = [
        {
            "step_id": build_hierarchical_step_id(1, 1),
            "step_type": "seed",
            "input_refs": [f"scenario::{scenario_key}"],
            "summary": f"Seed from deterministic scenario slot {scenario_key}",
        },
        {
            "step_id": build_hierarchical_step_id(2, 1),
            "step_type": "constraint_activation",
            "input_refs": [f"constraint::{item}" for item in constraints[:2]] or [f"scenario::{scenario_key}::constraints"],
            "summary": "Activate binding constraints before deriving executable path",
        },
        {
            "step_id": build_hierarchical_step_id(3, 1),
            "step_type": "target_or_objective",
            "input_refs": [f"objective::{objective}"] if objective else [f"scenario::{scenario_key}::objective"],
            "summary": f"Lock objective alignment: {objective or 'objective_not_provided'}",
        },
        {
            "step_id": build_hierarchical_step_id(4, 1),
            "step_type": "gap",
            "input_refs": ["strategic_freedom::warning", "strategic_freedom::blocking"],
            "summary": "Identify execution gap under current resistance baseline",
        },
        {
            "step_id": build_hierarchical_step_id(5, 1),
            "step_type": "required_or_warning_or_blocking",
            "input_refs": ["strategic_freedom::required", "strategic_freedom::warning", "strategic_freedom::blocking"],
            "summary": "Project required, warning and blocking conclusions",
        },
    ]

    step_types = [str(item.get("step_type") or "") for item in steps]
    if not reasoning_order_is_valid(step_types):
        raise ValueError(f"invalid reason chain step order for scenario {scenario_key}")
    if not validate_reason_chain_step_ids(steps):
        raise ValueError(f"invalid step_id in reason chain for scenario {scenario_key}")

    return {
        "run_id": run_id,
        "scenario_key": scenario_key,
        "reason_chain": {
            "steps": steps,
            "intermediate": {
                "dimension_mapping": dimension_mapping,
                "value_calculation": value_calculation,
            },
            "conclusions": {
                "required": [
                    {
                        "text": text,
                        "reason_step_ids": ["step_5.1"],
                    }
                    for text in required_items
                ],
                "warning": [
                    {
                        "text": text,
                        "reason_step_ids": ["step_5.1"],
                    }
                    for text in warning_items
                ],
                "blocking": [
                    {
                        "text": text,
                        "activation_step_ids": [build_hierarchical_step_id(2, 1)],
                        "reason_step_ids": [build_hierarchical_step_id(5, 1)],
                    }
                    for text in blocking_items
                ],
            },
        },
    }


def build_reason_chain_artifact(
    *,
    run_id: str,
    scenario_pack_ref: str,
    scenario_chains: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "artifact_type": "reason_chain",
        "version": "reason_chain_v1",
        "run_id": run_id,
        "scenario_pack_ref": scenario_pack_ref,
        "scenario_chains": scenario_chains,
    }


def build_reason_chain_view_model_artifact(
    *,
    run_id: str,
    scenario_pack_ref: str,
    scenario_chains: list[dict[str, Any]],
) -> dict[str, Any]:
    graph_nodes: list[dict[str, Any]] = []
    graph_edges: list[dict[str, Any]] = []
    for row in scenario_chains:
        scenario_key = str(row.get("scenario_key") or "")
        reason_chain = dict(row.get("reason_chain") or {})
        steps = list(reason_chain.get("steps") or [])
        for step in steps:
            step_id = str(step.get("step_id") or "").strip()
            node_id = f"{scenario_key}:{step_id}"
            graph_nodes.append(
                {
                    "id": node_id,
                    "scenario_key": scenario_key,
                    "node_type": "reason_step",
                    "step_id": step_id,
                    "step_type": str(step.get("step_type") or ""),
                    "label": str(step.get("summary") or ""),
                }
            )

        conclusions = dict(reason_chain.get("conclusions") or {})
        for bucket in ("required", "warning", "blocking"):
            for index, item in enumerate(list(conclusions.get(bucket) or []), start=1):
                if not isinstance(item, dict):
                    continue
                claim_id = f"{scenario_key}:claim:{bucket}:{index}"
                graph_nodes.append(
                    {
                        "id": claim_id,
                        "scenario_key": scenario_key,
                        "node_type": "claim",
                        "bucket": bucket,
                        "label": str(item.get("text") or ""),
                    }
                )
                for reason_step_id in list(item.get("reason_step_ids") or []):
                    rid = str(reason_step_id).strip()
                    if rid:
                        graph_edges.append(
                            {
                                "from": f"{scenario_key}:{rid}",
                                "to": claim_id,
                                "edge_type": "supports",
                            }
                        )
                for activation_step_id in list(item.get("activation_step_ids") or []):
                    aid = str(activation_step_id).strip()
                    if aid:
                        graph_edges.append(
                            {
                                "from": f"{scenario_key}:{aid}",
                                "to": claim_id,
                                "edge_type": "activates",
                            }
                        )

    return {
        "artifact_type": "reason_chain_view_model",
        "version": "reason_chain_view_model_v1",
        "run_id": run_id,
        "scenario_pack_ref": scenario_pack_ref,
        "graph": {
            "nodes": graph_nodes,
            "edges": graph_edges,
        },
    }


def build_actor_derivation_trace(
    *,
    scenario_key: str,
    scenario_ontology: dict[str, Any],
    actor_derivation: dict[str, Any],
    selected_dimensions: dict[str, Any],
    strategic_conditions: dict[str, Any],
    missing_evidence_reasons: list[str],
) -> dict[str, Any]:
    objective = str(scenario_ontology.get("objective") or "").strip()
    constraints = [str(item).strip() for item in (scenario_ontology.get("constraints") or []) if str(item).strip()]
    selected = [str(item).strip() for item in (selected_dimensions.get("selected_dimension_keys") or []) if str(item).strip()]
    required = [str(item).strip() for item in (strategic_conditions.get("required") or []) if str(item).strip()]
    derivation_keys = sorted(str(key) for key in actor_derivation.keys()) if isinstance(actor_derivation, dict) else []

    return {
        "scenario_key": scenario_key,
        "ontology_refs": [
            "objective",
            "constraints",
            "tradeoff_pressure",
            "resistance_assumptions",
        ],
        "selected_dimensions": selected,
        "actor_derivation_refs": [f"actor_derivation::{scenario_key}"],
        "derivation_steps": [
            f"Scene objective aligned: {objective or 'unknown objective'}",
            f"Scene constraints interpreted: {', '.join(constraints[:2]) if constraints else 'none'}",
            f"Actor derivation selected dimensions: {', '.join(selected) if selected else 'none'}",
            f"Actor derivation fields observed: {', '.join(derivation_keys[:3]) if derivation_keys else 'none'}",
            f"Strategic condition projection: {', '.join(required[:2]) if required else 'none'}",
        ],
        "missing_evidence_reasons": list(missing_evidence_reasons),
    }


def build_actor_derivation_artifact(
    *,
    run_id: str,
    actor_profile_ref: str,
    scenario_pack_ref: str,
    scenario_derivations: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "artifact_type": "actor_derivation",
        "version": "actor_derivation_v1",
        "run_id": run_id,
        "actor_profile_ref": actor_profile_ref,
        "scenario_pack_ref": scenario_pack_ref,
        "scenario_derivations": scenario_derivations,
    }
