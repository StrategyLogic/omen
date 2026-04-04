"""Situation analysis CLI commands."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from omen.scenario.loader import save_scenario_ontology_markdown, save_scenario_ontology_slice
from omen.scenario.situation_analyzer import build_scenario_ontology_from_situation
from omen.scenario.ingest_validator import DeferredScopeFeatureError


def _resolve_situation_doc_path(raw_doc: str) -> Path:
    raw = str(raw_doc).strip()
    if "/" in raw:
        candidate = Path(raw)
        if not candidate.suffix:
            candidate = candidate.with_suffix(".md")
        return candidate

    stem = raw[:-3] if raw.endswith(".md") else raw
    return Path("cases/situations") / f"{stem}.md"


def _resolve_default_output_path(input_path: Path) -> Path:
    return Path("data/scenarios") / f"{input_path.stem}.json"


def register_situation_analyze_commands(analyze_subparsers: Any) -> None:
    situation = analyze_subparsers.add_parser(
        "situation",
        help="analyze company situation documents into scenario ontology artifacts",
    )
    situation.add_argument(
        "--doc",
        required=False,
        help="Situation doc name or path. Bare names resolve to cases/situations/<doc>.md",
    )
    situation.add_argument(
        "--input",
        required=False,
        help="Deprecated alias for --doc",
    )
    situation.add_argument(
        "--actor",
        required=False,
        help="Optional actor reference path or identifier",
    )
    situation.add_argument(
        "--output",
        required=False,
        help="Optional output path for generated scenario ontology JSON. Defaults to data/scenarios/<doc_stem>.json",
    )
    situation.add_argument(
        "--pack-id",
        required=False,
        default="strategic_actor_nokia_v1",
        help="Deterministic pack id for scenario slot policy",
    )
    situation.add_argument(
        "--pack-version",
        required=False,
        default="1.0.0",
        help="Deterministic pack version",
    )


def handle_situation_analyze_command(args: Any) -> int:
    try:
        raw_doc = args.doc or args.input
        if not raw_doc:
            print("Analyze situation failed: missing required argument --doc")
            return 2

        input_path = _resolve_situation_doc_path(str(raw_doc))
        if not input_path.exists():
            print(f"Analyze situation failed: input not found: {input_path}")
            return 2

        output_path_arg = Path(args.output) if args.output else _resolve_default_output_path(input_path)

        ontology = build_scenario_ontology_from_situation(
            situation_file=input_path,
            actor_ref=args.actor,
            pack_id=str(args.pack_id),
            pack_version=str(args.pack_version),
        )
        output_path = save_scenario_ontology_slice(output_path_arg, ontology)
        markdown_path = output_path.with_suffix(".md")
        save_scenario_ontology_markdown(markdown_path, ontology)
        print(f"Saved scenario ontology artifact to {output_path}")
        print(f"Saved scenario ontology summary to {markdown_path}")
        return 0
    except DeferredScopeFeatureError as exc:
        print(f"Deferred scope: {exc}")
        print(
            "This release supports deterministic A/B/C packs only. "
            "Dynamic scenario authoring and enterprise resistance extensions are deferred."
        )
        return 2
    except Exception as exc:
        print(f"Analyze situation failed: {exc}")
        return 2
