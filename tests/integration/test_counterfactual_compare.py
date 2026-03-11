from pathlib import Path

from omen.scenario.loader import load_scenario
from omen.simulation.engine import run_simulation


ROOT = Path(__file__).resolve().parents[2]
SCENARIO_PATH = ROOT / "data" / "scenarios" / "ontology.json"


def test_counterfactual_like_variation_changes_run_shape() -> None:
    baseline = load_scenario(SCENARIO_PATH)
    baseline_result = run_simulation(baseline)

    variation = load_scenario(SCENARIO_PATH)
    variation.user_overlap_threshold = 0.9
    variation_result = run_simulation(variation)

    assert baseline_result["status"] == "completed"
    assert variation_result["status"] == "completed"
    assert baseline_result["run_id"] != variation_result["run_id"]
