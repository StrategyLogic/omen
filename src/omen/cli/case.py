"""Case-oriented CLI command group for analysis workflows."""

from __future__ import annotations

import datetime
import json
import uuid
from pathlib import Path
from typing import Any

from omen.analysis.actor.derivation import (
    derive_actor_path,
    derive_strategic_freedom_conditions,
)
from omen.analysis.actor.derivation_trace import (
    build_linked_evidence_refs,
    build_actor_derivation_artifact,
    build_actor_derivation_trace,
    build_reason_chain_artifact,
    build_reason_chain_view_model_artifact,
    build_scenario_reason_chain,
)
from omen.analysis.actor.insight import generate_persona_insight
from omen.analysis.actor.insight import build_recommendation_from_condition_sets
from omen.analysis.actor.insight import apply_partial_evidence_confidence_policy
from omen.analysis.actor.insight import try_generate_scenario_reason_chain_via_llm
from omen.analysis.actor.comparability import build_comparability_metadata
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
from omen.analysis.actor.strategy import (
    calculate_strategic_freedom_factor,
)
from omen.analysis.actor.query import build_events_snapshot
from omen.types import DETERMINISTIC_PACK_REQUIRED_SLOTS
from omen.ingest.synthesizer.services.actor import generate_actor_and_events_from_document
from omen.ingest.synthesizer.prompts.registry import ensure_analyze_prompt_available
from omen.ingest.synthesizer.prompts.registry import get_scenario_reason_chain_prompt_version_token
from omen.ingest.synthesizer.assembler import attach_founder_ref, attach_timeline_events
from omen.scenario.case_replay_loader import save_strategy_ontology
from omen.ui.artifacts import ensure_case_output_dir
from omen.ui.case_catalog import case_display_title, normalize_case_id, suggest_known_outcome


def _load_json_file(path: str | Path) -> dict[str, Any]:
    file_path = Path(path)
    return json.loads(file_path.read_text(encoding="utf-8"))


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

    scenario_results = []
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
        strategic_conditions = derive_strategic_freedom_conditions(
            scenario_key=scenario_key,
            actor_derivation=actor_derivation,
            selected_dimensions=selected_dimensions,
            resistance_baseline=scenario["resistance_baseline"],
            capability_fit=capability_fit["fit"],
        )
        confidence_level, missing_reasons = apply_partial_evidence_confidence_policy(
            evidence_refs=[],
            scenario_key=scenario_key,
        )
        derivation_trace = build_actor_derivation_trace(
            scenario_key=scenario_key,
            scenario_ontology=scene,
            actor_derivation=actor_derivation,
            selected_dimensions=selected_dimensions,
            strategic_conditions=strategic_conditions,
            missing_evidence_reasons=missing_reasons,
        )
        strategic_score = calculate_strategic_freedom_factor(
            capability_fit=capability_fit["fit"],
            resistance_baseline=scenario["resistance_baseline"],
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

        derivation_artifact = build_actor_derivation_artifact(
            run_id=run_id,
            actor_profile_ref=actor_profile_ref,
            scenario_pack_ref=pack["pack_id"],
            scenario_derivations=scenario_derivations,
        )
        saved = write_actor_derivation_artifact(actor_derivation_output_path, derivation_artifact)
        artifact["actor_derivation_ref"] = str(saved)

        reason_chain_rows = [
            build_scenario_reason_chain(
                run_id=run_id,
                scenario_key=scenario_key,
                scenario_ontology=scene,
                scenario_result=result,
            )
            for scenario_key, scene, result in raw_reason_chain_inputs
        ]

        # Optional LLM override path for intermediate reasoning detail only.
        # Deterministic core chain remains generated locally for replay stability.
        for item in reason_chain_rows:
            scenario_key = str(item.get("scenario_key") or "")
            chain = item.get("reason_chain") or {}
            deterministic_intermediate = dict(chain.get("intermediate") or {})
            llm_payload = try_generate_scenario_reason_chain_via_llm(
                scenario_json=(planned_scenarios or {}).get(scenario_key) or {},
                actor_profile_json={"actor_profile_ref": actor_profile_ref},
                planning_query_json={},
                situation_markdown="",
                config_path=config_path,
                debug_output_path=debug_output_path,
                scenario_key=scenario_key,
            )
            if isinstance(llm_payload, dict):
                llm_chain = llm_payload.get("reason_chain") if isinstance(llm_payload.get("reason_chain"), dict) else {}
                if isinstance(llm_chain.get("steps"), list) and llm_chain.get("steps"):
                    chain["steps"] = llm_chain.get("steps")
                if isinstance(llm_chain.get("conclusions"), dict) and llm_chain.get("conclusions"):
                    chain["conclusions"] = llm_chain.get("conclusions")
                llm_intermediate = llm_chain.get("intermediate") if isinstance(llm_chain.get("intermediate"), dict) else {}
                chain["intermediate"] = llm_intermediate or deterministic_intermediate
            else:
                chain["intermediate"] = deterministic_intermediate

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
            result["evidence_refs"] = build_linked_evidence_refs(reason_chain)

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


def save_deterministic_payload(output_path: str | Path, payload: dict[str, Any]) -> Path:
    return write_deterministic_run_artifact(output_path, payload)


def register_case_commands(subparsers: Any) -> None:
    case = subparsers.add_parser("case", help="case-oriented build and analysis commands")
    case_sub = case.add_subparsers(dest="case_command", required=True)

    build = case_sub.add_parser("build", help="build strategy + founder ontology artifacts")
    build.add_argument("--document", required=True, help="Path to case document")
    build.add_argument("--case-id", required=True, help="Case identifier")
    build.add_argument("--title", required=False, help="Optional case title")
    build.add_argument(
        "--known-outcome",
        required=False,
        help="Optional known historical outcome",
    )
    build.add_argument("--strategy", required=False, help="Optional strategy family label")
    build.add_argument(
        "--config",
        required=False,
        default="config/llm.toml",
        help="Path to local LLM config TOML",
    )
    build.add_argument(
        "--output-dir",
        required=False,
        default="output/case_replay",
        help="Root output directory",
    )
    build.add_argument(
        "--reuse-if-valid",
        action="store_true",
        help="Reuse existing artifacts when both strategy and founder files are present",
    )

    analyze = case_sub.add_parser("analyze", help="insight-time founder analysis")
    analyze_sub = analyze.add_subparsers(dest="analyze_command", required=True)

    status = analyze_sub.add_parser("status", help="show objective status snapshot")
    status.add_argument("--case-id", required=True, help="Case identifier")
    status.add_argument("--year", required=False, type=int, help="Snapshot year")
    status.add_argument("--date", required=False, help="Snapshot date")
    status.add_argument(
        "--output-dir",
        required=False,
        default="output/case_replay",
        help="Root output directory",
    )
    status.add_argument(
        "--output",
        required=False,
        help="Optional output JSON path for analyze status payload",
    )

    persona = analyze_sub.add_parser("persona", help="show subjective founder persona")
    persona.add_argument("--case-id", required=True, help="Case identifier")
    persona.add_argument("--year-range", required=False, help="Year range like 2014:2018")
    persona.add_argument(
        "--config",
        required=False,
        default="config/llm.toml",
        help="Path to local LLM config TOML",
    )
    persona.add_argument(
        "--output-dir",
        required=False,
        default="output/case_replay",
        help="Root output directory",
    )
    persona.add_argument(
        "--output",
        required=False,
        help="Optional output JSON path for analyze persona payload",
    )


def _generation_report_payload(
    *,
    case_id: str,
    strategy_path: Path,
    founder_path: Path,
    validation_passed: bool,
    validation_issues: list[dict[str, Any]],
    reused_existing: bool,
) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "strategy_ontology_path": str(strategy_path),
        "founder_ontology_path": str(founder_path),
        "validation_passed": validation_passed,
        "validation_issues": validation_issues,
        "reused_existing": reused_existing,
    }


