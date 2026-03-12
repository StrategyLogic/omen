from pathlib import Path

from omen.explain.report import build_explanation_report
from omen.scenario.loader import load_scenario_with_ontology
from omen.simulation.engine import run_simulation
from omen.simulation.replay import compare_run_results, run_counterfactual


ROOT = Path(__file__).resolve().parents[2]
SCENARIO_PATH = ROOT / "data" / "scenarios" / "ontology.json"


def test_comparison_explanation_contains_rule_trace_references() -> None:
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
    explanation = build_explanation_report(variation, comparison=comparison)

    assert explanation["rule_trace_references"]
    assert any(ref["rule_id"].startswith("AX-") for ref in explanation["rule_trace_references"])
