import json
import sys
from pathlib import Path

from omen.cli.main import main


ROOT = Path(__file__).resolve().parents[2]
SCENARIO_PATH = ROOT / "data" / "scenarios" / "ontology.json"


def test_cli_precision_eval_writes_repeatability_payload(tmp_path: Path, monkeypatch) -> None:
    output_path = tmp_path / "precision.json"
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
            str(output_path),
        ],
    )

    main()

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["runs"] == 3
    assert payload["repeatability"]["run_count"] == 3
    assert payload["repeatability"]["outcome_consistency"] >= 0.9
