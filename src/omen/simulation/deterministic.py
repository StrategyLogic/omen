"""Deterministic scenario simulate/compare orchestration."""

from __future__ import annotations

import datetime
import uuid
from pathlib import Path
from typing import Any

from omen.analysis.actor.formation import (
    assemble_capability_dilemma_fit,
    project_scenario_selected_dimensions,
)
from omen.analysis.actor.report_writer import (
    attach_strategic_freedom_summary,
    build_fixed_order_scenario_comparison,
    write_actor_derivation_artifact,
    write_deterministic_run_artifact,
    write_reason_chain_artifact,
    write_reason_chain_view_model_artifact,
)
from omen.analysis.actor.strategy import calculate_strategic_freedom_factor
from omen.ingest.synthesizer.services.scenario import prepare_deterministic_inputs_from_scenario
from omen.ingest.synthesizer.prompts.registry import get_scenario_reason_chain_prompt_version_token
from omen.ingest.validators.scenario import is_scenario_ontology_input_path
from omen.simulation.actor import (
    build_actor_derivation_artifact,
    build_actor_derivation_trace,
    build_comparability_metadata,
    derive_actor_path,
    get_simulate_reasoning_order,
)
from omen.simulation.reason import (
    apply_partial_evidence_confidence_policy,
    build_linked_evidence_refs,
    build_reason_chain_artifact,
    build_reason_chain_view_model_artifact,
    build_recommendation_from_condition_sets,
    build_scenario_reason_chain,
    extract_conclusion_buckets,
    resolve_reason_chain_with_llm,
)
from omen.types import DETERMINISTIC_PACK_REQUIRED_SLOTS


