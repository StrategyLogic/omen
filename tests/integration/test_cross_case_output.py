from pathlib import Path

from omen.scenario.loader import load_scenario_with_ontology
from omen.scenario.validator import validate_cross_case_output_contract_or_raise
from omen.simulation.engine import run_simulation
from omen.simulation.replay import compare_run_results, run_counterfactual


ROOT = Path(__file__).resolve().parents[2]
ONTOLOGY_SCENARIO = ROOT / "data" / "scenarios" / "ontology.json"
VECTOR_SCENARIO = ROOT / "data" / "scenarios" / "vector-memory.json"


def _build_cross_case_contract_for_scenario(path: Path) -> dict:
    scenario, ontology_setup = load_scenario_with_ontology(path)
    baseline = run_simulation(scenario, ontology_setup=ontology_setup)
    _, variation = run_counterfactual(
        scenario,
        {"user_overlap_threshold": 0.88},
        ontology_setup=ontology_setup,
    )
    comparison = compare_run_results(
        baseline,
        variation,
        conditions=[
            {
                "type": "override",
                "key": "user_overlap_threshold",
                "value": 0.88,
                "description": "override `user_overlap_threshold` -> 0.88",
            }
        ],
    )
    return {
        "result_artifact": {
            "scenario_id": baseline["scenario_id"],
            "outcome_class": baseline["outcome_class"],
            "winner": baseline.get("winner"),
            "timeline": baseline.get("timeline", []),
            "ontology_setup": baseline.get("ontology_setup"),
            "explanation": baseline.get("explanation"),
        },
        "explanation_artifact": {
            "branch_points": baseline["explanation"].get("branch_points", []),
            "causal_chain": baseline["explanation"].get("causal_chain", []),
            "narrative_summary": baseline["explanation"].get("narrative_summary"),
            "applied_axioms": baseline["explanation"].get("applied_axioms"),
            "rule_trace_references": baseline["explanation"].get("rule_trace_references"),
        },
        "comparison_artifact": {
            "baseline_outcome_class": comparison["baseline_outcome_class"],
            "variation_outcome_class": comparison["variation_outcome_class"],
            "conditions": comparison.get("conditions", []),
            "deltas": comparison.get("deltas", []),
        },
    }


def test_cross_case_output_contract_is_stable() -> None:
    ontology_contract = _build_cross_case_contract_for_scenario(ONTOLOGY_SCENARIO)
    vector_contract = _build_cross_case_contract_for_scenario(VECTOR_SCENARIO)

    ontology_validated = validate_cross_case_output_contract_or_raise(ontology_contract)
    vector_validated = validate_cross_case_output_contract_or_raise(vector_contract)

    assert ontology_validated.result_artifact.scenario_id
    assert vector_validated.result_artifact.scenario_id

    assert set(ontology_contract.keys()) == set(vector_contract.keys())
    assert set(ontology_contract["result_artifact"].keys()) == set(vector_contract["result_artifact"].keys())
    assert set(ontology_contract["explanation_artifact"].keys()) == set(
        vector_contract["explanation_artifact"].keys()
    )
    assert set(ontology_contract["comparison_artifact"].keys()) == set(
        vector_contract["comparison_artifact"].keys()
    )
