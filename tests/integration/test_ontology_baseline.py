from pathlib import Path

from omen.ingest.synthesizer.services.scenario import load_scenario
from omen.simulation.engine import run_simulation


ROOT = Path(__file__).resolve().parents[2]
SCENARIO_PATH = ROOT / "data" / "scenarios" / "ontology.json"


def test_baseline_simulation_completes() -> None:
    config = load_scenario(SCENARIO_PATH)
    result = run_simulation(config)

    assert result["status"] == "completed"
    assert result["outcome_class"] in {"replacement", "convergence", "coexistence"}
    assert result["winner"]["actor_id"]
    assert isinstance(result["winner"]["user_edge_count"], int)
    assert len(result["snapshots"]) == config.time_steps