def run_deterministic_simulate_from_pack(
    *,
    pack: dict[str, Any],
    actor_profile_ref: str,
    calculation_policy_version: str,
    planned_scenarios: dict[str, dict[str, Any]] | None = None,
    actor_derivation_output_path: str | Path | None = None,
    config_path: str | None = None,
    debug: bool = False,
    workshop_ui_mode: bool = False,
) -> dict[str, Any]:
    capability_templates = {
        "A": {"ecosystem_control": 0.75, "execution_velocity": 0.58},
        "B": {"ecosystem_control": 0.5, "execution_velocity": 0.72},
        "C": {"ecosystem_control": 0.4, "execution_velocity": 0.65},
    }

    scenario_results: list[dict[str, Any]] = []
    scenario_derivations: list[dict[str, Any]] = []
    raw_reason_chain_inputs: list[tuple[str, dict[str, Any], dict[str, Any]]] = []
    for scenario in pack["scenarios"]:
        scenario_key = scenario["scenario_key"]
        scene = (planned_scenarios or {}).get(scenario_key) or {
            "objective": scenario.get("target_outcome", ""),
            "constraints": scenario.get("constraints", []),
            "tradeoff_pressure": scenario.get("dilemma_tradeoffs", []),
            "resistance_assumptions": scenario.get("resistance_baseline", {}),
        }
        capability_fit = assemble_capability_dilemma_fit(
            scenario_key=scenario_key,
            capability_scores=capability_templates.get(scenario_key, {}),
        )
        selected_dimensions = project_scenario_selected_dimensions(
            scenario_key=scenario_key,
            capability_scores=capability_templates.get(scenario_key, {}),
            scenario_ontology=scene,
        )
        actor_derivation = derive_actor_path(
            scenario_key=scenario_key,
            actor_profile_ref=actor_profile_ref,
            scenario_ontology=scene,
            selected_dimensions=selected_dimensions,
            capability_scores=capability_templates.get(scenario_key, {}),
            capability_fit=capability_fit["fit"],
        )
        confidence_level, missing_reasons = apply_partial_evidence_confidence_policy(
            evidence_refs=[],
            scenario_key=scenario_key,
        )
        strategic_score = calculate_strategic_freedom_factor(
            capability_fit=capability_fit["fit"],
            resistance_baseline=scenario["resistance_baseline"],
        )
        strategic_conditions = {
            "score": strategic_score,
            "required": [],
            "warning": [],
            "blocking": [],
            "reasoning_order": list(get_simulate_reasoning_order()),
        }
        derivation_trace = build_actor_derivation_trace(
            scenario_key=scenario_key,
            scenario_ontology=scene,
            actor_derivation=actor_derivation,
            selected_dimensions=selected_dimensions,
            strategic_conditions=strategic_conditions,
            missing_evidence_reasons=missing_reasons,
        )

        scenario_results.append(
            {
                "scenario_key": scenario_key,
                "capability_dilemma_fit": capability_fit,
                "selected_dimensions": selected_dimensions,
                "actor_derivation": actor_derivation,
                "resistance": scenario["resistance_baseline"],
                "strategic_freedom": strategic_conditions,
                "derivation_trace": derivation_trace,
                "evidence_refs": [],
                "confidence_level": confidence_level,
            }
        )
        scenario_derivations.append(
            {
                "scenario_key": scenario_key,
                "actor_derivation": actor_derivation,
                "selected_dimensions": selected_dimensions,
                "strategic_freedom_score": strategic_score,
            }
        )
        raw_reason_chain_inputs.append((scenario_key, scene, scenario_results[-1]))

    scenario_order = [str(item.get("scenario_key") or "") for item in scenario_results]

    comparability = build_comparability_metadata(
        actor_profile_version=actor_profile_ref,
        scenario_pack_version=pack["pack_version"],
        calculation_policy_version=calculation_policy_version,
        executed_order=scenario_order,
        required_order=DETERMINISTIC_PACK_REQUIRED_SLOTS,
    )
    run_id = f"det-{uuid.uuid4().hex[:12]}"
    artifact = {
        "run_id": run_id,
        "run_timestamp": datetime.datetime.now().isoformat(),
        "actor_profile_ref": actor_profile_ref,
        "scenario_pack_ref": pack["pack_id"],
        "scenario_results": scenario_results,
        "scenario_comparison": build_fixed_order_scenario_comparison(
            scenario_results,
            order=DETERMINISTIC_PACK_REQUIRED_SLOTS,
        ),
        "recommendation_summary": build_recommendation_from_condition_sets(scenario_results),
        "comparability": comparability,
        "export_status": "success",
    }

    if actor_derivation_output_path:
        traces_dir = Path(actor_derivation_output_path).parent
        generation_output_path = traces_dir.parent / "generation" / "output.txt"
        debug_output_path = str(generation_output_path) if debug else None

        reason_chain_rows: list[dict[str, Any]] = []

        for scenario_key, scene, result in raw_reason_chain_inputs:
            deterministic_row = build_scenario_reason_chain(
                run_id=run_id,
                scenario_key=scenario_key,
                scenario_ontology=scene,
                scenario_result=result,
            )
            deterministic_chain = dict(deterministic_row.get("reason_chain") or {})
            chain, llm_status = resolve_reason_chain_with_llm(
                deterministic_reason_chain=deterministic_chain,
                scenario_key=scenario_key,
                scenario_ontology=scene,
                scenario_result=result,
                actor_profile_ref=actor_profile_ref,
                config_path=config_path,
                debug_output_path=debug_output_path,
            )

            row = {
                "run_id": run_id,
                "scenario_key": scenario_key,
                "reason_chain": chain,
                "llm_status": llm_status,
            }
            reason_chain_rows.append(row)

            single_artifact = build_reason_chain_artifact(
                run_id=run_id,
                scenario_pack_ref=pack["pack_id"],
                scenario_chains=[row],
            )
            single_artifact["prompt_token"] = get_scenario_reason_chain_prompt_version_token()
            single_path = traces_dir / f"reason_chain_{scenario_key.lower()}.json"
            write_reason_chain_artifact(single_path, single_artifact)

        reason_chain_artifact = build_reason_chain_artifact(
            run_id=run_id,
            scenario_pack_ref=pack["pack_id"],
            scenario_chains=reason_chain_rows,
        )
        reason_chain_artifact["prompt_token"] = get_scenario_reason_chain_prompt_version_token()
        reason_chain_path = Path(actor_derivation_output_path).parent / "reason_chain.json"
        saved_reason_chain = write_reason_chain_artifact(reason_chain_path, reason_chain_artifact)
        artifact["reason_chain_ref"] = str(saved_reason_chain)

        chain_by_key = {
            str(item.get("scenario_key") or ""): dict(item.get("reason_chain") or {})
            for item in reason_chain_rows
            if isinstance(item, dict)
        }
        for result in scenario_results:
            key = str(result.get("scenario_key") or "")
            reason_chain = chain_by_key.get(key, {})
            buckets = extract_conclusion_buckets(dict(reason_chain.get("conclusions") or {}))
            freedom = dict(result.get("strategic_freedom") or {})
            freedom["required"] = [str(item.get("text") or "").strip() for item in buckets["required"] if str(item.get("text") or "").strip()]
            freedom["warning"] = [str(item.get("text") or "").strip() for item in buckets["warning"] if str(item.get("text") or "").strip()]
            freedom["blocking"] = [str(item.get("text") or "").strip() for item in buckets["blocking"] if str(item.get("text") or "").strip()]
            result["strategic_freedom"] = freedom
            result["evidence_refs"] = build_linked_evidence_refs(reason_chain)

            if result["evidence_refs"]:
                result["confidence_level"] = "full-confidence"
                derivation_trace = dict(result.get("derivation_trace") or {})
                derivation_trace["missing_evidence_reasons"] = []
                result["derivation_trace"] = derivation_trace

        for row in scenario_derivations:
            key = str(row.get("scenario_key") or "").strip().lower()
            row["reason_chain_ref"] = f"traces/reason_chain_{key}.json"

        derivation_artifact = build_actor_derivation_artifact(
            run_id=run_id,
            actor_profile_ref=actor_profile_ref,
            scenario_pack_ref=pack["pack_id"],
            scenario_derivations=scenario_derivations,
        )
        saved = write_actor_derivation_artifact(actor_derivation_output_path, derivation_artifact)
        artifact["actor_derivation_ref"] = str(saved)

        if workshop_ui_mode:
            view_model_artifact = build_reason_chain_view_model_artifact(
                run_id=run_id,
                scenario_pack_ref=pack["pack_id"],
                scenario_chains=reason_chain_rows,
            )
            view_model_path = Path(actor_derivation_output_path).parent / "reason_chain_view_model.json"
            saved_view_model = write_reason_chain_view_model_artifact(view_model_path, view_model_artifact)
            artifact["reason_chain_view_model_ref"] = str(saved_view_model)

    return attach_strategic_freedom_summary(artifact)


