"""Scenario planning orchestrator for deterministic A/B/C artifacts."""

from __future__ import annotations

import json
import random
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from omen.analysis.actor.formation import ensure_strategic_actor_style
from omen.ingest.synthesizer.services.scenario import planning
from omen.scenario.models import ScenarioPlanningRuleTemplateModel
from omen.scenario.prior import build_prior_snapshot
from omen.scenario.prior import score_prior_probabilities
from omen.scenario.space import build_planning_query


REQUIRED_SCENARIO_KEYS: tuple[str, str, str] = ("A", "B", "C")


def load_template(path: str | Path = "config/templates/planning.yaml") -> ScenarioPlanningRuleTemplateModel:
    template_path = Path(path)
    if not template_path.is_absolute() and not template_path.exists():
        repo_root = Path(__file__).resolve().parents[3]
        template_path = repo_root / template_path
    payload = yaml.safe_load(template_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("planning template must be a YAML object")
    return ScenarioPlanningRuleTemplateModel.model_validate(payload)


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


def _validate(raw: dict[str, Any], *, scenario_key: str) -> None:
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


def normalize(
    llm_scenarios: list[Any],
) -> list[dict[str, Any]]:
    by_key: dict[str, dict[str, Any]] = {}

    for index, item in enumerate(llm_scenarios, start=1):
        if not isinstance(item, dict):
            raise ValueError(
                "LLM scenario decomposition must return JSON objects for all slots "
                f"(invalid position: {index})"
            )

        key = str(item.get("scenario_key") or "").strip().upper()
        if key not in REQUIRED_SCENARIO_KEYS:
            raise ValueError(
                f"LLM scenario decomposition has invalid scenario_key at position {index}: {key!r}"
            )
        if key in by_key:
            raise ValueError(f"LLM scenario decomposition duplicated scenario_key: {key}")
        by_key[key] = item

    missing = [key for key in REQUIRED_SCENARIO_KEYS if key not in by_key]
    if missing:
        raise ValueError(f"LLM scenario decomposition missing required slots: {missing}")

    normalized: list[dict[str, Any]] = []
    for key in REQUIRED_SCENARIO_KEYS:
        raw = by_key[key]
        _validate(raw, scenario_key=key)

        constraints = _nonempty_text_list(raw.get("constraints"))
        tradeoffs = _nonempty_text_list(raw.get("tradeoff_pressure"))

        raw_variables = raw.get("variables")
        variables: list[dict[str, Any]] = []
        if isinstance(raw_variables, list):
            for item in raw_variables:
                if isinstance(item, dict):
                    variables.append(item)

        if not variables:
            raise ValueError(f"LLM scenario decomposition slot {key} has empty variables")

        resistance_raw = raw.get("resistance_assumptions") or {}
        if not isinstance(resistance_raw, dict):
            raise ValueError(
                f"LLM scenario decomposition slot {key} must provide object resistance_assumptions"
            )

        rationale = [
            str(x).strip()
            for x in (resistance_raw.get("assumption_rationale") or [])
            if str(x).strip()
        ]
        if not rationale:
            raise ValueError(
                f"LLM scenario decomposition slot {key} missing resistance_assumptions.assumption_rationale"
            )

        normalized.append(
            {
                "scenario_key": key,
                "title": str(raw.get("title") or "").strip(),
                "goal": str(raw.get("goal") or "").strip(),
                "target": str(raw.get("target") or "").strip(),
                "objective": str(raw.get("objective") or "").strip(),
                "variables": variables,
                "constraints": constraints,
                "tradeoff_pressure": tradeoffs,
                "resistance_assumptions": {
                    "structural_conflict": float(resistance_raw["structural_conflict"]),
                    "resource_reallocation_drag": float(resistance_raw["resource_reallocation_drag"]),
                    "cultural_misalignment": float(resistance_raw["cultural_misalignment"]),
                    "veto_node_intensity": float(resistance_raw["veto_node_intensity"]),
                    "aggregate_resistance": float(resistance_raw["aggregate_resistance"]),
                    "assumption_rationale": rationale,
                },
                "modeling_notes": [
                    *[
                        str(x).strip()
                        for x in (raw.get("modeling_notes") or [])
                        if str(x).strip()
                    ],
                ],
            }
        )
    return normalized


def _build_from_situation_artifact(
    *,
    situation_artifact: dict[str, Any],
    llm_decomposition: dict[str, Any],
    pack_id: str,
    pack_version: str,
) -> dict[str, Any]:
    scenarios = normalize(
        list(llm_decomposition.get("scenarios") or []),
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


def _resolve_actor_json_ref(actor_ref: str | None) -> str | None:
    raw = str(actor_ref or "").strip()
    if not raw or raw in {"unknown_actor", "none"}:
        return None

    candidate = Path(raw)
    if not candidate.exists() or candidate.suffix.lower() != ".json":
        return None
    return raw


def _build_random_prior_fallback(*, scenario_ontology: dict[str, Any]) -> list[dict[str, Any]]:
    scenarios = [
        str(item.get("scenario_key") or "").strip().upper()
        for item in list(scenario_ontology.get("scenarios") or [])
        if isinstance(item, dict)
    ]
    keys = sorted([key for key in scenarios if key in {"A", "B", "C"}])
    if keys != ["A", "B", "C"]:
        keys = ["A", "B", "C"]

    rng = random.SystemRandom()
    samples = {key: rng.random() for key in keys}
    total = sum(samples.values()) or 1.0
    return [
        {
            "scenario_key": key,
            "score": samples[key] / total,
            "explain": "Fallback random prior due to unavailable actor-aware LLM scoring",
        }
        for key in keys
    ]


def _validate_artifact_or_raise(decomposition: dict[str, Any]) -> None:
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


def decompose_scenario_from_situation(
    *,
    situation_artifact: dict[str, Any],
    pack_id: str,
    pack_version: str,
    config_path: str,
    planning_template: dict[str, Any],
    planning_query: dict[str, Any],
) -> dict[str, Any]:
    return planning(
        situation_artifact=situation_artifact,
        pack_id=pack_id,
        pack_version=pack_version,
        config_path=config_path,
        planning_template=planning_template,
        planning_query=planning_query,
    )


def from_situation(
    *,
    situation_artifact: dict[str, Any],
    pack_id: str,
    pack_version: str,
    actor_ref: str | None,
    config_path: str,
    traces_dir: str | Path,
) -> dict[str, Any]:
    actor_json_ref = _resolve_actor_json_ref(actor_ref)
    if actor_json_ref:
        actor_enhancement_trace = ensure_strategic_actor_style(
            actor_ref=actor_json_ref,
            current_case_id_to_exclude=str(situation_artifact.get("id") or "unknown_case"),
            config_path=config_path,
        )
    else:
        actor_enhancement_trace = {
            "stage": "actor_style_enhancement",
            "status": "skipped",
            "reason": "actor_ref missing or not a valid actor ontology .json; planning remains decoupled",
            "actor_ref": str(actor_ref or ""),
        }

    template = load_template()
    planning_query = build_planning_query(
        situation_artifact=situation_artifact,
        actor_ref=str(actor_ref or "none"),
        template=template,
    )

    try:
        decomposition = decompose_scenario_from_situation(
            situation_artifact=situation_artifact,
            pack_id=pack_id,
            pack_version=pack_version,
            config_path=config_path,
            planning_template=template.model_dump(),
            planning_query=planning_query,
        )
    except Exception as exc:
        raise ScenarioDecompositionValidationError(
            "Scenario planning failed: LLM decomposition call failed. No local artifacts were written.",
            decomposition_payload={"error": str(exc), "error_type": type(exc).__name__},
        ) from exc

    _validate_artifact_or_raise(decomposition)

    traces_path = Path(traces_dir)
    traces_path.mkdir(parents=True, exist_ok=True)

    planning_query_path = traces_path / "planning_query.json"
    _write_auxiliary_json(planning_query_path, planning_query)

    ontology = _build_from_situation_artifact(
        situation_artifact=situation_artifact,
        llm_decomposition=decomposition,
        pack_id=pack_id,
        pack_version=pack_version,
    )

    try:
        if not actor_json_ref:
            raise ValueError("actor-aware prior scoring skipped: actor ontology json is unavailable")
        raw_priors, prior_scoring_trace = score_prior_probabilities(
            actor_ref=actor_json_ref,
            scenario_ontology=ontology,
            planning_query=planning_query,
            config_path=config_path,
        )
    except Exception:
        if not actor_json_ref:  
            raw_priors = _build_random_prior_fallback(scenario_ontology=ontology)  
            prior_scoring_trace = {  
                "stage": "scenario_prior_prompt",  
                "status": "fallback",  
                "reason": "actor-aware prior scoring skipped: actor ontology json is unavailable",  
                "scoring_source": "random_fallback",  
            }  
        else:  
            try:  
                raw_priors, prior_scoring_trace = score_prior_probabilities(  
                    actor_ref=actor_json_ref,  
                    scenario_ontology=ontology,  
                    planning_query=planning_query,  
                    config_path=config_path,  
                )  
            except (ValueError, TypeError, json.JSONDecodeError) as exc:  
                raw_priors = _build_random_prior_fallback(scenario_ontology=ontology)  
                prior_scoring_trace = {  
                    "stage": "scenario_prior_prompt",  
                    "status": "fallback",  
                    "reason": str(exc),  
                    "scoring_source": "random_fallback",  
                }  
            except Exception as exc:  
                prior_scoring_trace = {  
                    "stage": "scenario_prior_prompt",  
                    "status": "error",  
                    "reason": str(exc),  
                    "error_type": type(exc).__name__,  
                    "scoring_source": "score_prior_probabilities",  
                }  
                ontology["_planner_trace"] = {  
                    "actor_style_enhancement": actor_enhancement_trace,  
                    "prior_scoring": prior_scoring_trace,  
                }  
                raise

    prior_snapshot = build_prior_snapshot(
        pack_id=pack_id,
        pack_version=pack_version,
        situation_id=str(situation_artifact.get("id") or "unknown"),
        actor_ref=str(actor_json_ref or actor_ref or "none"),
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
