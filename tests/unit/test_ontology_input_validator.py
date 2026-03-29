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


def test_validate_ontology_input_accepts_flexible_case_shape() -> None:
    payload = {
        "meta": {
            "version": "1.0",
            "case_id": "x-developer-replay",
            "domain": "management_ontology",
        },
        "tbox": {
            "concepts": [
                {
                    "concept": [
                        {"id": "c1", "name": "DataDrivenManagementActor"},
                        {"id": "c2", "name": "decision_support"},
                    ]
                }
            ],
            "relations": [
                {
                    "name": "has_capability",
                    "source": "DataDrivenManagementActor",
                    "target": "decision_support",
                    "description": "Actor has capability",
                }
            ],
            "axioms": [
                {"id": "rule_1"},
                {"id": "rule_custom", "type": "domain_specific"},
            ],
        },
        "abox": {
            "actors": [
                {
                    "actor": [
                        {
                            "id": "xd_platform",
                            "name": "X-Developer Platform",
                            "concept": "DataDrivenManagementActor",
                        }
                    ]
                }
            ],
            "capabilities": [
                {"actor_id": "xd_platform", "name": "decision_support", "score": 0.85}
            ],
        },
        "reasoning_profile": {
            "activation_rules": [{"id": "rule_1"}],
        },
    }

    package = validate_ontology_input_or_raise(payload)

    assert package.tbox.concepts[0].name == "DataDrivenManagementActor"
    assert package.abox.actors[0].actor_id == "xd_platform"
    assert package.reasoning_profile.activation_rules[0].rule_id == "rule_1"


def test_validate_ontology_input_accepts_raw_llm_style_payload() -> None:
    payload = {
        "meta": {
            "case_id": "x-developer-replay",
            "case_title": "X-Developer Replay",
            "ontology_version": "1.0",
        },
        "tbox": {
            "concepts": ["DataDrivenManagementActor", "decision_support"],
            "relations": ["has_capability", "competes_with"],
            "axioms": [{"id": "axiom_1", "statement": "A competes_with B"}],
        },
        "abox": {
            "actors": [
                {
                    "actor_id": "xd_platform",
                    "concept": "DataDrivenManagementActor",
                }
            ],
        },
        "reasoning_profile": {
            "rules": [{"id": "axiom_1"}],
        },
    }

    package = validate_ontology_input_or_raise(payload)

    assert package.meta.version == "1.0"
    assert package.meta.domain == "X-Developer Replay"
    assert len(package.tbox.concepts) == 2
    assert len(package.tbox.relations) >= 1


def test_validate_ontology_input_accepts_custom_relation_names() -> None:
    payload = {
        "meta": {
            "version": "1.0",
            "case_id": "custom-relations",
            "domain": "management_ontology",
        },
        "tbox": {
            "concepts": [
                {"name": "StartupActor", "description": "", "category": "actor"},
                {"name": "MarketProblem", "description": "", "category": "other"},
                {"name": "GrowthOutcome", "description": "", "category": "outcome"},
            ],
            "relations": [
                {
                    "name": "addresses",
                    "source": "StartupActor",
                    "target": "MarketProblem",
                    "description": "startup addresses a market problem",
                },
                {
                    "name": "leads_to",
                    "source": "MarketProblem",
                    "target": "GrowthOutcome",
                    "description": "problem resolution leads to growth",
                },
            ],
            "axioms": [{"id": "ax-1", "statement": "sample", "type": "activation"}],
        },
        "abox": {
            "actors": [{"actor_id": "startup", "actor_type": "StartupActor"}],
        },
        "reasoning_profile": {"activation_rules": [{"rule_id": "ax-1"}]},
    }

    package = validate_ontology_input_or_raise(payload)

    relation_names = [relation.name for relation in package.tbox.relations]
    assert "addresses" in relation_names
    assert "leads_to" in relation_names


def test_validate_ontology_input_accepts_dual_space_ontology() -> None:
    payload = {
        "meta": {
            "version": "1.0",
            "case_id": "dual-space",
            "domain": "strategy",
        },
        "tbox": {
            "concepts": [
                {"name": "StartupActor", "description": "", "category": "actor"},
                {"name": "tech_capability", "description": "", "category": "capability"},
            ],
            "relations": [
                {
                    "name": "has_capability",
                    "source": "StartupActor",
                    "target": "tech_capability",
                    "description": "",
                }
            ],
            "axioms": [{"id": "ax-1", "statement": "sample", "type": "activation"}],
        },
        "abox": {
            "actors": [{"actor_id": "startup", "actor_type": "StartupActor"}],
            "capabilities": [{"actor_id": "startup", "name": "tech_capability", "score": 0.8}],
            "constraints": [],
        },
        "reasoning_profile": {"activation_rules": [{"rule_id": "ax-1"}]},
        "tech_space_ontology": {
            "actors": [{"actor_id": "startup"}],
            "capabilities": [{"name": "tech_capability", "score": 0.8}],
            "axioms": [{"id": "tax-1", "statement": "tech evolves"}],
        },
        "market_space_ontology": {
            "actors": [{"actor_id": "startup"}],
            "market_attributes": {"adoption_resistance": 0.7},
            "axioms": [{"id": "max-1", "statement": "resistance slows adoption"}],
        },
        "shared_actors": ["startup"],
    }

    package = validate_ontology_input_or_raise(payload)

    assert package.shared_actors == ["startup"]


