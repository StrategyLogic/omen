from pathlib import Path

import pytest

from omen.ingest.synthesizer.services.scenario import load_case_package_from_scenario


ROOT = Path(__file__).resolve().parents[2]
ONTOLOGY_SCENARIO = ROOT / "data" / "scenarios" / "ontology.json"
VECTOR_SCENARIO = ROOT / "data" / "scenarios" / "vector-memory.json"
INVALID_CASE_PACKAGE = ROOT / "tests" / "fixtures" / "ontology" / "invalid_case_package_missing_artifacts.json"


def test_load_case_package_from_ontology_scenario() -> None:
    pkg = load_case_package_from_scenario(ONTOLOGY_SCENARIO)

    assert pkg.manifest.case_id == "ontology"
    assert pkg.runtime_support.simulate_supported is True


def test_load_case_package_from_vector_memory_scenario() -> None:
    pkg = load_case_package_from_scenario(VECTOR_SCENARIO)

    assert pkg.manifest.case_id == "vector-memory"
    assert pkg.manifest.scenario_entry == "data/scenarios/vector-memory.json"


def test_reject_missing_case_package_artifacts() -> None:
    import json

    payload = json.loads(INVALID_CASE_PACKAGE.read_text(encoding="utf-8"))
    from omen.ingest.validators.scenario import validate_case_package_or_raise

    with pytest.raises(ValueError):
        validate_case_package_or_raise(payload, base_dir=ROOT)
