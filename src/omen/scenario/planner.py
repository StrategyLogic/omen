"""Scenario planning orchestrator for deterministic A/B/C artifacts."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from omen.ingest.synthesizer.clients import invoke_text_prompt, render_prompt_template
from omen.ingest.synthesizer.prompts import build_json_retry_prompt
from omen.ingest.synthesizer.prompts.registry import get_prompt_template
from omen.ingest.synthesizer.services.scenario import decompose_scenario_from_situation
from omen.scenario.prior import build_prior_snapshot
from omen.scenario.space import build_planning_query
from omen.scenario.template_loader import load_planning_template


class ScenarioDecompositionValidationError(ValueError):
    """Raised when decomposition payload shape is unusable for local planning."""

    def __init__(self, message: str, *, decomposition_payload: Any) -> None:
        super().__init__(message)
        self.decomposition_payload = decomposition_payload


def _render_base_prompt(template_key: str, values: dict[str, object]) -> str:
    return render_prompt_template(get_prompt_template(template_key, tier="base"), values)


def _extract_json_object(text: str) -> dict[str, Any]:
    decoder = json.JSONDecoder()
    start = text.find("{")
    if start == -1:
        raise ValueError("LLM response does not contain JSON object")
    payload, _ = decoder.raw_decode(text[start:])
    if not isinstance(payload, dict):
        raise ValueError("LLM response payload is not an object")
    return payload


def _invoke_json(prompt: str, *, config_path: str, stage: str) -> dict[str, Any]:
    content = invoke_text_prompt(config_path=config_path, user_prompt=prompt)
    try:
        return _extract_json_object(content)
    except Exception:
        retry_prompt = build_json_retry_prompt(prompt)
        retry_content = invoke_text_prompt(config_path=config_path, user_prompt=retry_prompt)
        return _extract_json_object(retry_content)


def _resolve_actor_ontology_path(actor_ref: str) -> Path | None:
    candidate = Path(str(actor_ref).strip())
    if candidate.exists() and candidate.suffix.lower() == ".json":
        return candidate
    return None


def _find_strategic_actor(payload: dict[str, Any]) -> dict[str, Any] | None:
    actors = payload.get("actors") or []
    if not isinstance(actors, list):
        return None
    for actor in actors:
        if not isinstance(actor, dict):
            continue
        if str(actor.get("type") or "").strip() == "StrategicActor":
            return actor
    return None


def _is_strategic_actor_admissible(payload: dict[str, Any]) -> bool:
    strategic_actor = _find_strategic_actor(payload)
    if not isinstance(strategic_actor, dict):
        return False

    profile = strategic_actor.get("profile") or {}
    if not isinstance(profile, dict):
        return False
    style = profile.get("strategic_style") or {}
    if not isinstance(style, dict):
        return False

    filled = 0
    if str(style.get("decision_style") or "").strip():
        filled += 1
    if str(style.get("value_proposition") or "").strip():
        filled += 1
    if isinstance(style.get("decision_preferences"), list) and any(str(x).strip() for x in style["decision_preferences"]):
        filled += 1
    if isinstance(style.get("non_negotiables"), list) and any(str(x).strip() for x in style["non_negotiables"]):
        filled += 1

    return filled >= 2


def _enhance_actor_ontology_style(
    *,
    actor_payload: dict[str, Any],
    actor_ref: str,
    strategic_actor_name: str,
    strategic_actor_role: str,
    current_case_id_to_exclude: str,
    config_path: str,
) -> dict[str, Any]:
    prompt = _render_base_prompt(
        "scenario_enhance_prompt",
        {
            "actor_ref": actor_ref,
            "strategic_actor_name": strategic_actor_name,
            "strategic_actor_role": strategic_actor_role,
            "current_case_id_to_exclude": current_case_id_to_exclude,
            "actor_ontology_json": json.dumps(actor_payload, ensure_ascii=False),
        },
    )
    return _invoke_json(prompt, config_path=config_path, stage="scenario_enhance_prompt")


def _extract_strategic_actor_identity(actor_payload: dict[str, Any]) -> tuple[str, str]:
    strategic_actor = _find_strategic_actor(actor_payload)
    if not isinstance(strategic_actor, dict):
        return ("unknown_strategic_actor", "")
    return (
        str(strategic_actor.get("name") or "unknown_strategic_actor").strip(),
        str(strategic_actor.get("role") or "").strip(),
    )


def _apply_enhanced_style(actor_payload: dict[str, Any], enhanced: dict[str, Any]) -> bool:
    strategic_actor = _find_strategic_actor(actor_payload)
    if not isinstance(strategic_actor, dict):
        return False

    profile = strategic_actor.setdefault("profile", {})
    if not isinstance(profile, dict):
        return False

    existing = profile.get("strategic_style")
    if not isinstance(existing, dict):
        existing = {}
        profile["strategic_style"] = existing

    candidate = enhanced.get("strategic_style") if isinstance(enhanced.get("strategic_style"), dict) else enhanced
    if not isinstance(candidate, dict):
        return False

    changed = False
    for field in ("decision_style", "value_proposition"):
        value = str(candidate.get(field) or "").strip()
        if value and str(existing.get(field) or "").strip() != value:
            existing[field] = value
            changed = True

    for field in ("decision_preferences", "non_negotiables"):
        raw = candidate.get(field)
        if isinstance(raw, list):
            normalized = [str(item).strip() for item in raw if str(item).strip()]
            if normalized and normalized != existing.get(field):
                existing[field] = normalized
                changed = True

    return changed


def _ensure_strategic_actor_admissible(
    *,
    actor_ref: str,
    situation_artifact: dict[str, Any],
    config_path: str,
) -> str:
    actor_path = _resolve_actor_ontology_path(actor_ref)
    if actor_path is None:
        return actor_ref

    try:
        payload = json.loads(actor_path.read_text(encoding="utf-8"))
    except Exception:
        return actor_ref

    if _is_strategic_actor_admissible(payload):
        return actor_ref

    strategic_actor_name, strategic_actor_role = _extract_strategic_actor_identity(payload)
    current_case_id_to_exclude = str(situation_artifact.get("id") or "unknown_case").strip()

    try:
        enhanced = _enhance_actor_ontology_style(
            actor_payload=payload,
            actor_ref=actor_ref,
            strategic_actor_name=strategic_actor_name,
            strategic_actor_role=strategic_actor_role,
            current_case_id_to_exclude=current_case_id_to_exclude,
            config_path=config_path,
        )
    except Exception:
        return actor_ref

    if _apply_enhanced_style(payload, enhanced):
        actor_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    return actor_ref


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
            by_key.setdefault(
                slot_order[index],
                {
                    "scenario_key": slot_order[index],
                    "title": f"Scenario {slot_order[index]}",
                    "objective": text,
                    "constraints": [text],
                    "tradeoff_pressure": [],
                    "variables": [],
                    "resistance_assumptions": {},
                    "modeling_notes": [
                        "Derived from plain-text LLM scenario payload",
                        "Schema fallback applied by planner",
                    ],
                },
            )

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
            for index, item in enumerate(raw_variables, start=1):
                if isinstance(item, dict):
                    variables.append(item)
                    continue
                text = str(item).strip()
                if not text:
                    continue
                variables.append(
                    {
                        "name": text,
                        "type": "text",
                        "value_range_or_enum": [],
                        "baseline_assumption": text,
                        "rationale": "Variable normalized from plain-text decomposition output",
                        "signal_ref": f"signal::{policy.key.lower()}::{index}",
                        "constraint_ref": "market::primary",
                    }
                )

        if not variables:
            variables = [
                {
                    "name": "signal_direction",
                    "type": "categorical",
                    "value_range_or_enum": ["positive", "neutral", "negative"],
                    "baseline_assumption": policy.signal_basis,
                    "rationale": "Policy-guided fallback variable after LLM normalization",
                    "signal_ref": f"signal::{policy.key.lower()}::primary",
                    "constraint_ref": "market::primary",
                }
            ]

        resistance_raw = raw.get("resistance_assumptions") or {}
        resistance_note = ""
        if isinstance(resistance_raw, dict):
            resistance = resistance_raw
        else:
            resistance_note = str(resistance_raw).strip()
            resistance = {}
        default_r = policy.resistance
        extra_rationale = []
        if resistance_note:
            extra_rationale.append(resistance_note)
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
                        *extra_rationale,
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


def _build_raw_priors(
    *,
    decomposition: dict[str, Any],
    fallback_query: dict[str, Any],
) -> list[dict[str, Any]]:
    llm_priors = decomposition.get("raw_prior_scores")
    if isinstance(llm_priors, list):
        normalized: list[dict[str, Any]] = []
        for item in llm_priors:
            if not isinstance(item, dict):
                continue
            key = str(item.get("scenario_key") or "").strip().upper()
            if key not in {"A", "B", "C"}:
                continue
            normalized.append({"scenario_key": key, "score": float(item.get("score") or 0.0)})
        if len(normalized) == 3:
            return sorted(normalized, key=lambda item: item["scenario_key"])

    fallback = fallback_query.get("similarity_scores") or []
    output = [
        {
            "scenario_key": str(item.get("scenario_key") or "").strip().upper(),
            "score": float(item.get("score") or 0.0),
        }
        for item in fallback
        if str(item.get("scenario_key") or "").strip().upper() in {"A", "B", "C"}
    ]
    if len(output) != 3:
        output = [
            {"scenario_key": "A", "score": 0.4},
            {"scenario_key": "B", "score": 0.35},
            {"scenario_key": "C", "score": 0.25},
        ]
    return sorted(output, key=lambda item: item["scenario_key"])


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
    actor_ref = _ensure_strategic_actor_admissible(
        actor_ref=actor_ref,
        situation_artifact=situation_artifact,
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

    raw_priors = _build_raw_priors(decomposition=decomposition, fallback_query=planning_query)
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

    ontology = _build_scenario_ontology_from_situation_artifact(
        situation_artifact=situation_artifact,
        llm_decomposition=decomposition,
        pack_id=pack_id,
        pack_version=pack_version,
    )
    ontology["planning_query_ref"] = str(planning_query_path)
    ontology["prior_snapshot_ref"] = str(prior_snapshot_path)
    ontology["source_meta"] = {
        **(ontology.get("source_meta") or {}),
        "generated_at": datetime.now().isoformat(),
        "planner": "planner_v1",
    }
    return ontology
