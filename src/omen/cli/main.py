"""CLI entrypoint for Omen MVP."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from omen.scenario.loader import load_scenario
from omen.simulation.engine import run_simulation


def main() -> None:
    parser = argparse.ArgumentParser(prog="omen", description="Omen strategic simulation CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    simulate = sub.add_parser("simulate", help="run one scenario simulation")
    simulate.add_argument("--scenario", required=True, help="Path to scenario JSON")
    simulate.add_argument("--output", required=False, help="Optional output JSON path")

    args = parser.parse_args()
    if args.command == "simulate":
        config = load_scenario(args.scenario)
        result = run_simulation(config)
        rendered = json.dumps(result, ensure_ascii=False, indent=2)
        if args.output:
            Path(args.output).write_text(rendered, encoding="utf-8")
        else:
            print(rendered)


if __name__ == "__main__":
    main()
