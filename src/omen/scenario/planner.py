"""Scenario planning orchestrator for deterministic A/B/C artifacts."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from omen.ingest.synthesizer.services.actor import ensure_strategic_actor_style
from omen.ingest.synthesizer.services.scenario import decompose_scenario_from_situation
from omen.scenario.prior import build_prior_snapshot
from omen.scenario.prior import score_prior_probabilities
from omen.scenario.space import build_planning_query
from omen.scenario.template_loader import load_planning_template


class ScenarioDecompositionValidationError(ValueError):
    """Raised when decomposition payload shape is unusable for local planning."""

    def __init__(self, message: str, *, decomposition_payload: Any) -> None:
        super().__init__(message)
        self.decomposition_payload = decomposition_payload


def _nonempty_text_list(value: Any) -> list[str]:
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _validate_structured_llm_scenario(raw: dict[str, Any], *, scenario_key: str) -> None:
    missing_fields: list[str] = []
    for field_name in ("title", "goal", "target", "objective"):
        if not str(raw.get(field_name) or "").strip():
            missing_fields.append(field_name)

    variables = raw.get("variables")
    if not isinstance(variables, list) or not variables:
        missing_fields.append("variables")

    if not _nonempty_text_list(raw.get("constraints")):
        missing_fields.append("constraints")
    if not _nonempty_text_list(raw.get("tradeoff_pressure")):
        missing_fields.append("tradeoff_pressure")

    if missing_fields:
        raise ValueError(
            "LLM scenario decomposition produced incomplete structured payload "
            f"for slot {scenario_key}: missing {sorted(set(missing_fields))}"
        )


@dataclass(frozen=True)
class ScenarioSlotPolicy:
    key: str
    label: str
    intent: str
    signal_basis: str
    objective: str
    tradeoffs: tuple[str, str]
    resistance: tuple[float, float, float, float]
    constraint_hint: str


def fixed_slot_policies() -> tuple[ScenarioSlotPolicy, ...]:
    return (
        ScenarioSlotPolicy(
            key="A",
            label="Offense",
            intent="Breakthrough action under advantage assumptions",
            signal_basis="Proactive rule-shaping and upside-capture assumptions",
            objective="Create asymmetric advantage through proactive strategic offense.",
            tradeoffs=(
                "Execution speed vs operating stability",
                "Aggressive investment vs short-term margin protection",
            ),
            resistance=(0.8, 0.7, 0.6, 0.7),
            constraint_hint="Prioritize upside signal capture while controlling execution fragility",
        ),
        ScenarioSlotPolicy(
            key="B",
            label="Defense",
            intent="Bottom-line defense under external constraints",
            signal_basis="Constraint-led survival and compliance assumptions",
            objective="Protect core assets and survivability under pressure.",
            tradeoffs=(
                "Predictability vs innovation velocity",
                "Cost control vs option creation",
            ),
            resistance=(0.5, 0.5, 0.5, 0.4),
            constraint_hint="Prioritize continuity under linearly projected market and org constraints",
        ),
        ScenarioSlotPolicy(
            key="C",
            label="Confrontation",
            intent="Direct rivalry action under competitive escalation",
            signal_basis="Rival activation and strategic confrontation assumptions",
            objective="Compete in direct strategic confrontation under fixed rules.",
            tradeoffs=(
                "Emergency containment vs long-term autonomy",
                "Fast de-risking vs strategic upside preservation",
            ),
            resistance=(0.4, 0.4, 0.5, 0.3),
            constraint_hint="Prioritize downside containment and contingency optionality",
        ),
    )


def normalize_llm_scenarios_with_policy(
    llm_scenarios: list[Any],
    *,
    source_hint: str,
    strict_structured: bool = False,
) -> list[dict[str, Any]]:
    policies = fixed_slot_policies()
    by_key: dict[str, dict[str, Any]] = {}
    slot_order = [slot.key for slot in policies]

    for index, item in enumerate(llm_scenarios):
        if isinstance(item, dict):
            key = str(item.get("scenario_key") or "").strip().upper()
            if key in {"A", "B", "C"}:
                by_key[key] = item
                continue
            if index < len(slot_order):
                by_key.setdefault(slot_order[index], item)
            continue

        text = str(item).strip()
        if not text:
            continue
        if index < len(slot_order):
            if strict_structured:
                raise ValueError(
                    "LLM scenario decomposition returned non-object payload "
                    f"for slot {slot_order[index]}: {text!r}"
                )
            raise ValueError("LLM scenario decomposition must return JSON objects for all slots")

    missing = [slot.key for slot in policies if slot.key not in by_key]
    if missing:
        raise ValueError(f"LLM scenario decomposition missing required slots: {missing}")

    normalized: list[dict[str, Any]] = []
    for policy in policies:
        raw = by_key[policy.key]
        if strict_structured:
            _validate_structured_llm_scenario(raw, scenario_key=policy.key)

        constraints = _nonempty_text_list(raw.get("constraints"))
        if not constraints:
            constraints = [policy.constraint_hint]

        tradeoffs = _nonempty_text_list(raw.get("tradeoff_pressure"))
        if not tradeoffs:
            tradeoffs = list(policy.tradeoffs)

        raw_variables = raw.get("variables")
        variables: list[dict[str, Any]] = []
        if isinstance(raw_variables, list):
            for item in raw_variables:
                if isinstance(item, dict):
                    variables.append(item)

        if not variables:
            raise ValueError(f"LLM scenario decomposition slot {policy.key} has empty variables")

        resistance_raw = raw.get("resistance_assumptions") or {}
        if isinstance(resistance_raw, dict):
            resistance = resistance_raw
        else:
            resistance = {}

        default_r = policy.resistance
        normalized.append(
            {
                "scenario_key": policy.key,
                "title": str(raw.get("title") or f"Scenario {policy.key}: {policy.label}").strip(),
                "goal": str(raw.get("goal") or policy.objective).strip(),
                "target": str(raw.get("target") or "strategic-position").strip(),
                "objective": str(raw.get("objective") or policy.objective).strip(),
                "variables": variables,
                "constraints": constraints,
                "tradeoff_pressure": tradeoffs,
                "resistance_assumptions": {
                    "structural_conflict": float(resistance.get("structural_conflict", default_r[0])),
                    "resource_reallocation_drag": float(resistance.get("resource_reallocation_drag", default_r[1])),
                    "cultural_misalignment": float(resistance.get("cultural_misalignment", default_r[2])),
                    "veto_node_intensity": float(resistance.get("veto_node_intensity", default_r[3])),
                    "aggregate_resistance": float(
                        resistance.get("aggregate_resistance", round(sum(default_r) / 4.0, 3))
                    ),
                    "assumption_rationale": [
                        *[
                            str(x).strip()
                            for x in (resistance.get("assumption_rationale") or [])
                            if str(x).strip()
                        ],
                        source_hint,
                        f"intent: {policy.intent}",
                    ],
                },
                "modeling_notes": [
                    *[
                        str(x).strip()
                        for x in (raw.get("modeling_notes") or [])
                        if str(x).strip()
                    ],
                    "Scenario normalized under deterministic A/B/C intent policy",
                    f"signal_basis: {policy.signal_basis}",
                ],
            }
        )
    return normalized


def _build_scenario_ontology_from_situation_artifact(
    *,
    situation_artifact: dict[str, Any],
    llm_decomposition: dict[str, Any],
    pack_id: str,
    pack_version: str,
) -> dict[str, Any]:
    scenarios = normalize_llm_scenarios_with_policy(
        list(llm_decomposition.get("scenarios") or []),
        source_hint=f"Derived from situation artifact: {situation_artifact.get('id', 'unknown')}",
    )
    source_meta = dict(llm_decomposition.get("source_meta") or {})
    source_meta.setdefault(
        "source_path",
        str((situation_artifact.get("source_meta") or {}).get("source_path") or ""),
    )
    source_meta.setdefault("generated_at", datetime.now().isoformat())
    source_meta["generated_from"] = "situation_artifact"

    return {
        "pack_id": pack_id,
        "pack_version": pack_version,
        "derived_from_situation_id": str(situation_artifact.get("id") or "unknown"),
        "ontology_version": str(llm_decomposition.get("ontology_version") or "scenario_ontology_v1"),
        "planning_query_ref": str(llm_decomposition.get("planning_query_ref") or "traces/planning_query.json"),
        "prior_snapshot_ref": str(llm_decomposition.get("prior_snapshot_ref") or "traces/prior_snapshot.json"),
        "scenarios": scenarios,
        "decomposition_quality": llm_decomposition.get("decomposition_quality") or {},
        "source_meta": source_meta,
    }


def _write_auxiliary_json(path: str | Path, payload: dict[str, Any]) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return output_path


def _validate_decomposition_json_or_raise(decomposition: dict[str, Any]) -> None:
    scenarios = decomposition.get("scenarios")
    if not isinstance(scenarios, list):
        raise ScenarioDecompositionValidationError(
            "Scenario decomposition validation failed: `scenarios` must be a JSON array. "
            "No local artifacts were written.",
            decomposition_payload=decomposition,
        )

    non_object_items = [idx for idx, item in enumerate(scenarios, start=1) if not isinstance(item, dict)]
    if non_object_items:
        raise ScenarioDecompositionValidationError(
            "Scenario decomposition validation failed: all `scenarios` entries must be JSON objects "
            f"(invalid positions: {non_object_items}). No local artifacts were written.",
            decomposition_payload=decomposition,
        )


def plan_scenarios_from_situation(
    *,
    situation_artifact: dict[str, Any],
    pack_id: str,
    pack_version: str,
    actor_ref: str,
    config_path: str,
    traces_dir: str | Path,
) -> dict[str, Any]:
    actor_enhancement_trace = ensure_strategic_actor_style(
        actor_ref=actor_ref,
        current_case_id_to_exclude=str(situation_artifact.get("id") or "unknown_case"),
        config_path=config_path,
    )

    template = load_planning_template()
    planning_query = build_planning_query(
        situation_artifact=situation_artifact,
        actor_ref=actor_ref,
        template=template,
    )

    decomposition = decompose_scenario_from_situation(
        situation_artifact=situation_artifact,
        pack_id=pack_id,
        pack_version=pack_version,
        config_path=config_path,
        planning_template=template.model_dump(),
        planning_query=planning_query,
    )

    _validate_decomposition_json_or_raise(decomposition)

    traces_path = Path(traces_dir)
    traces_path.mkdir(parents=True, exist_ok=True)

    planning_query_path = traces_path / "planning_query.json"
    _write_auxiliary_json(planning_query_path, planning_query)

    ontology = _build_scenario_ontology_from_situation_artifact(
        situation_artifact=situation_artifact,
        llm_decomposition=decomposition,
        pack_id=pack_id,
        pack_version=pack_version,
    )

    raw_priors, prior_scoring_trace = score_prior_probabilities(
        actor_ref=actor_ref,
        scenario_ontology=ontology,
        planning_query=planning_query,
        config_path=config_path,
    )

    prior_snapshot = build_prior_snapshot(
        pack_id=pack_id,
        pack_version=pack_version,
        situation_id=str(situation_artifact.get("id") or "unknown"),
        actor_ref=actor_ref,
        raw_prior_scores=raw_priors,
        planning_query_ref=str(planning_query_path),
    )
    prior_snapshot_path = traces_path / "prior_snapshot.json"
    _write_auxiliary_json(prior_snapshot_path, prior_snapshot)

    ontology["planning_query_ref"] = str(planning_query_path)
    ontology["prior_snapshot_ref"] = str(prior_snapshot_path)
    ontology["source_meta"] = {
        **(ontology.get("source_meta") or {}),
        "generated_at": datetime.now().isoformat(),
        "planner": "planner_v1",
    }
    ontology["_planner_trace"] = {
        "actor_style_enhancement": actor_enhancement_trace,
        "prior_scoring": prior_scoring_trace,
    }
    return ontology
