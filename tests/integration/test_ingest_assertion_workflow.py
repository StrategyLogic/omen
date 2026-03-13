import json
import sys
from pathlib import Path

from omen.cli.main import main


ROOT = Path(__file__).resolve().parents[2]
SCENARIO_PATH = ROOT / "data" / "scenarios" / "ontology.json"


def test_cli_ingest_dry_run_with_assertion_generation(tmp_path: Path, monkeypatch) -> None:
    text_path = tmp_path / "sample.txt"
    text_path.write_text(
        "AIMemoryActor and DatabaseActor both appear in this paragraph to trigger conflict mapping.",
        encoding="utf-8",
    )

    output_path = tmp_path / "ingest_assertions.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "omen",
            "ingest-dry-run",
            "--scenario",
            str(SCENARIO_PATH),
            "--text-file",
            str(text_path),
            "--build-assertions",
            "--output",
            str(output_path),
        ],
    )

    main()

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["assertion_count"] >= 1
    assert payload["assertion_review_summary"]["rejected"] >= 1
    assert isinstance(payload["assertions"], list)
