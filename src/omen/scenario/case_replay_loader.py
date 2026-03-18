"""Loader utilities for Spec 6 case replay artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from omen.scenario.ontology_loader import bind_ontology_to_scenario
from omen.scenario.validator import validate_scenario_or_raise
from omen.scenario.ontology_validator import validate_ontology_input_or_raise


def save_strategy_ontology(payload: dict[str, Any], path: str | Path) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return output


def validate_strategy_ontology(payload: dict[str, Any]) -> dict[str, Any]:
    validated = validate_ontology_input_or_raise(payload)
    return validated.model_dump(mode="python")


def load_case_replay_scenario(
    ontology_path: str | Path,
):
    ontology_payload = json.loads(Path(ontology_path).read_text(encoding="utf-8"))
    ontology = validate_ontology_input_or_raise(ontology_payload)
    scenario = validate_scenario_or_raise(ontology_payload)
    ontology_setup = bind_ontology_to_scenario(ontology, scenario)
    return scenario, ontology_setup
