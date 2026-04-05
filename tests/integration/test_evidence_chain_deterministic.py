from omen.analysis.actor.insight import (
    apply_contradiction_confidence_flag,
    map_major_conclusions_to_evidence,
)
from omen.analysis.actor.query import normalize_deterministic_evidence_records


def test_deterministic_evidence_chain_mapping() -> None:
    evidence = normalize_deterministic_evidence_records(
        [
            {
                "evidence_id": "e1",
                "source_label": "memo",
                "source_timestamp": "2010-01-01",
                "claim_excerpt": "example",
                "evidence_strength": "strong",
            }
        ]
    )
    mapped = map_major_conclusions_to_evidence(
        [{"text": "conclusion", "evidence_refs": ["e1"]}],
        evidence,
    )

    assert len(mapped) == 1
    assert mapped[0]["conclusion"] == "conclusion"
    assert len(mapped[0]["evidence_items"]) == 1


def test_deterministic_conflict_reduces_confidence() -> None:
    flag = apply_contradiction_confidence_flag(
        [
            {"evidence_id": "e1", "contradiction_group": "g1"},
            {"evidence_id": "e2", "contradiction_group": "g1"},
        ]
    )
    assert flag == "reduced-confidence"
