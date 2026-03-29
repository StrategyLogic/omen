from __future__ import annotations

import copy

from omen.analysis.founder.loader import validate_founder_ref
from omen.ingest.llm_ontology.founder_builder import founder_hash


def test_validate_founder_ref_does_not_mutate_strategy_or_founder_payloads() -> None:
    founder_ontology = {
        "meta": {"case_id": "xd"},
        "actors": [{"id": "founder-1", "type": "founder", "name": "Founder X"}],
        "events": [],
    }
    strategy_ontology = {
        "meta": {"case_id": "xd"},
        "founder_ref": {
            "path": "founder_ontology.json",
            "hash": founder_hash(founder_ontology),
        },
    }

    strategy_before = copy.deepcopy(strategy_ontology)
    founder_before = copy.deepcopy(founder_ontology)

    validate_founder_ref(strategy_ontology, founder_ontology)

    assert strategy_ontology == strategy_before
    assert founder_ontology == founder_before