def test_validate_ontology_input_rejects_missing_market_adoption_resistance() -> None:
    payload = {
        "meta": {
            "version": "1.0",
            "case_id": "dual-space-missing-attr",
            "domain": "strategy",
        },
        "tbox": {
            "concepts": [
                {"name": "StartupActor", "description": "", "category": "actor"},
                {"name": "tech_capability", "description": "", "category": "capability"},
            ],
            "relations": [
                {
                    "name": "has_capability",
                    "source": "StartupActor",
                    "target": "tech_capability",
                    "description": "",
                }
            ],
            "axioms": [{"id": "ax-1", "statement": "sample", "type": "activation"}],
        },
        "abox": {
            "actors": [{"actor_id": "startup", "actor_type": "StartupActor"}],
            "capabilities": [{"actor_id": "startup", "name": "tech_capability", "score": 0.8}],
            "constraints": [],
        },
        "reasoning_profile": {"activation_rules": [{"rule_id": "ax-1"}]},
        "tech_space_ontology": {
            "actors": [{"actor_id": "startup"}],
            "capabilities": [{"name": "tech_capability", "score": 0.8}],
            "axioms": [{"id": "tax-1", "statement": "tech evolves"}],
        },
        "market_space_ontology": {
            "actors": [{"actor_id": "startup"}],
            "axioms": [{"id": "max-1", "statement": "resistance slows adoption"}],
        },
        "shared_actors": ["startup"],
    }

    with pytest.raises(OntologyValidationError) as exc:
        validate_ontology_input_or_raise(payload)

    assert any(issue.code == "missing_market_adoption_resistance" for issue in exc.value.issues)


def test_validate_ontology_input_autofixes_capability_constraint_mismatch() -> None:
    payload = {
        "meta": {
            "version": "1.0",
            "case_id": "autofix-mismatch",
            "domain": "strategy",
        },
        "tbox": {
            "concepts": [
                {"name": "StartupActor", "description": "", "category": "actor"},
                {"name": "analytics", "description": "", "category": "capability"},
                {
                    "name": "process_compliance_burden",
                    "description": "",
                    "category": "constraint",
                },
            ],
            "relations": [
                {
                    "name": "has_capability",
                    "source": "StartupActor",
                    "target": "analytics",
                    "description": "",
                }
            ],
            "axioms": [{"id": "ax-1", "statement": "sample", "type": "activation"}],
        },
        "abox": {
            "actors": [{"actor_id": "startup", "actor_type": "StartupActor"}],
            "capabilities": [
                {"actor_id": "startup", "name": "analytics", "score": 0.8},
                {
                    "actor_id": "startup",
                    "name": "process_compliance_burden",
                    "score": 0.75,
                },
            ],
            "constraints": [],
        },
        "reasoning_profile": {"activation_rules": [{"rule_id": "ax-1"}]},
    }

    with pytest.warns(UserWarning, match="Auto-fix"):
        package = validate_ontology_input_or_raise(payload)

    capability_names = [item.name for item in package.abox.capabilities]
    assert "process_compliance_burden" not in capability_names

    constraint_names = [item.name for item in package.abox.constraints]
    assert "process_compliance_burden" in constraint_names


def test_validate_ontology_input_autofixes_legacy_event_shape() -> None:
    payload = {
        "meta": {
            "version": "1.0",
            "case_id": "legacy-event-shape",
            "domain": "strategy",
        },
        "tbox": {
            "concepts": [
                {"name": "StartupActor", "description": "", "category": "actor"},
                {"name": "analytics", "description": "", "category": "capability"},
            ],
            "relations": [
                {
                    "name": "has_capability",
                    "source": "StartupActor",
                    "target": "analytics",
                    "description": "",
                }
            ],
            "axioms": [{"id": "ax-1", "statement": "sample", "type": "activation"}],
        },
        "abox": {
            "actors": [{"actor_id": "startup", "actor_type": "StartupActor"}],
            "capabilities": [{"actor_id": "startup", "name": "analytics", "score": 0.8}],
            "events": [
                {
                    "event_id": "xdev-1",
                    "time": "2019-10",
                    "event": "launch",
                    "description": "launch event",
                    "evidence_refs": ["src-1"],
                }
            ],
        },
        "reasoning_profile": {"activation_rules": [{"rule_id": "ax-1"}]},
    }

    with pytest.warns(UserWarning, match="legacy abox.events"):
        package = validate_ontology_input_or_raise(payload)

    assert len(package.abox.events) == 1
    assert package.abox.events[0].event_type == "launch"
    assert package.abox.events[0].payload.get("event_id") == "xdev-1"
