import json
import sys
from pathlib import Path

import pytest

from omen.cli.main import main


ROOT = Path(__file__).resolve().parents[2]
SCENARIO_PATH = ROOT / "data" / "scenarios" / "ontology.json"


def test_simulate_rejects_removed_local_nl_compile_flag(tmp_path: Path, monkeypatch) -> None:
    payload_path = tmp_path / "deferred_dynamic.json"
    payload_path.write_text(
        json.dumps(
            {
                "pack_id": "strategic_actor_nokia_v1",
                "pack_version": "1.0.0",
                "case_id": "nokia_elop",
                "dynamic_authoring": {"enabled": True},
                "scenarios": [
                    {"slot": "A", "title": "A", "description": "valid description for scenario A"},
                    {"slot": "B", "title": "B", "description": "valid description for scenario B"},
                    {"slot": "C", "title": "C", "description": "valid description for scenario C"},
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "omen",
            "simulate",
            "--scenario",
            str(SCENARIO_PATH),
            "--deterministic-nl-json",
            str(payload_path),
        ],
    )

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 2
