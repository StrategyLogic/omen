from omen.ingest.models import PrecisionEvaluationProfile
from omen.simulation.precision_gate import evaluate_precision_gates


def test_precision_gate_passes_when_all_metrics_meet_thresholds() -> None:
    profile = PrecisionEvaluationProfile(
        profile_id="p-1",
        case_id="ontology",
        repeatability_threshold=0.9,
        directional_correctness_threshold=0.85,
        trace_completeness_threshold=0.95,
        status="active",
    )

    report = evaluate_precision_gates(
        profile,
        repeatability_metrics={"outcome_consistency": 1.0, "top_driver_consistency": 0.95},
        directional_metrics={"directional_correctness": 0.9},
        trace_metrics={"trace_completeness": 0.95},
    )

    assert report["status"] == "passed"
    assert report["failed_gate_count"] == 0


def test_precision_gate_reports_remediation_targets() -> None:
    profile = PrecisionEvaluationProfile(
        profile_id="p-2",
        case_id="ontology",
        repeatability_threshold=0.9,
        directional_correctness_threshold=0.85,
        trace_completeness_threshold=0.95,
        status="active",
    )

    report = evaluate_precision_gates(
        profile,
        repeatability_metrics={"outcome_consistency": 0.6, "top_driver_consistency": 0.7},
        directional_metrics={"directional_correctness": 0.8},
        trace_metrics={"trace_completeness": 0.5},
    )

    assert report["status"] == "failed"
    assert report["failed_gate_count"] == 3
    assert len(report["remediation_targets"]) == 3
