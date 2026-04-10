import json
from pathlib import Path

import pytest

from omen.ingest.synthesizer.services.scenario import load_scenario
from omen.ingest.validators.scenario import validate_scenario_or_raise


ROOT = Path(__file__).resolve().parents[2]
SCENARIO_PATH = ROOT / "data" / "scenarios" / "ontology.json"


def test_load_valid_scenario() -> None:
    scenario = load_scenario(SCENARIO_PATH)
    assert scenario.scenario_id == "ontology-battle-baseline"
    assert len(scenario.actors) >= 2


def test_reject_unknown_action() -> None:
    payload = json.loads(SCENARIO_PATH.read_text(encoding="utf-8"))
    payload["actors"][0]["available_actions"].append("unknown_move")
    with pytest.raises(Exception):
        validate_scenario_or_raise(payload)
