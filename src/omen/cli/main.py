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
        required=True,
        help=(
            "JSON object of dotted-path overrides, "
            'e.g. {"user_overlap_threshold": 0.9}'
        ),
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

        try:
            overrides: dict[str, Any] = json.loads(args.overrides)
        except json.JSONDecodeError as exc:
            parser.error(f"invalid --overrides JSON: {exc}")
            return

        if not isinstance(overrides, dict):
            parser.error("--overrides must be a JSON object")
            return

        _, variation = run_counterfactual(config, overrides)
        comparison = compare_run_results(baseline, variation)
        rendered = json.dumps(comparison, ensure_ascii=False, indent=2)
        output_path = _write_output(rendered, args.output, "comparison.json", args.incremental)
        print(f"Saved comparison to {output_path}")


if __name__ == "__main__":
    main()
