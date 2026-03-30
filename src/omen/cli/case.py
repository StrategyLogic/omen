"""Case-oriented CLI command group for analysis workflows."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from omen.analysis.actor.insight import generate_persona_insight
from omen.analysis.actor.query import build_events_snapshot
from omen.ingest.llm_ontology.actor_service import generate_actor_and_events_from_document
from omen.ingest.llm_ontology.prompt_registry import ensure_analyze_prompt_available
from omen.ingest.llm_ontology.strategy_assembler import attach_founder_ref, attach_timeline_events
from omen.scenario.case_replay_loader import save_strategy_ontology
from omen.ui.artifacts import ensure_case_output_dir
from omen.ui.case_catalog import case_display_title, normalize_case_id, suggest_known_outcome


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
    from omen.ingest.llm_ontology.service import generate_strategy_ontology_from_document

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
