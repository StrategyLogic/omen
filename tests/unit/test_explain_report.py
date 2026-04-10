from pathlib import Path

from omen.explain.report import build_explanation_report
from omen.ingest.synthesizer.services.scenario import load_scenario
from omen.simulation.engine import run_simulation
from omen.simulation.replay import compare_run_results, run_counterfactual


ROOT = Path(__file__).resolve().parents[2]
SCENARIO_PATH = ROOT / "data" / "scenarios" / "ontology.json"


def test_explanation_payload_fields_present() -> None:
    config = load_scenario(SCENARIO_PATH)
    result = run_simulation(config)

    explanation = result["explanation"]
    assert explanation["run_id"] == result["run_id"]
    assert isinstance(explanation["branch_points"], list)
    assert isinstance(explanation["causal_chain"], list)
    assert isinstance(explanation["reality_gap_analysis"], list)
    assert isinstance(explanation["narrative_summary"], str)


def test_explanation_includes_counterfactual_deltas_when_provided() -> None:
    baseline = load_scenario(SCENARIO_PATH)
    baseline_result = run_simulation(baseline)
    _, variation_result = run_counterfactual(baseline, {"user_overlap_threshold": 0.9})
    comparison = compare_run_results(baseline_result, variation_result)

    explanation = build_explanation_report(variation_result, comparison=comparison)
    assert explanation["counterfactual_deltas"]
    assert any(delta["metric"] == "competition_edge_count" for delta in explanation["counterfactual_deltas"])


def test_explanation_reality_gap_analysis_populates_high_resistance_case() -> None:
    result = {
        "run_id": "run-1",
        "outcome_class": "convergence",
        "winner": {"actor_id": "x_developer_startup"},
        "snapshots": [],
        "ontology_setup": {
            "space_summary": {
                "adoption_resistance": 0.75,
            }
        },
        "real_world_outcome": "market_entry_failure",
    }

    explanation = build_explanation_report(result)
    gaps = explanation["reality_gap_analysis"]

    assert gaps
    assert any(gap["factor"] == "simulated_vs_real_outcome" for gap in gaps)
    assert any(gap["factor"] == "adoption_resistance" for gap in gaps)
