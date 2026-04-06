"""Load and validate scenario planning template files."""

from __future__ import annotations

from pathlib import Path

import yaml

from omen.scenario.models import ScenarioPlanningRuleTemplateModel


def load_planning_template(path: str | Path = "config/templates/planning.yaml") -> ScenarioPlanningRuleTemplateModel:
    template_path = Path(path)
    if not template_path.is_absolute() and not template_path.exists():
        repo_root = Path(__file__).resolve().parents[3]
        template_path = repo_root / template_path
    payload = yaml.safe_load(template_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("planning template must be a YAML object")
    return ScenarioPlanningRuleTemplateModel.model_validate(payload)
