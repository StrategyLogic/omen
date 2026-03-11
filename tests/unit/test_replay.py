from pathlib import Path

from omen.scenario.loader import load_scenario
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
