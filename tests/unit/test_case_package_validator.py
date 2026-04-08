import json
from pathlib import Path

import pytest

from omen.ingest.validators.scenario import (
    validate_case_package_or_raise,
    validate_cross_case_output_contract_or_raise,
    validate_runtime_support_or_raise,
)


ROOT = Path(__file__).resolve().parents[2]
ONTOLOGY_SCENARIO = ROOT / "data" / "scenarios" / "ontology.json"
FIXTURE_CONTRACT_DIR = ROOT / "tests" / "fixtures" / "contracts"


def test_validate_runtime_support_rejects_disabled_capabilities() -> None:
    payload = {
        "simulate_supported": True,
        "explain_supported": True,
        "compare_supported": True,
        "semantic_conditions_supported": False,
        "rule_trace_supported": True,
    }

    with pytest.raises(Exception):
        validate_runtime_support_or_raise(payload)


def test_validate_case_package_from_scenario_payload() -> None:
    payload = json.loads(ONTOLOGY_SCENARIO.read_text(encoding="utf-8"))
    payload["case_package"]["required_artifacts"] = [
        str((FIXTURE_CONTRACT_DIR / "case-package.schema.json").relative_to(ROOT)),
        str((FIXTURE_CONTRACT_DIR / "cross-case-output.schema.json").relative_to(ROOT)),
    ]
    case_package = validate_case_package_or_raise(payload["case_package"], base_dir=ROOT)

    assert case_package.manifest.case_id == "ontology"
    assert case_package.runtime_support.compare_supported is True


def test_validate_cross_case_output_contract_minimal() -> None:
    contract = {
        "result_artifact": {
            "scenario_id": "s1",
            "outcome_class": "coexistence",
            "winner": None,
            "timeline": [],
            "ontology_setup": None,
            "explanation": None,
        },
        "explanation_artifact": {
            "branch_points": [],
            "causal_chain": [],
            "narrative_summary": None,
            "applied_axioms": None,
            "rule_trace_references": [],
        },
        "comparison_artifact": {
            "baseline_outcome_class": "coexistence",
            "variation_outcome_class": "convergence",
            "conditions": [
                {
                    "description": "override `user_overlap_threshold` -> 0.9",
                }
            ],
            "deltas": [],
        },
    }

    validated = validate_cross_case_output_contract_or_raise(contract)
    assert validated.result_artifact.outcome_class == "coexistence"
