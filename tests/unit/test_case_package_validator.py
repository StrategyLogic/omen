import json
from pathlib import Path

import pytest

from omen.scenario.validator import (
    validate_case_package_or_raise,
    validate_cross_case_output_contract_or_raise,
    validate_runtime_support_or_raise,
)


ROOT = Path(__file__).resolve().parents[2]
ONTOLOGY_SCENARIO = ROOT / "data" / "scenarios" / "ontology.json"


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