def _load_analysis_artifacts(case_id: str, output_dir: str) -> tuple[Path, dict[str, Any] | None, dict[str, Any]]:
    case_dir = ensure_case_output_dir(case_id, output_root=output_dir)
    strategy_path = case_dir / "strategy_ontology.json"
    founder_path = case_dir / "founder_ontology.json"

    if not founder_path.exists():
        raise FileNotFoundError(f"missing founder artifact: {founder_path}")

    founder_payload = json.loads(founder_path.read_text(encoding="utf-8"))
    strategy_payload = None
    if strategy_path.exists():
        strategy_payload = json.loads(strategy_path.read_text(encoding="utf-8"))
    return case_dir, strategy_payload, founder_payload


def handle_case_command(args: Any) -> int:
    from omen.ingest.synthesizer.services.strategy import generate_strategy_ontology_from_document

    def emit(step: str, status: str, message: str) -> None:
        print(f"[CASE-BUILD][{step}][{status}] {message}", flush=True)

    if args.case_command == "analyze":
        if args.analyze_command == "status":
            case_id = normalize_case_id(args.case_id)
            case_dir = ensure_case_output_dir(case_id, output_root=args.output_dir)
            strategy_path = case_dir / "strategy_ontology.json"
            founder_path = case_dir / "founder_ontology.json"

            if not strategy_path.exists() or not founder_path.exists():
                print(
                    "Analyze status requires existing artifacts. "
                    f"Missing file(s): strategy={strategy_path.exists()}, founder={founder_path.exists()}"
                )
                return 2

            strategy_payload = json.loads(strategy_path.read_text(encoding="utf-8"))
            founder_payload = json.loads(founder_path.read_text(encoding="utf-8"))

            status_payload = build_events_snapshot(
                strategy_ontology=strategy_payload,
                actor_ontology=founder_payload,
                year=args.year,
                date=args.date,
            )

            output_path = Path(args.output) if args.output else case_dir / "analyze_status.json"
            output_path.write_text(
                json.dumps(status_payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            print(f"Saved analyze status payload to {output_path}")
            print(
                "Summary: "
                f"timeline_events={status_payload['summary']['timeline_event_count']}, "
                f"actor_nodes={status_payload['summary']['actor_node_count']}, "
                f"actor_edges={status_payload['summary']['actor_edge_count']}"
            )
            return 0

        if args.analyze_command == "persona":
            try:
                ensure_analyze_prompt_available("persona")
                case_id = normalize_case_id(args.case_id)
                case_dir, strategy_payload, founder_payload = _load_analysis_artifacts(case_id, args.output_dir)
            except Exception as exc:
                print(f"Analyze persona is unavailable: {exc}")
                return 2

            try:
                persona_payload = generate_persona_insight(
                    case_id=case_id,
                    actor_ontology=founder_payload,
                    strategy_ontology=strategy_payload,
                    config_path=args.config,
                )
            except Exception as exc:
                print(f"Analyze persona failed: {exc}")
                return 2

            output_path = Path(args.output) if args.output else case_dir / "analyze_persona.json"
            output_path.write_text(
                json.dumps(persona_payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            print(f"Saved analyze persona payload to {output_path}")
            return 0

        print(f"Analyze command `{args.analyze_command}` is not implemented yet.")
        return 3
    if args.case_command != "build":
        raise ValueError(f"unsupported case sub-command: {args.case_command}")

    case_id = normalize_case_id(args.case_id)
    case_dir = ensure_case_output_dir(case_id, output_root=args.output_dir)
    strategy_path = case_dir / "strategy_ontology.json"
    founder_path = case_dir / "founder_ontology.json"

    emit("init", "STARTED", f"case_id={case_id}, output_dir={case_dir}")

    if args.reuse_if_valid and strategy_path.exists() and founder_path.exists():
        emit("reuse", "PASSED", "reusing existing strategy/founder artifacts")
        report = _generation_report_payload(
            case_id=case_id,
            strategy_path=strategy_path,
            founder_path=founder_path,
            validation_passed=True,
            validation_issues=[],
            reused_existing=True,
        )
        (case_dir / "generation.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"Reused strategy ontology: {strategy_path}")
        print(f"Reused founder ontology: {founder_path}")
        return 0

    title = args.title or case_display_title(case_id)
    known_outcome = args.known_outcome or suggest_known_outcome(case_id)

    emit("strategy_generation", "STARTED", "generating strategy ontology")
    generation = generate_strategy_ontology_from_document(
        document_path=args.document,
        case_id=case_id,
        title=title,
        strategy=args.strategy,
        known_outcome=known_outcome,
        config_path=args.config,
        logger=emit,
    )
    known_outcome_effective = generation.inferred_known_outcome or known_outcome
    emit("strategy_generation", "PASSED", f"validation_passed={generation.validation_passed}")

    emit("slice_generation", "STARTED", "generating founder ontology + timeline events")
    founder_payload, timeline_events = generate_actor_and_events_from_document(
        document_path=args.document,
        case_id=case_id,
        title=title,
        known_outcome=known_outcome_effective,
        config_path=args.config,
        logger=emit,
    )
    emit(
        "slice_generation",
        "PASSED",
        f"founder_actors={len(founder_payload.get('actors') or [])}, timeline_events={len(timeline_events)}",
    )

    strategy_payload = generation.strategy_ontology
    emit("assemble", "RUNNING", "attaching timeline events and founder_ref to strategy ontology")
    strategy_payload = attach_timeline_events(strategy_payload, timeline_events)
    strategy_payload = attach_founder_ref(
        strategy_payload,
        founder_payload,
        founder_filename=founder_path.name,
    )
    emit("assemble", "PASSED", "strategy ontology assembled")

    emit("persist", "RUNNING", "writing artifacts to disk")
    save_strategy_ontology(strategy_payload, strategy_path)
    founder_path.write_text(json.dumps(founder_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    report = _generation_report_payload(
        case_id=case_id,
        strategy_path=strategy_path,
        founder_path=founder_path,
        validation_passed=generation.validation_passed,
        validation_issues=generation.validation_issues,
        reused_existing=False,
    )
    (case_dir / "generation.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    emit("persist", "PASSED", "artifacts written: strategy_ontology.json, founder_ontology.json, generation.json")

    print(f"Saved strategy ontology to {strategy_path}")
    print(f"Saved founder ontology to {founder_path}")
    print(f"Saved generation report to {case_dir / 'generation.json'}")

    if not generation.validation_passed:
        emit("done", "FAILED", "strategy ontology contains validation issues")
        print("Strategy ontology generated with validation issues")
        return 2
    emit("done", "PASSED", "case build completed successfully")
    return 0
