from pathlib import Path

from omen.ingest.synthesizer.services.scenario import load_scenario
from omen.simulation.replay import create_counterfactual_config
from omen.simulation.engine import run_simulation


ROOT = Path(__file__).resolve().parents[2]
SCENARIO_PATH = ROOT / "data" / "scenarios" / "ontology.json"


def test_deterministic_core_outputs_stable_shape() -> None:
    config1 = load_scenario(SCENARIO_PATH)
    config2 = load_scenario(SCENARIO_PATH)

    result1 = run_simulation(config1)
    result2 = run_simulation(config2)

    assert result1["status"] == "completed"
    assert result2["status"] == "completed"
    assert result1["outcome_class"] in {"replacement", "convergence", "coexistence"}
    assert result2["outcome_class"] in {"replacement", "convergence", "coexistence"}
    assert len(result1["snapshots"]) == len(result2["snapshots"])
    assert result1["winner"]["user_edge_count"] == result2["winner"]["user_edge_count"]


def test_different_seed_can_change_simulation_trajectory() -> None:
    baseline = load_scenario(SCENARIO_PATH)
    variation = create_counterfactual_config(
        baseline,
        {
            "seed": 7,
            "random_perturbation": 0.3,
        },
    )

    result1 = run_simulation(baseline)
    result2 = run_simulation(variation)

    assert result1["winner"]["user_edge_count"] != result2["winner"]["user_edge_count"]
