"""Scenario loader for ontology battle simulation."""

from __future__ import annotations

import json
from pathlib import Path

from omen.scenario.validator import ScenarioConfig, validate_scenario_or_raise


def load_scenario(path: str | Path) -> ScenarioConfig:
    scenario_path = Path(path)
    with scenario_path.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    return validate_scenario_or_raise(payload)
