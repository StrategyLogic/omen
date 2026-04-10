"""Scenario schema validation for ontology battle MVP."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from omen.ingest.synthesizer.schema import VERSION as ACTOR_SCHEMA_VERSION
from omen.scenario.ingest_validator import (
    DeferredScopeFeatureError,
    IncompleteDeterministicPackError,
)
from omen.ingest.models import DeterministicScenarioPackModel
from omen.ingest.models import ScenarioOntologySliceModel
from omen.types import CasePackage, RuntimeSupportDeclaration
from omen.simulation.step import is_action_known


class CapabilityDimension(BaseModel):
    name: str = Field(min_length=1)
    weight: float = Field(gt=0.0)


class ActorConfig(BaseModel):
    actor_id: str = Field(min_length=1)
    actor_type: str
    budget: float = Field(ge=0.0)
    initial_user_base: int = Field(ge=0)
    available_actions: list[str] = Field(min_length=1)
    functional_profile: dict[str, float] = Field(min_length=1)

    @field_validator("available_actions")
    @classmethod
    def available_actions_must_be_known(cls, value: list[str]) -> list[str]:
        unknown = [a for a in value if not is_action_known(a)]
        if unknown:
            raise ValueError(f"unknown action(s): {unknown}")
        return value

    @field_validator("functional_profile")
    @classmethod
    def profile_values_between_zero_and_one(cls, value: dict[str, float]) -> dict[str, float]:
        invalid = {k: v for k, v in value.items() if v < 0.0 or v > 1.0}
        if invalid:
            raise ValueError(f"functional_profile values must be in [0,1], got {invalid}")
        return value


class ScenarioConfig(BaseModel):
    scenario_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    time_steps: int = Field(ge=1, le=1000)
    seed: int | None = None
    random_perturbation: float = Field(default=0.1, ge=0.0, le=1.0)
    user_overlap_threshold: float = Field(default=0.2, ge=0.0, le=1.0)
    actors: list[ActorConfig] = Field(min_length=2)
    capabilities: list[CapabilityDimension] = Field(min_length=1)

    @model_validator(mode="after")
    def actor_ids_unique(self) -> "ScenarioConfig":
        ids = [a.actor_id for a in self.actors]
        if len(ids) != len(set(ids)):
            raise ValueError("actor_id must be unique")
        return self


def validate_scenario(payload: dict) -> ScenarioConfig:
    return ScenarioConfig.model_validate(payload)


def validate_scenario_or_raise(payload: dict) -> ScenarioConfig:
    return validate_scenario(payload)


def is_scenario_ontology_input_payload(payload: Any) -> bool:
    return (
        isinstance(payload, dict)
        and "pack_id" in payload
        and "scenarios" in payload
        and ("ontology_version" in payload or "derived_from_situation_id" in payload)
    )


def is_scenario_ontology_input_path(path: str | Path) -> bool:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return False
    return is_scenario_ontology_input_payload(payload)


class ResultArtifactContract(BaseModel):
    scenario_id: str = Field(min_length=1)
    outcome_class: str = Field(min_length=1)
    winner: dict | None = None
    timeline: list
    ontology_setup: dict | None = None
    explanation: dict | None = None


class ExplanationArtifactContract(BaseModel):
    branch_points: list
    causal_chain: list
    narrative_summary: str | None = None
    applied_axioms: dict | None = None
    rule_trace_references: list | None = None


class SemanticConditionObject(BaseModel):
    description: str = Field(min_length=1)
    type: str | None = None
    semantic_type: str | None = None
    category: str | None = None


class ComparisonArtifactContract(BaseModel):
    baseline_outcome_class: str = Field(min_length=1)
    variation_outcome_class: str = Field(min_length=1)
    conditions: list[SemanticConditionObject] = Field(default_factory=list)
    deltas: list


class CrossCaseOutputContract(BaseModel):
    result_artifact: ResultArtifactContract
    explanation_artifact: ExplanationArtifactContract
    comparison_artifact: ComparisonArtifactContract


def validate_runtime_support_or_raise(payload: dict) -> RuntimeSupportDeclaration:
    return RuntimeSupportDeclaration.model_validate(payload)


def _resolve_existing_path(base_dir: Path, relative_or_abs: str) -> Path:
    path = Path(relative_or_abs)
    candidate = path if path.is_absolute() else base_dir / path
    return candidate.resolve()


def validate_case_package_or_raise(
    payload: dict,
    *,
    base_dir: str | Path | None = None,
) -> CasePackage:
    package = CasePackage.model_validate(payload)
    if base_dir is None:
        return package

    base = Path(base_dir).resolve()
    required_paths = [
        package.scenario_file,
        package.case_doc_file,
        package.manifest.scenario_entry,
        package.manifest.narrative_entry,
        *package.required_artifacts,
    ]
    missing = [
        rel
        for rel in required_paths
        if not _resolve_existing_path(base, rel).exists()
    ]
    if missing:
        raise ValueError(f"case package references missing artifact(s): {missing}")

    return package

def validate_cross_case_output_contract_or_raise(payload: dict) -> CrossCaseOutputContract:
    return CrossCaseOutputContract.model_validate(payload)


def format_validation_report(*, target_artifact: str, errors: list[dict]) -> dict:
    return {
        "status": "pass" if not errors else "fail",
        "target_artifact": target_artifact,
        "schema_version": ACTOR_SCHEMA_VERSION,
        "errors": errors,
        "warnings": [],
    }


def validate_deterministic_scenario_pack_or_raise(
    payload: dict,
    *,
    required_slots: tuple[str, ...] = ("A", "B", "C"),
) -> DeterministicScenarioPackModel:
    for key in (
        "enterprise_resistance_extensions",
        "enterprise_template_catalog",
        "resistance_extension_profiles",
    ):
        if key in payload:
            raise DeferredScopeFeatureError(
                f"`{key}` is deferred scope. Enterprise resistance extensions are not supported in this release."
            )

    for index, scenario in enumerate(payload.get("scenarios") or []):
        if not isinstance(scenario, dict):
            continue
        deferred_keys = [
            key
            for key in (
                "custom_resistance_dimensions",
                "enterprise_resistance_profile",
                "department_resistance_breakdown",
            )
            if key in scenario
        ]
        if deferred_keys:
            raise DeferredScopeFeatureError(
                f"scenario index {index} uses deferred enterprise resistance keys: {deferred_keys}."
            )

    pack = DeterministicScenarioPackModel.model_validate(payload)
    existing = {scenario.scenario_key for scenario in pack.scenarios}
    missing = [slot for slot in required_slots if slot not in existing]
    if missing:
        raise IncompleteDeterministicPackError(
            f"deterministic scenario pack missing required slots: {missing}"
        )

    for scenario in pack.scenarios:
        if not scenario.target_outcome.strip():
            raise IncompleteDeterministicPackError(
                f"scenario {scenario.scenario_key} missing target_outcome"
            )
        if not scenario.constraints:
            raise IncompleteDeterministicPackError(
                f"scenario {scenario.scenario_key} missing constraints"
            )
        if not scenario.dilemma_tradeoffs:
            raise IncompleteDeterministicPackError(
                f"scenario {scenario.scenario_key} missing dilemma_tradeoffs"
            )

        if not any(item.strip() for item in scenario.constraints):
            raise IncompleteDeterministicPackError(
                f"scenario {scenario.scenario_key} constraints are empty after normalization"
            )
        if not any(item.strip() for item in scenario.dilemma_tradeoffs):
            raise IncompleteDeterministicPackError(
                f"scenario {scenario.scenario_key} dilemma_tradeoffs are empty after normalization"
            )
    return pack


def validate_scenario_ontology_slice_or_raise(
    payload: dict,
    *,
    required_slots: tuple[str, ...] = ("A", "B", "C"),
) -> ScenarioOntologySliceModel:
    for key in (
        "enterprise_resistance_extensions",
        "enterprise_template_catalog",
        "resistance_extension_profiles",
    ):
        if key in payload:
            raise DeferredScopeFeatureError(
                f"`{key}` is deferred scope. Enterprise resistance extensions are not supported in this release."
            )

    for index, scenario in enumerate(payload.get("scenarios") or []):
        if not isinstance(scenario, dict):
            continue
        deferred_keys = [
            key
            for key in (
                "custom_resistance_dimensions",
                "enterprise_resistance_profile",
                "department_resistance_breakdown",
            )
            if key in scenario
        ]
        if deferred_keys:
            raise DeferredScopeFeatureError(
                f"scenario index {index} uses deferred enterprise resistance keys: {deferred_keys}."
            )

    ontology = ScenarioOntologySliceModel.model_validate(payload)
    existing = {item.scenario_key for item in ontology.scenarios}
    missing = [slot for slot in required_slots if slot not in existing]
    if missing:
        raise IncompleteDeterministicPackError(
            f"scenario ontology missing required slots: {missing}"
        )

    ordered = [item.scenario_key for item in ontology.scenarios]
    if ordered != list(required_slots):
        raise IncompleteDeterministicPackError(
            f"scenario ontology must keep deterministic slot order {required_slots}, got {ordered}"
        )

    for scenario in ontology.scenarios:
        if not scenario.goal.strip():
            raise IncompleteDeterministicPackError(
                f"scenario {scenario.scenario_key} missing goal"
            )
        if not scenario.target.strip():
            raise IncompleteDeterministicPackError(
                f"scenario {scenario.scenario_key} missing target"
            )
        if not scenario.objective.strip():
            raise IncompleteDeterministicPackError(
                f"scenario {scenario.scenario_key} missing objective"
            )
        if not scenario.variables:
            raise IncompleteDeterministicPackError(
                f"scenario {scenario.scenario_key} missing variables"
            )
        if not any(item.strip() for item in scenario.constraints):
            raise IncompleteDeterministicPackError(
                f"scenario {scenario.scenario_key} constraints are empty after normalization"
            )
        if not any(item.strip() for item in scenario.tradeoff_pressure):
            raise IncompleteDeterministicPackError(
                f"scenario {scenario.scenario_key} tradeoff_pressure is empty after normalization"
            )
    return ontology


def validate_reason_chain_artifact_or_raise(payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("reason_chain artifact must be an object")
    if str(payload.get("artifact_type") or "") != "reason_chain":
        raise ValueError("reason_chain artifact_type must be `reason_chain`")

    rows = list(payload.get("scenario_chains") or [])
    if not rows:
        raise ValueError("reason_chain must contain non-empty scenario_chains")

    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("scenario_chain row must be an object")
        scenario_key = str(row.get("scenario_key") or "").strip()
        if scenario_key not in {"A", "B", "C"}:
            raise ValueError(f"invalid scenario_key in reason_chain row: {scenario_key}")

        reason_chain = row.get("reason_chain") or {}
        steps = list(reason_chain.get("steps") or [])
        if not steps:
            raise ValueError(f"reason_chain steps missing for scenario {scenario_key}")
        for step in steps:
            step_id = str((step or {}).get("step_id") or "").strip()
            if not step_id:
                raise ValueError(f"invalid step_id in scenario {scenario_key}: {step_id}")

        conclusions = reason_chain.get("conclusions") or {}
        for item in list(conclusions.get("blocking") or []):
            if not isinstance(item, dict):
                raise ValueError("blocking conclusion must be an object")
            if not list(item.get("activation_step_ids") or []):
                raise ValueError("blocking conclusion missing activation_step_ids")
            if not list(item.get("reason_step_ids") or []):
                raise ValueError("blocking conclusion missing reason_step_ids")

    return payload


def validate_reason_chain_view_model_artifact_or_raise(payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("reason_chain_view_model artifact must be an object")
    if str(payload.get("artifact_type") or "") != "reason_chain_view_model":
        raise ValueError("reason_chain_view_model artifact_type must be `reason_chain_view_model`")

    graph = payload.get("graph") or {}
    nodes = list(graph.get("nodes") or [])
    edges = list(graph.get("edges") or [])
    if not nodes:
        raise ValueError("reason_chain_view_model must contain graph.nodes")
    if not edges:
        raise ValueError("reason_chain_view_model must contain graph.edges")
    return payload


