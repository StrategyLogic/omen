from pathlib import Path

from omen.ingest.synthesizer.services.scenario import load_scenario_with_ontology
from omen.simulation.engine import run_simulation
from omen.simulation.replay import compare_run_results, run_counterfactual


ROOT = Path(__file__).resolve().parents[2]
VECTOR_SCENARIO = ROOT / "data" / "scenarios" / "vector-memory.json"


def test_vector_memory_case_runs_shared_workflow() -> None:
    scenario, ontology_setup = load_scenario_with_ontology(VECTOR_SCENARIO)

    baseline = run_simulation(scenario, ontology_setup=ontology_setup)
    _, variation = run_counterfactual(
        scenario,
        {"user_overlap_threshold": 0.85},
        ontology_setup=ontology_setup,
    )
    comparison = compare_run_results(
        baseline,
        variation,
        conditions=[
            {
                "type": "override",
                "key": "user_overlap_threshold",
                "value": 0.85,
                "description": "override `user_overlap_threshold` -> 0.85",
            }
        ],
    )

    assert baseline["status"] == "completed"
    assert baseline["scenario_id"] == "vector-memory-baseline"
    assert "timeline" in baseline
    assert "branch_points" in baseline["explanation"]

    assert comparison["baseline_outcome_class"]
    assert comparison["variation_outcome_class"]
    assert isinstance(comparison["conditions"], list)
    assert isinstance(comparison["deltas"], list)
