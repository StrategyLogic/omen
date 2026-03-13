import json
import sys
from pathlib import Path

from omen.cli.main import main


ROOT = Path(__file__).resolve().parents[2]
SCENARIO_PATH = ROOT / "data" / "scenarios" / "ontology.json"


def test_precision_gate_report_generation(tmp_path: Path, monkeypatch) -> None:
    profile_path = tmp_path / "profile.json"
    profile_path.write_text(
        json.dumps(
            {
                "profile_id": "p-ontology",
                "case_id": "ontology",
                "repeatability_threshold": 0.9,
                "directional_correctness_threshold": 0.85,
                "trace_completeness_threshold": 0.95,
                "status": "active",
            }
        ),
        encoding="utf-8",
    )

    precision_path = tmp_path / "precision.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "omen",
            "precision-eval",
            "--scenario",
            str(SCENARIO_PATH),
            "--runs",
            "3",
            "--seed",
            "42",
            "--output",
            str(precision_path),
        ],
    )
    main()

    comparison_path = tmp_path / "comparison.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "omen",
            "compare",
            "--scenario",
            str(SCENARIO_PATH),
            "--overrides",
            '{"user_overlap_threshold": 0.9}',
            "--output",
            str(comparison_path),
        ],
    )
    main()

    report_path = tmp_path / "gate_report.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "omen",
            "precision-gate",
            "--profile-json",
            str(profile_path),
            "--precision-json",
            str(precision_path),
            "--comparison-json",
            str(comparison_path),
            "--output",
            str(report_path),
        ],
    )
    main()

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["governance"]["profile"]["profile_id"] == "p-ontology"
    assert report["governance"]["gate_evaluation"]["status"] in {"passed", "failed"}
    assert "repeatability" in report["evidence"]
