"""Scenario loader for ontology battle simulation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from omen.ingest.synthesizer.builders.situation import (
    scenario_ontology_to_markdown,
    situation_artifact_to_markdown,
)
from omen.ingest.validators.scenario import (
    ScenarioConfig,
    validate_case_package_or_raise,
    validate_scenario_ontology_slice_or_raise,
    validate_scenario_or_raise,
)
from omen.ingest.validators.situation import validate_situation_artifact_or_raise
from omen.ingest.validators.strategy import validate_ontology_input_or_raise
from omen.scenario.ontology_loader import bind_ontology_to_scenario, load_ontology_input
from omen.types import CasePackage


def load_scenario(path: str | Path) -> ScenarioConfig:
    scenario_path = Path(path)
    with scenario_path.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    return validate_scenario_or_raise(payload)


def load_case_package(path: str | Path) -> CasePackage:
    package_path = Path(path)
    with package_path.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    return validate_case_package_or_raise(payload, base_dir=package_path.parent.parent)


def load_case_package_from_scenario(path: str | Path) -> CasePackage:
    scenario_path = Path(path)
    with scenario_path.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    case_package_payload = payload.get("case_package")
    if not isinstance(case_package_payload, dict):
        raise ValueError("scenario missing `case_package` object")

    return validate_case_package_or_raise(case_package_payload, base_dir=scenario_path.parent.parent.parent)


def load_scenario_with_ontology(
    scenario_path: str | Path,
    ontology_path: str | Path | None = None,
) -> tuple[ScenarioConfig, dict[str, Any] | None]:
    scenario_path = Path(scenario_path)
    with scenario_path.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    scenario = validate_scenario_or_raise(payload)

    ontology = None
    if ontology_path is not None:
        ontology = load_ontology_input(ontology_path)
    elif isinstance(payload, dict) and all(key in payload for key in ("meta", "tbox", "abox")):
        ontology = validate_ontology_input_or_raise(payload)

    if ontology is None:
        return scenario, None

    ontology_metadata = bind_ontology_to_scenario(ontology, scenario)
    return scenario, ontology_metadata


def load_scenario_ontology_slice(path: str | Path) -> dict[str, Any]:
    scenario_path = Path(path)
    with scenario_path.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    validated = validate_scenario_ontology_slice_or_raise(payload)
    return validated.model_dump()


def save_scenario_ontology_slice(path: str | Path, payload: dict[str, Any]) -> Path:
    output_path = Path(path)
    validated = validate_scenario_ontology_slice_or_raise(payload)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(validated.model_dump(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return output_path


def save_scenario_ontology_markdown(path: str | Path, payload: dict[str, Any]) -> Path:
    output_path = Path(path)
    validated = validate_scenario_ontology_slice_or_raise(payload)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    markdown = scenario_ontology_to_markdown(validated.model_dump())
    output_path.write_text(markdown, encoding="utf-8")
    return output_path


def load_situation_artifact(path: str | Path) -> dict[str, Any]:
    situation_path = Path(path)
    with situation_path.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    validated = validate_situation_artifact_or_raise(payload)
    return validated.model_dump()


def save_situation_artifact(path: str | Path, payload: dict[str, Any]) -> Path:
    output_path = Path(path)
    validated = validate_situation_artifact_or_raise(payload)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(validated.model_dump(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return output_path


def save_situation_markdown(path: str | Path, payload: dict[str, Any], config_path: str = "config/llm.toml") -> Path:
    output_path = Path(path)
    validated = validate_situation_artifact_or_raise(payload)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    markdown = situation_artifact_to_markdown(validated.model_dump(), config_path=config_path)
    output_path.write_text(markdown, encoding="utf-8")
    return output_path


def save_auxiliary_json(path: str | Path, payload: dict[str, Any]) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return output_path


def resolve_situation_artifact_ref(ref: str | Path) -> Path:
    raw = str(ref).strip()
    if not raw:
        raise ValueError("empty situation reference")

    candidate = Path(raw)
    if candidate.exists():
        return candidate

    root_candidate = Path("data/scenarios") / raw / "situation.json"
    if root_candidate.exists():
        return root_candidate

    # Backward compatibility for legacy artifact layout.
    return Path("data/scenarios") / raw / "generation" / "situation.json"


def resolve_scenario_artifact_ref(ref: str | Path) -> Path:
    raw = str(ref).strip()
    if not raw:
        raise ValueError("empty scenario reference")

    candidate = Path(raw)
    if candidate.exists():
        return candidate

    return Path("data/scenarios") / raw / "scenario_pack.json"
