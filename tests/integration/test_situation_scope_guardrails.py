import sys
from pathlib import Path

import pytest

from omen.cli.main import main


def test_analyze_situation_rejects_deferred_dynamic_authoring(tmp_path: Path, monkeypatch, capsys) -> None:
    deferred_source = tmp_path / "deferred_dynamic.md"
    deferred_source.write_text(
        """
# Deferred Dynamic Example

company current state: transition phase

dynamic_authoring: enabled
""".strip(),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "omen",
            "analyze",
            "situation",
            "--input",
            str(deferred_source),
            "--actor",
            "actors/steve-jobs.md",
            "--output",
            str(tmp_path / "unused.json"),
        ],
    )

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 2
    out = capsys.readouterr().out
    assert "Deferred scope:" in out
    assert "Dynamic scenario authoring and enterprise resistance extensions are deferred." in out
