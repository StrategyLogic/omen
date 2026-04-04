"""Situation analysis CLI commands."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from omen.scenario.loader import save_scenario_ontology_slice
from omen.scenario.situation_analyzer import build_scenario_ontology_from_situation
from omen.scenario.ingest_validator import DeferredScopeFeatureError


def register_situation_analyze_commands(analyze_subparsers: Any) -> None:
    situation = analyze_subparsers.add_parser(
        "situation",
        help="analyze company situation documents into scenario ontology artifacts",
    )
    situation.add_argument(
        "--input",
        required=True,
        help="Path to situation source markdown under cases/situations/",
    )
    situation.add_argument(
        "--actor",
        required=True,
        help="Actor reference path or identifier",
    )
    situation.add_argument(
        "--output",
        required=True,
        help="Output path under data/scenarios/ for generated scenario ontology JSON",
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
        input_path = Path(args.input)
        if not input_path.exists():
            print(f"Analyze situation failed: input not found: {input_path}")
            return 2

        ontology = build_scenario_ontology_from_situation(
            situation_file=input_path,
            actor_ref=str(args.actor),
            pack_id=str(args.pack_id),
            pack_version=str(args.pack_version),
        )
        output_path = save_scenario_ontology_slice(args.output, ontology)
        print(f"Saved scenario ontology artifact to {output_path}")
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
