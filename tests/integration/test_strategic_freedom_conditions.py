import json
import sys
from pathlib import Path

from omen.cli.main import main


ROOT = Path(__file__).resolve().parents[2]
SCENARIO_PATH = ROOT / "data" / "scenarios" / "ontology.json"
NL_INPUT_PATH = ROOT / "tests" / "fixtures" / "scenario_compilation" / "nokia_nl_scenarios.json"


def test_deterministic_compare_contains_actionable_condition_sets(tmp_path: Path, monkeypatch) -> None:
    output_path = tmp_path / "det_compare.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "omen",
            "compare",
            "--scenario",
            str(SCENARIO_PATH),
            "--deterministic-nl-json",
            str(NL_INPUT_PATH),
            "--output",
            str(output_path),
        ],
    )

    main()

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    results = list(payload.get("scenario_results") or [])
    assert len(results) == 3

    for item in results:
        freedom = item.get("strategic_freedom") or {}
        assert "score" in freedom
        assert "required" in freedom
        assert "warning" in freedom
        assert "blocking" in freedom
        assert isinstance(freedom["required"], list)
        assert isinstance(freedom["warning"], list)
        assert isinstance(freedom["blocking"], list)

    overview = list(payload.get("strategic_freedom_overview") or [])
    assert len(overview) == 3
    assert all("strategic_freedom_score" in row for row in overview)
