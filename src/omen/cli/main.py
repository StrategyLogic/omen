"""CLI entrypoint for Omen MVP."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from omen.explain.report import build_explanation_report
from omen.scenario.loader import load_scenario
from omen.simulation.replay import (
    compare_run_results,
    create_counterfactual_config,
    load_run_result,
    run_counterfactual,
)
from omen.simulation.engine import run_simulation


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

    args = parser.parse_args()
    if args.command == "simulate":
        config = load_scenario(args.scenario)
        if args.seed is None:
            config = create_counterfactual_config(config, {"seed": None})
        else:
            config = create_counterfactual_config(config, {"seed": args.seed})
        result = run_simulation(config)
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
        config = load_scenario(args.scenario)
        baseline = run_simulation(config)
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

        _, variation = run_counterfactual(config, overrides)
        comparison = compare_run_results(baseline, variation, conditions=conditions)
        rendered = json.dumps(comparison, ensure_ascii=False, indent=2)
        output_path = _write_output(rendered, args.output, "comparison.json", args.incremental)
        print(f"Saved comparison to {output_path}")


if __name__ == "__main__":
    main()
