from pathlib import Path

from omen.ingest.synthesizer.services.scenario import load_scenario
from omen.simulation.engine import run_simulation
from omen.simulation.replay import (
    compare_run_results,
    load_run_result,
    run_counterfactual,
    save_run_result,
)


ROOT = Path(__file__).resolve().parents[2]
SCENARIO_PATH = ROOT / "data" / "scenarios" / "ontology.json"


def test_counterfactual_compare_flow(tmp_path: Path) -> None:
    baseline = load_scenario(SCENARIO_PATH)
    baseline_result = run_simulation(baseline)
    baseline_path = save_run_result(baseline_result, tmp_path / "baseline.json")
    loaded_baseline = load_run_result(baseline_path)

    _, variation_result = run_counterfactual(
        baseline,
        {
            "user_overlap_threshold": 0.9,
            "actors.2.initial_user_base": 120,
        },
    )
    comparison = compare_run_results(loaded_baseline, variation_result)

    assert baseline_result["status"] == "completed"
    assert variation_result["status"] == "completed"
    assert loaded_baseline["run_id"] == baseline_result["run_id"]
    assert comparison["baseline_run_id"] == baseline_result["run_id"]
    assert comparison["variation_run_id"] == variation_result["run_id"]
    assert len(comparison["deltas"]) >= 3
    assert {delta["metric"] for delta in comparison["deltas"]} >= {
        "winner_user_edge_count",
        "competition_edge_count",
    }
