from __future__ import annotations

from omen.scenario.validator import format_validation_report


def test_actor_validator_report_pass() -> None:
    report = format_validation_report(target_artifact="output/actors/xd", errors=[])
    assert report["status"] == "pass"
    assert report["errors"] == []


def test_actor_validator_report_fail() -> None:
    report = format_validation_report(
        target_artifact="output/actors/xd/actor_ontology.json",
        errors=[{"field": "meta", "reason": "missing object"}],
    )
    assert report["status"] == "fail"
    assert len(report["errors"]) == 1
