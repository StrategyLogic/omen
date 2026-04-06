import json
import sys
from pathlib import Path

import pytest

from omen.cli.main import main


ROOT = Path(__file__).resolve().parents[2]
NL_INPUT_PATH = ROOT / "tests" / "fixtures" / "scenario_compilation" / "nokia_nl_scenarios.json"


def test_analyze_actor_compile_pack_removed(tmp_path: Path, monkeypatch) -> None:
    output_path = tmp_path / "compiled_pack.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "omen",
            "analyze",
            "actor",
            "compile-pack",
            "--nl-json",
            str(NL_INPUT_PATH),
            "--output",
            str(output_path),
        ],
    )

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 2
    assert not output_path.exists()


def test_analyze_actor_compile_pack_ambiguous_failure(tmp_path: Path, monkeypatch) -> None:
    bad_payload_path = tmp_path / "ambiguous.json"
    bad_payload_path.write_text(
        json.dumps(
            {
                "pack_id": "strategic_actor_nokia_v1",
                "pack_version": "1.0.0",
                "case_id": "nokia_elop",
                "scenarios": [
                    {
                        "slot": "A",
                        "title": "too-short",
                        "description": "short",
                    },
                    {
                        "slot": "B",
                        "title": "ok",
                        "description": "this is a valid description for B path",
                    },
                    {
                        "slot": "C",
                        "title": "ok",
                        "description": "this is a valid description for C path",
                    },
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
            "analyze",
            "actor",
            "compile-pack",
            "--nl-json",
            str(bad_payload_path),
        ],
    )

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 2
