import json
import sys
from pathlib import Path

from omen.cli.main import main


ROOT = Path(__file__).resolve().parents[2]
SCENARIO_PATH = ROOT / "data" / "scenarios" / "ontology.json"


def test_cli_ingest_dry_run_generates_candidates(tmp_path: Path, monkeypatch) -> None:
    text_path = tmp_path / "sample.txt"
    text_path.write_text(
        "AIMemoryActor appears in this scenario.",
        encoding="utf-8",
    )

    output_path = tmp_path / "ingest_candidates.json"
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
            "--output",
            str(output_path),
        ],
    )

    main()

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["candidate_count"] >= 1
    assert payload["mapped_count"] >= 1
    assert payload["source_inventory"]["source_dir"].endswith("data/ingest/sources")
    assert isinstance(payload["candidates"], list)
