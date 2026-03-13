"""CLI entrypoint for Omen MVP."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from omen.explain.precision_report import build_precision_report
from omen.explain.report import build_explanation_report
from omen.ingest.assertion_builder import build_assertions_from_candidates
from omen.ingest.candidate_builder import build_candidates_from_text
from omen.ingest.pdf_extract import extract_pdf_pages
from omen.ingest.source_inventory import build_source_inventory
from omen.scenario.loader import load_case_package_from_scenario, load_scenario_with_ontology
from omen.scenario.ontology_loader import load_ontology_input
from omen.scenario.ingest_validator import validate_extracted_entity_candidates_or_raise
from omen.scenario.ingest_validator import validate_ontology_assertion_candidates_or_raise
from omen.scenario.ingest_validator import validate_precision_profile_or_raise
from omen.simulation.replay import (
    compare_run_results,
    create_counterfactual_config,
    load_run_result,
    run_counterfactual,
)
from omen.simulation.engine import run_simulation
from omen.simulation.precision_gate import evaluate_precision_gates
from omen.simulation.precision_metrics import evaluate_repeatability


def _with_timestamp_suffix(path: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    if path.suffix:
        return path.with_name(f"{path.stem}_{timestamp}{path.suffix}")
    return path.with_name(f"{path.name}_{timestamp}")


def _write_output(
    rendered: str,
    requested_path: str | None,
    default_filename: str,
    incremental: bool,
) -> Path:
    output_path = Path(requested_path) if requested_path else Path("output") / default_filename
    if incremental:
        output_path = _with_timestamp_suffix(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered, encoding="utf-8")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(prog="omen", description="Omen strategic simulation CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    simulate = sub.add_parser("simulate", help="run one scenario simulation")
    simulate.add_argument("--scenario", required=True, help="Path to scenario JSON")
    simulate.add_argument(
        "--ontology-input",
        required=False,
        help="Optional ontology input JSON path for battlefield setup metadata",
    )
    simulate.add_argument(
        "--seed",
        required=False,
        type=int,
        help="Optional stable seed. If omitted, simulate uses randomized seed each run.",
    )
    simulate.add_argument("--output", required=False, help="Optional output JSON path")
    simulate.add_argument(
        "--incremental",
        action="store_true",
        help="Add timestamp suffix to output filename to avoid overwrite",
    )

    explain = sub.add_parser("explain", help="generate explanation from a saved run result")
    explain.add_argument("--input", required=True, help="Path to saved run result JSON")
    explain.add_argument("--output", required=False, help="Optional output JSON path")
    explain.add_argument(
        "--incremental",
        action="store_true",
        help="Add timestamp suffix to output filename to avoid overwrite",
    )

    compare = sub.add_parser("compare", help="run counterfactual and compare with baseline")
    compare.add_argument("--scenario", required=True, help="Path to scenario JSON")
    compare.add_argument(
        "--ontology-input",
        required=False,
        help="Optional ontology input JSON path for battlefield setup metadata",
    )
    compare.add_argument(
        "--overrides",
        required=False,
        help=(
            "JSON object of dotted-path overrides, "
            'e.g. {"user_overlap_threshold": 0.9}'
        ),
    )
    compare.add_argument(
        "--budget-actor",
        required=False,
        help="Actor id for budget shock entry (commercial primary parameter)",
    )
    compare.add_argument(
        "--budget-delta",
        required=False,
        type=float,
        help="Budget delta applied to --budget-actor in variation run",
    )
    compare.add_argument("--output", required=False, help="Optional comparison JSON path")
    compare.add_argument(
        "--incremental",
        action="store_true",
        help="Add timestamp suffix to output filename to avoid overwrite",
    )

    precision_eval = sub.add_parser(
        "precision-eval",
        help="run repeated simulations and report repeatability metrics",
    )
    precision_eval.add_argument("--scenario", required=True, help="Path to scenario JSON")
    precision_eval.add_argument(
        "--ontology-input",
        required=False,
        help="Optional ontology input JSON path for battlefield setup metadata",
    )
    precision_eval.add_argument(
        "--runs",
        required=False,
        type=int,
        default=5,
        help="Number of repeated runs (default: 5)",
    )
    precision_eval.add_argument(
        "--seed",
        required=False,
        type=int,
        help="Optional fixed seed used for each run",
    )
    precision_eval.add_argument("--output", required=False, help="Optional output JSON path")
    precision_eval.add_argument(
        "--incremental",
        action="store_true",
        help="Add timestamp suffix to output filename to avoid overwrite",
    )

    ingest_dry_run = sub.add_parser(
        "ingest-dry-run",
        help="build mapped ingest candidates from text/pdf without runtime integration",
    )
    ingest_dry_run.add_argument("--scenario", required=True, help="Path to scenario JSON")
    ingest_dry_run.add_argument(
        "--ontology-input",
        required=False,
        help="Optional ontology input JSON path; defaults to scenario file when ontology is embedded",
    )
    ingest_dry_run.add_argument("--text-file", required=False, help="Path to input text file")
    ingest_dry_run.add_argument("--pdf-file", required=False, help="Path to input PDF file")
    ingest_dry_run.add_argument("--pdf-start-page", required=False, type=int, default=1)
    ingest_dry_run.add_argument("--pdf-end-page", required=False, type=int)
    ingest_dry_run.add_argument(
        "--build-assertions",
        action="store_true",
        help="Generate ontology assertion candidates from extracted candidates",
    )
    ingest_dry_run.add_argument(
        "--auto-approve-mapped",
        action="store_true",
        help="Allow auto-approval only for mapped high-confidence candidates",
    )
    ingest_dry_run.add_argument(
        "--auto-approve-threshold",
        required=False,
        type=float,
        default=0.9,
        help="Confidence threshold for auto-approval when --auto-approve-mapped is enabled",
    )
    ingest_dry_run.add_argument("--output", required=False, help="Optional output JSON path")
    ingest_dry_run.add_argument(
        "--incremental",
        action="store_true",
        help="Add timestamp suffix to output filename to avoid overwrite",
    )

    precision_gate = sub.add_parser(
        "precision-gate",
        help="evaluate precision release gates with profile + precision artifacts",
    )
    precision_gate.add_argument("--profile-json", required=True, help="Path to precision profile JSON")
    precision_gate.add_argument(
        "--precision-json",
        required=False,
        help="Optional precision-eval output JSON path",
    )
    precision_gate.add_argument(
        "--comparison-json",
        required=False,
        help="Optional compare output JSON path with precision_summary",
    )
    precision_gate.add_argument("--output", required=False, help="Optional output JSON path")
    precision_gate.add_argument(
        "--incremental",
        action="store_true",
        help="Add timestamp suffix to output filename to avoid overwrite",
    )

    args = parser.parse_args()
    if args.command == "simulate":
        load_case_package_from_scenario(args.scenario)
        config, ontology_setup = load_scenario_with_ontology(args.scenario, args.ontology_input)
        if args.seed is None:
            config = create_counterfactual_config(config, {"seed": None})
        else:
            config = create_counterfactual_config(config, {"seed": args.seed})
        result = run_simulation(config, ontology_setup=ontology_setup)
        rendered = json.dumps(result, ensure_ascii=False, indent=2)
        output_path = _write_output(rendered, args.output, "result.json", args.incremental)
        print(f"Saved simulation result to {output_path}")
    elif args.command == "explain":
        result = load_run_result(args.input)
        explanation = result.get("explanation") or build_explanation_report(result)
        rendered = json.dumps(explanation, ensure_ascii=False, indent=2)
        output_path = _write_output(rendered, args.output, "explanation.json", args.incremental)
        print(f"Saved explanation to {output_path}")
    elif args.command == "compare":
        load_case_package_from_scenario(args.scenario)
        config, ontology_setup = load_scenario_with_ontology(args.scenario, args.ontology_input)
        baseline = run_simulation(config, ontology_setup=ontology_setup)
        overrides: dict[str, Any] = {}
        conditions: list[dict[str, Any]] = []

        if args.overrides:
            try:
                overrides = json.loads(args.overrides)
            except json.JSONDecodeError as exc:
                parser.error(f"invalid --overrides JSON: {exc}")
                return

            if not isinstance(overrides, dict):
                parser.error("--overrides must be a JSON object")
                return
            for key, value in sorted(overrides.items()):
                conditions.append(
                    {
                        "type": "override",
                        "key": key,
                        "value": value,
                        "description": f"override `{key}` -> {value}",
                    }
                )

        has_budget_actor = args.budget_actor is not None
        has_budget_delta = args.budget_delta is not None
        if has_budget_actor != has_budget_delta:
            parser.error("--budget-actor and --budget-delta must be provided together")
            return

        if has_budget_actor and has_budget_delta:
            actor_index = next(
                (idx for idx, actor in enumerate(config.actors) if actor.actor_id == args.budget_actor),
                None,
            )
            if actor_index is None:
                parser.error(f"unknown --budget-actor: {args.budget_actor}")
                return
            original_budget = config.actors[actor_index].budget
            overrides[f"actors.{actor_index}.budget"] = original_budget + args.budget_delta
            conditions.append(
                {
                    "type": "budget_delta",
                    "actor_id": args.budget_actor,
                    "delta": args.budget_delta,
                    "new_budget": original_budget + args.budget_delta,
                    "description": (
                        f"budget shock for `{args.budget_actor}`: "
                        f"{original_budget} -> {original_budget + args.budget_delta} "
                        f"(delta {args.budget_delta})"
                    ),
                }
            )

        if not overrides:
            parser.error("provide --overrides and/or --budget-actor with --budget-delta")
            return

        _, variation = run_counterfactual(config, overrides, ontology_setup=ontology_setup)
        comparison = compare_run_results(baseline, variation, conditions=conditions)
        rendered = json.dumps(comparison, ensure_ascii=False, indent=2)
        output_path = _write_output(rendered, args.output, "comparison.json", args.incremental)
        print(f"Saved comparison to {output_path}")
    elif args.command == "precision-eval":
        if args.runs < 1:
            parser.error("--runs must be >= 1")
            return

        load_case_package_from_scenario(args.scenario)
        config, ontology_setup = load_scenario_with_ontology(args.scenario, args.ontology_input)

        results: list[dict[str, Any]] = []
        for _ in range(args.runs):
            if args.seed is None:
                run_config = create_counterfactual_config(config, {"seed": None})
            else:
                run_config = create_counterfactual_config(config, {"seed": args.seed})
            results.append(run_simulation(run_config, ontology_setup=ontology_setup))

        repeatability = evaluate_repeatability(results)
        payload = {
            "scenario_id": config.scenario_id,
            "runs": args.runs,
            "seed": args.seed,
            "repeatability": repeatability,
        }
        rendered = json.dumps(payload, ensure_ascii=False, indent=2)
        output_path = _write_output(rendered, args.output, "precision.json", args.incremental)
        print(f"Saved precision evaluation to {output_path}")
    elif args.command == "ingest-dry-run":
        load_case_package_from_scenario(args.scenario)
        has_text = bool(args.text_file)
        has_pdf = bool(args.pdf_file)
        if has_text == has_pdf:
            parser.error("provide exactly one of --text-file or --pdf-file")
            return

        ontology_path = args.ontology_input or args.scenario
        ontology = load_ontology_input(ontology_path)
        concept_names = [concept.name for concept in ontology.tbox.concepts]

        if has_text:
            text_path = Path(args.text_file)
            if not text_path.exists():
                parser.error(f"--text-file not found: {text_path}")
                return
            raw_text = text_path.read_text(encoding="utf-8")
            document_id = text_path.stem
            source_type = "text"
            source_path = str(text_path)
        else:
            pdf_path = Path(args.pdf_file)
            raw_text = extract_pdf_pages(
                pdf_path,
                start_page=args.pdf_start_page,
                end_page=args.pdf_end_page,
            )
            document_id = pdf_path.stem
            source_type = "pdf"
            source_path = str(pdf_path)

        candidates = build_candidates_from_text(
            raw_text,
            document_id=document_id,
            concept_names=concept_names,
        )
        validate_extracted_entity_candidates_or_raise(candidates)

        assertion_candidates: list[dict[str, Any]] = []
        if args.build_assertions:
            assertion_candidates = build_assertions_from_candidates(
                candidates,
                auto_approve_mapped=args.auto_approve_mapped,
                auto_approve_threshold=args.auto_approve_threshold,
            )
            validate_ontology_assertion_candidates_or_raise(assertion_candidates)

        assertion_review_summary = {
            "pending": sum(1 for item in assertion_candidates if item.get("review_state") == "pending"),
            "approved": sum(1 for item in assertion_candidates if item.get("review_state") == "approved"),
            "rejected": sum(1 for item in assertion_candidates if item.get("review_state") == "rejected"),
        }

        payload = {
            "document": {
                "document_id": document_id,
                "source_type": source_type,
                "source_path": source_path,
            },
            "source_inventory": build_source_inventory(),
            "candidate_count": len(candidates),
            "mapped_count": sum(1 for item in candidates if item.get("mapping_status") == "mapped"),
            "candidates": candidates,
            "assertion_count": len(assertion_candidates),
            "assertion_review_summary": assertion_review_summary,
            "assertions": assertion_candidates,
        }
        rendered = json.dumps(payload, ensure_ascii=False, indent=2)
        output_path = _write_output(rendered, args.output, "ingest_candidates.json", args.incremental)
        print(f"Saved ingest dry-run candidates to {output_path}")
    elif args.command == "precision-gate":
        profile_payload = json.loads(Path(args.profile_json).read_text(encoding="utf-8"))
        profile = validate_precision_profile_or_raise(profile_payload)

        precision_payload = None
        if args.precision_json:
            precision_payload = json.loads(Path(args.precision_json).read_text(encoding="utf-8"))

        comparison_payload = None
        if args.comparison_json:
            comparison_payload = json.loads(Path(args.comparison_json).read_text(encoding="utf-8"))

        if not precision_payload and not comparison_payload:
            parser.error("provide --precision-json and/or --comparison-json")
            return

        directional_metrics = (
            ((comparison_payload or {}).get("precision_summary", {}) or {}).get(
                "directional_correctness", {}
            )
        )
        trace_metrics = (
            ((comparison_payload or {}).get("precision_summary", {}) or {}).get(
                "trace_completeness", {}
            )
        )
        repeatability_metrics = (precision_payload or {}).get("repeatability", {})

        gate_evaluation = evaluate_precision_gates(
            profile,
            repeatability_metrics=repeatability_metrics,
            directional_metrics=directional_metrics,
            trace_metrics=trace_metrics,
        )
        report = build_precision_report(
            gate_evaluation=gate_evaluation,
            profile_payload=profile_payload,
            precision_payload=precision_payload,
            comparison_payload=comparison_payload,
        )
        rendered = json.dumps(report, ensure_ascii=False, indent=2)
        output_path = _write_output(rendered, args.output, "precision_gate_report.json", args.incremental)
        print(f"Saved precision gate report to {output_path}")


if __name__ == "__main__":
    main()
