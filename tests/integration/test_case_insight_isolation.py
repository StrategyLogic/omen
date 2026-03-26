import json
import sys
from pathlib import Path

from omen.cli.main import main


def _write_founder_artifact(case_root: Path, founder_name: str) -> None:
    case_root.mkdir(parents=True, exist_ok=True)
    founder_payload = {
        "actors": [
            {
                "id": f"actor_{founder_name.lower()}",
                "type": "founder",
                "name": founder_name,
                "profile": {
                    "mental_patterns": {
                        "core_beliefs": ["automation first", "long-term leverage"],
                    },
                    "strategic_style": {
                        "decision_style": "evidence-based",
                        "non_negotiables": ["engineering quality"],
                    },
                },
            }
        ]
    }
    (case_root / "founder_ontology.json").write_text(
        json.dumps(founder_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def test_analyze_insight_is_isolated_between_cases(tmp_path: Path, monkeypatch) -> None:
    output_root = tmp_path / "output" / "case_replay"

    _write_founder_artifact(output_root / "xd", "Founder XD")
    _write_founder_artifact(output_root / "shenda", "Founder SHENDA")

    monkeypatch.chdir(tmp_path)

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "omen",
            "case",
            "analyze",
            "insight",
            "--case-id",
            "xd",
            "--output-dir",
            str(output_root),
        ],
    )
    assert main() == 0

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "omen",
            "case",
            "analyze",
            "insight",
            "--case-id",
            "shenda",
            "--output-dir",
            str(output_root),
        ],
    )
    assert main() == 0

    xd_payload = json.loads((output_root / "xd" / "analyze_insight.json").read_text(encoding="utf-8"))
    shenda_payload = json.loads((output_root / "shenda" / "analyze_insight.json").read_text(encoding="utf-8"))

    assert xd_payload["query"]["case_id"] == "xd"
    assert shenda_payload["query"]["case_id"] == "shenda"

    assert len(xd_payload["why_chain"]) >= 3
    assert len(shenda_payload["why_chain"]) >= 3

    assert len((xd_payload.get("gap_analysis") or {}).get("process_gaps") or []) >= 3
    assert len((shenda_payload.get("gap_analysis") or {}).get("process_gaps") or []) >= 3

    for payload in (xd_payload, shenda_payload):
        for why_item in payload.get("why_chain") or []:
            assert "question" in why_item
            assert "answer" in why_item
            assert "evidence_refs" in why_item

        for gap in (payload.get("gap_analysis") or {}).get("process_gaps") or []:
            assert "assumption" in gap
            assert "observation" in gap
            assert "gap_significance" in gap

        for gap in (payload.get("gap_analysis") or {}).get("outcome_gaps") or []:
            assert "assumption" in gap
            assert "observation" in gap
            assert "gap_significance" in gap