def run_deterministic_compare_from_pack(
    *,
    pack: dict[str, Any],
    actor_profile_ref: str,
    calculation_policy_version: str,
    planned_scenarios: dict[str, dict[str, Any]] | None = None,
    actor_derivation_output_path: str | Path | None = None,
    config_path: str | None = None,
    debug: bool = False,
    workshop_ui_mode: bool = False,
) -> dict[str, Any]:
    payload = run_deterministic_simulate_from_pack(
        pack=pack,
        actor_profile_ref=actor_profile_ref,
        calculation_policy_version=calculation_policy_version,
        planned_scenarios=planned_scenarios,
        actor_derivation_output_path=actor_derivation_output_path,
        config_path=config_path,
        debug=debug,
        workshop_ui_mode=workshop_ui_mode,
    )
    payload["comparison_type"] = "deterministic_pack"
    payload["recommendation_summary"] = "Deterministic compare completed."
    return payload


def run_deterministic_simulate_from_scenario_ontology(
    *,
    scenario_path: str | Path,
    actor_profile_ref: str,
    calculation_policy_version: str,
    actor_derivation_output_path: str | Path | None = None,
    config_path: str | None = None,
    debug: bool = False,
    workshop_ui_mode: bool = False,
) -> dict[str, Any]:
    pack_payload, planned_scenarios = prepare_deterministic_inputs_from_scenario(scenario_path)
    return run_deterministic_simulate_from_pack(
        pack=pack_payload,
        actor_profile_ref=actor_profile_ref,
        calculation_policy_version=calculation_policy_version,
        planned_scenarios=planned_scenarios,
        actor_derivation_output_path=actor_derivation_output_path,
        config_path=config_path,
        debug=debug,
        workshop_ui_mode=workshop_ui_mode,
    )


def run_deterministic_compare_from_scenario_ontology(
    *,
    scenario_path: str | Path,
    actor_profile_ref: str,
    calculation_policy_version: str,
    actor_derivation_output_path: str | Path | None = None,
    config_path: str | None = None,
    debug: bool = False,
    workshop_ui_mode: bool = False,
) -> dict[str, Any]:
    pack_payload, planned_scenarios = prepare_deterministic_inputs_from_scenario(scenario_path)
    return run_deterministic_compare_from_pack(
        pack=pack_payload,
        actor_profile_ref=actor_profile_ref,
        calculation_policy_version=calculation_policy_version,
        planned_scenarios=planned_scenarios,
        actor_derivation_output_path=actor_derivation_output_path,
        config_path=config_path,
        debug=debug,
        workshop_ui_mode=workshop_ui_mode,
    )


def try_run_deterministic_simulate_from_scenario_input(
    *,
    scenario_path: str | Path,
    actor_profile_ref: str,
    calculation_policy_version: str,
    config_path: str | None = None,
    debug: bool = False,
    workshop_ui_mode: bool = False,
) -> dict[str, Any] | None:
    if not is_scenario_ontology_input_path(scenario_path):
        return None

    actor_derivation_output_path = Path(scenario_path).parent / "traces" / "actor_derivation.json"
    return run_deterministic_simulate_from_scenario_ontology(
        scenario_path=scenario_path,
        actor_profile_ref=actor_profile_ref,
        calculation_policy_version=calculation_policy_version,
        actor_derivation_output_path=actor_derivation_output_path,
        config_path=config_path,
        debug=debug,
        workshop_ui_mode=workshop_ui_mode,
    )


def try_run_deterministic_compare_from_scenario_input(
    *,
    scenario_path: str | Path,
    actor_profile_ref: str,
    calculation_policy_version: str,
    config_path: str | None = None,
    debug: bool = False,
    workshop_ui_mode: bool = False,
) -> dict[str, Any] | None:
    if not is_scenario_ontology_input_path(scenario_path):
        return None

    actor_derivation_output_path = Path(scenario_path).parent / "traces" / "actor_derivation.json"
    return run_deterministic_compare_from_scenario_ontology(
        scenario_path=scenario_path,
        actor_profile_ref=actor_profile_ref,
        calculation_policy_version=calculation_policy_version,
        actor_derivation_output_path=actor_derivation_output_path,
        config_path=config_path,
        debug=debug,
        workshop_ui_mode=workshop_ui_mode,
    )


def save_deterministic_payload(output_path: str | Path, payload: dict[str, Any]) -> Path:
    return write_deterministic_run_artifact(output_path, payload)
