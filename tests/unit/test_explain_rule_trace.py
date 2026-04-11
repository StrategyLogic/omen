from pathlib import Path

from omen.explain.report import build_explanation_report
from omen.ingest.synthesizer.services.scenario import load_scenario_with_ontology
from omen.simulation.engine import run_simulation


ROOT = Path(__file__).resolve().parents[2]
SCENARIO_PATH = ROOT / "data" / "scenarios" / "ontology.json"


def test_explanation_includes_applied_axioms_and_rule_trace_references() -> None:
    scenario, ontology_setup = load_scenario_with_ontology(SCENARIO_PATH)
    result = run_simulation(scenario, ontology_setup=ontology_setup)

    explanation = build_explanation_report(result)
    assert "applied_axioms" in explanation
    assert "rule_trace_references" in explanation
    assert explanation["applied_axioms"]["activation"]
