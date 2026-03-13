from pathlib import Path

from omen.scenario.loader import load_scenario
from omen.simulation.engine import run_simulation
from omen.simulation.precision_metrics import evaluate_repeatability
from omen.simulation.replay import create_counterfactual_config


ROOT = Path(__file__).resolve().parents[2]
SCENARIO_PATH = ROOT / "data" / "scenarios" / "ontology.json"


def test_precision_repeatability_with_fixed_seed() -> None:
    scenario = load_scenario(SCENARIO_PATH)

    runs = []
    for _ in range(5):
        seeded = create_counterfactual_config(scenario, {"seed": 42})
        runs.append(run_simulation(seeded))

    metrics = evaluate_repeatability(runs)

    assert metrics["run_count"] == 5
    assert metrics["outcome_consistency"] >= 0.9
    assert metrics["top_driver_consistency"] >= 0.9
