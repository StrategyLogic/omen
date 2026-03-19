"""Spec 6 baseline replay execution helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from omen.explain.report import build_explanation_report
from omen.scenario.case_replay_loader import load_case_replay_scenario
from omen.simulation.engine import run_simulation
from omen.simulation.replay import save_run_result
from omen.ui.artifacts import ensure_case_output_dir
from omen.ui.view_model import build_case_replay_view_model


def run_case_replay_baseline(
    *,
    case_id: str,
    ontology_path: str | Path,
    output_root: str | Path = "output/case_replay",
) -> dict[str, Any]:
    scenario, ontology_setup = load_case_replay_scenario(ontology_path=ontology_path)
    ontology_warnings = list(ontology_setup.get("ontology_warnings") or [])
    result = run_simulation(scenario, ontology_setup=ontology_setup)
    explanation = build_explanation_report(result)

    case_dir = ensure_case_output_dir(case_id=case_id, output_root=output_root)
    result_path = save_run_result(result, case_dir / "baseline_result.json")
    explanation_path = save_run_result(explanation, case_dir / "baseline_explanation.json")

    view_model = build_case_replay_view_model(result=result, explanation=explanation, case_id=case_id)
    view_model_path = save_run_result(view_model, case_dir / "view_model.json")

    return {
        "result": result,
        "explanation": explanation,
        "view_model": view_model,
        "ontology_warnings": ontology_warnings,
        "paths": {
            "result": str(result_path),
            "explanation": str(explanation_path),
            "view_model": str(view_model_path),
        },
    }
