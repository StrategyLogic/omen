"""Top-level founder analysis commands.

Command family:
- omen analyze founder --doc <name>
- omen analyze founder persona --doc <name>
- omen analyze founder strategy --doc <name>
- omen analyze founder insight --doc <name>
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from omen.analysis.founder.formation import build_strategic_formation_chain
from omen.analysis.founder.insight import generate_persona_insight, generate_unified_insight, generate_why_insight
from omen.analysis.founder.query import build_status_snapshot
from omen.ingest.llm_ontology.founder_service import generate_founder_and_events_from_document
from omen.ingest.llm_ontology.prompt_registry import ensure_analyze_prompt_available
from omen.ingest.llm_ontology.service import generate_strategy_ontology_from_document
from omen.ingest.llm_ontology.strategy_assembler import attach_founder_ref, attach_timeline_events
from omen.scenario.case_replay_loader import save_strategy_ontology
from omen.ui.artifacts import ensure_case_output_dir
from omen.ui.case_catalog import case_display_title, normalize_case_id, suggest_known_outcome


def register_analyze_commands(subparsers: Any) -> None:
    analyze = subparsers.add_parser("analyze", help="top-level analysis commands")
    analyze_sub = analyze.add_subparsers(dest="analyze_object", required=True)

    founder = analyze_sub.add_parser("founder", help="founder-focused analysis flow")
    founder.add_argument(
        "--doc",
        required=True,
        help="Document name or path. Bare names resolve to cases/founder/<doc>.md",
    )
    founder.add_argument("--title", required=False, help="Optional case title")
    founder.add_argument("--known-outcome", required=False, help="Optional known outcome")
    founder.add_argument("--year", required=False, type=int, help="Optional status snapshot year")
    founder.add_argument("--date", required=False, help="Optional status snapshot date")
    founder.add_argument("--event-id", required=False, help="Optional target event id")
    founder.add_argument(
        "--config",
        required=False,
        default="config/llm.toml",
        help="Path to local LLM config TOML",
    )
    founder.add_argument(
        "--output-dir",
        required=False,
        default="output/founder",
        help="Root output directory for founder analysis artifacts",
    )

    founder_sub = founder.add_subparsers(dest="founder_command", required=False)

    founder_sub.add_parser("persona", help="output persona only")
    founder_sub.add_parser("strategy", help="output strategic chain (formation + why)")
    founder_sub.add_parser("insight", help="output unified insight")


def _resolve_doc_path(doc: str) -> Path:
    raw = str(doc).strip()
    if "/" in raw:
        candidate = Path(raw)
        if not candidate.suffix:
            candidate = candidate.with_suffix(".md")
        return candidate

    stem = raw
    if stem.endswith(".md"):
        stem = stem[:-3]
    return Path("cases/founder") / f"{stem}.md"


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


def _pick_event_id(founder_payload: dict[str, Any], event_id: str | None) -> str:
    if event_id and str(event_id).strip():
        return str(event_id).strip()

    events = founder_payload.get("events")
    if isinstance(events, list) and events:
        for item in reversed(events):
            if not isinstance(item, dict):
                continue
            candidate = str(item.get("id") or item.get("event_id") or "").strip()
            if candidate:
                return candidate

    raise ValueError("No event id available. Use --event-id explicitly.")


def _ensure_founder_artifacts(args: Any) -> tuple[str, Path]:
    case_id = normalize_case_id(args.doc)
    doc_path = _resolve_doc_path(args.doc)
    if not doc_path.exists():
        raise FileNotFoundError(f"document not found: {doc_path}")

    case_dir = ensure_case_output_dir(case_id, output_root=args.output_dir)
    strategy_path = case_dir / "strategy_ontology.json"
    founder_path = case_dir / "founder_ontology.json"

    if strategy_path.exists() and founder_path.exists():
        return case_id, case_dir

    title = args.title or case_display_title(case_id)
    known_outcome = args.known_outcome or suggest_known_outcome(case_id)

    generation = generate_strategy_ontology_from_document(
        document_path=str(doc_path),
        case_id=case_id,
        title=title,
        strategy=None,
        known_outcome=known_outcome,
        config_path=args.config,
    )
    known_outcome_effective = generation.inferred_known_outcome or known_outcome

    founder_payload, timeline_events = generate_founder_and_events_from_document(
        document_path=str(doc_path),
        case_id=case_id,
        title=title,
        known_outcome=known_outcome_effective,
        config_path=args.config,
    )

    strategy_payload = attach_timeline_events(generation.strategy_ontology, timeline_events)
    strategy_payload = attach_founder_ref(
        strategy_payload,
        founder_payload,
        founder_filename=founder_path.name,
    )

    save_strategy_ontology(strategy_payload, strategy_path)
    founder_path.write_text(json.dumps(founder_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    report = {
        "case_id": case_id,
        "strategy_ontology_path": str(strategy_path),
        "founder_ontology_path": str(founder_path),
        "validation_passed": generation.validation_passed,
        "validation_issues": generation.validation_issues,
        "reused_existing": False,
    }
    (case_dir / "generation.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return case_id, case_dir


def _run_status(case_dir: Path, strategy_payload: dict[str, Any] | None, founder_payload: dict[str, Any], *, year: int | None, date: str | None) -> None:
    if strategy_payload is None:
        raise ValueError("Missing strategy ontology for status analysis")

    status_payload = build_status_snapshot(
        strategy_ontology=strategy_payload,
        founder_ontology=founder_payload,
        year=year,
        date=date,
    )
    output_path = case_dir / "analyze_status.json"
    output_path.write_text(json.dumps(status_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved analyze status payload to {output_path}")


def _run_persona(case_id: str, case_dir: Path, strategy_payload: dict[str, Any] | None, founder_payload: dict[str, Any], config_path: str) -> None:
    ensure_analyze_prompt_available("persona")
    persona_payload = generate_persona_insight(
        case_id=case_id,
        founder_ontology=founder_payload,
        strategy_ontology=strategy_payload,
        config_path=config_path,
    )
    output_path = case_dir / "analyze_persona.json"
    output_path.write_text(json.dumps(persona_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved analyze persona payload to {output_path}")


def _run_strategy(case_id: str, case_dir: Path, strategy_payload: dict[str, Any] | None, founder_payload: dict[str, Any], config_path: str, event_id: str | None) -> None:
    ensure_analyze_prompt_available("formation")
    ensure_analyze_prompt_available("why")

    target_event_id = _pick_event_id(founder_payload, event_id)
    formation_payload = build_strategic_formation_chain(
        founder_ontology=founder_payload,
        target_event_id=target_event_id,
    )
    formation_output = case_dir / "analyze_formation.json"
    formation_output.write_text(json.dumps(formation_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved analyze formation payload to {formation_output}")

    why_payload = generate_why_insight(
        case_id=case_id,
        founder_ontology=founder_payload,
        strategy_ontology=strategy_payload,
        decision_id=target_event_id,
        config_path=config_path,
    )
    why_output = case_dir / "analyze_why.json"
    why_output.write_text(json.dumps(why_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved analyze why payload to {why_output}")


def _run_insight(case_id: str, case_dir: Path, strategy_payload: dict[str, Any] | None, founder_payload: dict[str, Any], config_path: str, event_id: str | None) -> None:
    ensure_analyze_prompt_available("insight")

    formation_payload = None
    resolved_event_id = _pick_event_id(founder_payload, event_id)
    try:
        formation_payload = build_strategic_formation_chain(
            founder_ontology=founder_payload,
            target_event_id=resolved_event_id,
        )
    except Exception:
        formation_payload = None

    insight_payload = generate_unified_insight(
        case_id=case_id,
        founder_ontology=founder_payload,
        strategy_ontology=strategy_payload,
        formation_payload=formation_payload,
        config_path=config_path,
    )
    output_path = case_dir / "analyze_insight.json"
    output_path.write_text(json.dumps(insight_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved unified insight payload to {output_path}")


def handle_analyze_command(args: Any) -> int:
    if args.analyze_object != "founder":
        print(f"Analyze object `{args.analyze_object}` is not supported")
        return 3

    try:
        case_id, _ = _ensure_founder_artifacts(args)
        case_dir, strategy_payload, founder_payload = _load_analysis_artifacts(case_id, args.output_dir)
    except Exception as exc:
        print(f"Analyze founder setup failed: {exc}")
        return 2

    try:
        founder_command = getattr(args, "founder_command", None)

        if founder_command in (None, ""):
            _run_status(case_dir, strategy_payload, founder_payload, year=args.year, date=args.date)
            _run_persona(case_id, case_dir, strategy_payload, founder_payload, args.config)
            _run_strategy(case_id, case_dir, strategy_payload, founder_payload, args.config, args.event_id)
            _run_insight(case_id, case_dir, strategy_payload, founder_payload, args.config, args.event_id)
            print("Completed founder full analysis flow")
            return 0

        if founder_command == "persona":
            _run_persona(case_id, case_dir, strategy_payload, founder_payload, args.config)
            return 0

        if founder_command == "strategy":
            _run_strategy(case_id, case_dir, strategy_payload, founder_payload, args.config, args.event_id)
            return 0

        if founder_command == "insight":
            _run_insight(case_id, case_dir, strategy_payload, founder_payload, args.config, args.event_id)
            return 0

        print(f"Analyze founder sub-command `{founder_command}` is not supported")
        return 3
    except Exception as exc:
        print(f"Analyze founder failed: {exc}")
        return 2
