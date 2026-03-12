from pathlib import Path

from omen.scenario.loader import load_scenario_with_ontology
from omen.simulation.engine import run_simulation
from omen.simulation.replay import compare_run_results, run_counterfactual


ROOT = Path(__file__).resolve().parents[2]
SCENARIO_PATH = ROOT / "data" / "scenarios" / "ontology.json"


def test_compare_output_contains_semantic_conditions_and_ontology_setup() -> None:
    scenario, ontology_setup = load_scenario_with_ontology(SCENARIO_PATH)
    baseline = run_simulation(scenario, ontology_setup=ontology_setup)
    _, variation = run_counterfactual(
        scenario,
        {"user_overlap_threshold": 0.9},
        ontology_setup=ontology_setup,
    )

    comparison = compare_run_results(
        baseline,
        variation,
        conditions=[
            {
                "type": "override",
                "key": "user_overlap_threshold",
                "value": 0.9,
                "description": "override `user_overlap_threshold` -> 0.9",
            }
        ],
    )

    assert baseline.get("ontology_setup") is not None
    assert variation.get("ontology_setup") is not None
    assert comparison["conditions"][0]["semantic_type"] == "overlap_threshold_change"
