from pathlib import Path

from omen.ingest.synthesizer.services.situation import (
    _compute_dual_confidence,
    build_situation_confidence_trace,
)


def test_compute_dual_confidence_derives_risk_and_overall_metrics() -> None:
    result = _compute_dual_confidence(
        context={
            "known_unknowns": [
                "u1",
                "u2",
                "u3",
                "u4",
            ]
        },
        uncertainty_space={
            "assumptions_explicit": [
                {
                    "target_unknown": "u1",
                    "assumption_text": "a1",
                    "quality_score": 0.9,
                },
                {
                    "target_unknown": "u2",
                    "assumption_text": "a2",
                    "quality_score": 0.9,
                },
                {
                    "target_unknown": "u3",
                    "assumption_text": "a3",
                    "quality_score": 0.9,
                },
                {
                    "target_unknown": "u4",
                    "assumption_text": "a4",
                    "quality_score": 0.9,
                },
            ]
        },
    )

    assert result["confidence_risk"] == 0.4
    assert result["coverage_ratio"] == 0.9
    assert result["confidence_overall"] == 0.9
    assert result["metrics"]["known_unknowns_count"] == 4
    assert result["metrics"]["assumptions_filled_count"] == 4
    assert result["guardrail_applied"] is True


def test_build_situation_confidence_trace_contains_generation_style_fields() -> None:
    situation_artifact = {
        "id": "nokia-elop-2010",
        "source_meta": {
            "source_path": "cases/situations/nokia-elop-2010.md",
            "pack_id": "nokia_v1",
            "pack_version": "1.0.0",
            "generated_at": "2026-04-05T12:00:00",
        },
        "uncertainty_space": {
            "confidence_risk": 0.4,
            "confidence_overall": 0.94,
            "overall_confidence": 0.94,
            "guardrail_applied": False,
            "metrics": {
                "known_unknowns_count": 4,
                "assumptions_filled_count": 4,
                "assumptions_quality_avg": 0.9,
                "cognitive_coverage": 0.9,
            },
            "assumptions_explicit": [
                {
                    "target_unknown": "u1",
                    "assumption_text": "a1",
                    "quality_score": 0.9,
                }
            ],
        },
    }

    trace = build_situation_confidence_trace(
        situation_artifact=situation_artifact,
        situation_artifact_path=Path("data/scenarios/nokia_v1/nokia-elop-2010_situation.json"),
    )

    assert trace["artifact_type"] == "situation_generation_trace"
    assert trace["situation_id"] == "nokia-elop-2010"
    assert trace["validation_passed"] is True
    assert trace["confidence"]["confidence_risk"] == 0.4
    assert trace["confidence"]["confidence_overall"] == 0.94
    assert trace["metrics"]["cognitive_coverage"] == 0.9