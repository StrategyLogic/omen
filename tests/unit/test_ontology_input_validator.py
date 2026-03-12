import json
from pathlib import Path

import pytest

from omen.scenario.ontology_validator import OntologyValidationError, validate_ontology_input_or_raise


ROOT = Path(__file__).resolve().parents[2]
VALID_PATH = ROOT / "data" / "scenarios" / "ontology.json"
INVALID_MISSING_CONCEPTS_PATH = ROOT / "tests" / "fixtures" / "ontology" / "invalid_missing_concepts.json"
INVALID_RULE_REF_PATH = ROOT / "tests" / "fixtures" / "ontology" / "invalid_rule_ref.json"


def test_validate_ontology_input_success() -> None:
    payload = json.loads(VALID_PATH.read_text(encoding="utf-8"))
    package = validate_ontology_input_or_raise(payload)

    assert package.meta.case_id == "ontology-battlefield"
    assert len(package.tbox.concepts) > 0
    assert len(package.reasoning_profile.activation_rules) > 0


def test_validate_ontology_input_rejects_missing_concepts() -> None:
    payload = json.loads(INVALID_MISSING_CONCEPTS_PATH.read_text(encoding="utf-8"))

    with pytest.raises(OntologyValidationError) as exc:
        validate_ontology_input_or_raise(payload)

    assert any(issue.code == "schema_validation_error" for issue in exc.value.issues)


def test_validate_ontology_input_rejects_unresolved_rule_ref() -> None:
    payload = json.loads(INVALID_RULE_REF_PATH.read_text(encoding="utf-8"))

    with pytest.raises(OntologyValidationError) as exc:
        validate_ontology_input_or_raise(payload)

    assert any(issue.code == "unresolved_rule_ref" for issue in exc.value.issues)
