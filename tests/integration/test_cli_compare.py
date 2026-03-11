import json
import sys
from pathlib import Path

from omen.cli.main import main


ROOT = Path(__file__).resolve().parents[2]
SCENARIO_PATH = ROOT / "data" / "scenarios" / "ontology.json"


def test_cli_compare_writes_comparison_json(tmp_path: Path, monkeypatch) -> None:
    output_path = tmp_path / "comparison.json"
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
            str(output_path),
        ],
    )

    main()

    comparison = json.loads(output_path.read_text(encoding="utf-8"))
    assert "baseline_run_id" in comparison
    assert "variation_run_id" in comparison
    assert "deltas" in comparison
    assert "explanation" in comparison
    assert isinstance(comparison["deltas"], list)
