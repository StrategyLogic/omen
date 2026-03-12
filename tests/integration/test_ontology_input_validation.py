from pathlib import Path

from omen.scenario.loader import load_scenario_with_ontology


ROOT = Path(__file__).resolve().parents[2]
SCENARIO_PATH = ROOT / "data" / "scenarios" / "ontology.json"


def test_load_scenario_with_ontology_binds_metadata() -> None:
    scenario, ontology_setup = load_scenario_with_ontology(SCENARIO_PATH)

    assert scenario.scenario_id == "ontology-battle-baseline"
    assert ontology_setup is not None
    assert ontology_setup["meta"]["case_id"] == "ontology-battlefield"
    assert ontology_setup["axiom_count"] >= 1
