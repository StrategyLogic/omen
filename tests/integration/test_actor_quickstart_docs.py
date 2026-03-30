from __future__ import annotations

from pathlib import Path


def test_quickstart_contains_actor_commands() -> None:
    path = Path("specs/007-founder-opensource/quickstart.md")
    content = path.read_text(encoding="utf-8")
    assert "omen analyze actor --doc" in content
    assert "omen validate actor --doc" in content
    assert "streamlit run app/strategic_actor.py" in content
