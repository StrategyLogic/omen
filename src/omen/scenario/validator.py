"""Scenario schema validation for ontology battle MVP."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field, field_validator, model_validator

from omen.ingest.synthesizer.schema import VERSION as ACTOR_SCHEMA_VERSION
from omen.scenario.ingest_validator import (
    DeferredScopeFeatureError,
    IncompleteDeterministicPackError,
)
from omen.scenario.ontology_models import DeterministicScenarioPackModel
from omen.scenario.ontology_models import ScenarioOntologySliceModel
from omen.scenario.ontology_models import SituationArtifactModel
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


def validate_situation_artifact_or_raise(payload: dict) -> SituationArtifactModel:
    artifact = SituationArtifactModel.model_validate(payload)
    if artifact.version != "0.1.0":
        raise IncompleteDeterministicPackError(
            f"situation artifact version must be 0.1.0, got {artifact.version!r}"
        )
    if not artifact.signals:
        raise IncompleteDeterministicPackError("situation artifact missing signals")
    required_signal_fields = (
        "id",
        "name",
        "domain",
        "strength",
        "direction",
        "mapped_targets",
        "cascade_rules",
        "market_constraints",
        "mechanism_note",
    )
    allowed_domains = {"tech", "market", "capital", "standard", "policy"}
    allowed_impact_types = {"driver", "constraint", "amplifier", "dampener"}
    allowed_directions = {"up", "down", "mixed"}
    allowed_lags = {"short", "medium", "long"}
    required_conditions_by_type = {
        "driver": ("activation_condition", "expected_effect"),
        "constraint": ("binding_condition", "release_condition", "expected_effect"),
        "amplifier": ("modulation_target", "modulation_condition", "modulation_factor", "expected_effect"),
        "dampener": ("modulation_target", "modulation_condition", "modulation_factor", "expected_effect"),
    }

    for index, signal in enumerate(artifact.signals, start=1):
        for field in required_signal_fields:
            if field not in signal:
                raise IncompleteDeterministicPackError(
                    f"situation signal #{index} missing required field `{field}`"
                )
            value = signal.get(field)
            if value is None or value == "":
                raise IncompleteDeterministicPackError(
                    f"situation signal #{index} missing required field `{field}`"
                )

        domain = str(signal.get("domain") or "").strip()
        if domain not in allowed_domains:
            raise IncompleteDeterministicPackError(
                f"situation signal #{index} has invalid domain {domain!r}"
            )

        strength = signal.get("strength")
        if not isinstance(strength, (int, float)):
            raise IncompleteDeterministicPackError(
                f"situation signal #{index} strength must be numeric in [0,1]"
            )
        if float(strength) < 0.0 or float(strength) > 1.0:
            raise IncompleteDeterministicPackError(
                f"situation signal #{index} strength must be in [0,1]"
            )

        direction = str(signal.get("direction") or "").strip()
        if direction not in allowed_directions:
            raise IncompleteDeterministicPackError(
                f"situation signal #{index} has invalid direction {direction!r}"
            )

        mapped_targets = signal.get("mapped_targets")
        if not isinstance(mapped_targets, list) or not mapped_targets:
            raise IncompleteDeterministicPackError(
                f"situation signal #{index} mapped_targets must be a non-empty list"
            )
        for target_index, target in enumerate(mapped_targets, start=1):
            if not isinstance(target, dict):
                raise IncompleteDeterministicPackError(
                    f"situation signal #{index} mapped_target #{target_index} must be an object"
                )
            space = str(target.get("space") or "").strip()
            if space not in {"TechSpace", "MarketSpace"}:
                raise IncompleteDeterministicPackError(
                    f"situation signal #{index} mapped_target #{target_index} has invalid space {space!r}"
                )
            element_key = str(target.get("element_key") or "").strip()
            if not element_key:
                raise IncompleteDeterministicPackError(
                    f"situation signal #{index} mapped_target #{target_index} missing `element_key`"
                )
            impact_type = str(target.get("impact_type") or "").strip()
            if impact_type not in allowed_impact_types:
                raise IncompleteDeterministicPackError(
                    f"situation signal #{index} mapped_target #{target_index} has invalid impact_type {impact_type!r}"
                )
            impact_strength = target.get("impact_strength")
            if not isinstance(impact_strength, (int, float)):
                raise IncompleteDeterministicPackError(
                    f"situation signal #{index} mapped_target #{target_index} impact_strength must be numeric in [0,1]"
                )
            if float(impact_strength) < 0.0 or float(impact_strength) > 1.0:
                raise IncompleteDeterministicPackError(
                    f"situation signal #{index} mapped_target #{target_index} impact_strength must be in [0,1]"
                )

            mechanism_conditions = target.get("mechanism_conditions")
            if not isinstance(mechanism_conditions, dict):
                raise IncompleteDeterministicPackError(
                    f"situation signal #{index} mapped_target #{target_index} mechanism_conditions must be an object"
                )

            for field in required_conditions_by_type[impact_type]:
                value = mechanism_conditions.get(field)
                if field == "modulation_factor":
                    if not isinstance(value, (int, float)) or float(value) < 0.0 or float(value) > 1.0:
                        raise IncompleteDeterministicPackError(
                            f"situation signal #{index} mapped_target #{target_index} `{field}` must be numeric in [0,1]"
                        )
                    continue

                text = str(value or "").strip()
                if not text:
                    raise IncompleteDeterministicPackError(
                        f"situation signal #{index} mapped_target #{target_index} missing `{field}`"
                    )

        cascade_rules = signal.get("cascade_rules")
        if not isinstance(cascade_rules, list):
            raise IncompleteDeterministicPackError(
                f"situation signal #{index} field `cascade_rules` must be a list"
            )
        if not cascade_rules:
            no_cascade_reason = str(signal.get("no_cascade_reason") or "").strip()
            if not no_cascade_reason:
                raise IncompleteDeterministicPackError(
                    f"situation signal #{index} must include cascade_rules or no_cascade_reason"
                )
        for cascade_index, cascade in enumerate(cascade_rules, start=1):
            if not isinstance(cascade, dict):
                raise IncompleteDeterministicPackError(
                    f"situation signal #{index} cascade_rule #{cascade_index} must be an object"
                )
            trigger = str(cascade.get("trigger_condition") or "").strip()
            next_signal_id = str(cascade.get("next_signal_id") or "").strip()
            expected_lag = str(cascade.get("expected_lag") or "").strip()
            if not trigger or not next_signal_id:
                raise IncompleteDeterministicPackError(
                    f"situation signal #{index} cascade_rule #{cascade_index} missing trigger_condition or next_signal_id"
                )
            if expected_lag not in allowed_lags:
                raise IncompleteDeterministicPackError(
                    f"situation signal #{index} cascade_rule #{cascade_index} has invalid expected_lag {expected_lag!r}"
                )

        market_constraints = signal.get("market_constraints")
        if not isinstance(market_constraints, list) or not market_constraints:
            raise IncompleteDeterministicPackError(
                f"situation signal #{index} field `market_constraints` must be a non-empty list"
            )
        for constraint_index, constraint in enumerate(market_constraints, start=1):
            if not isinstance(constraint, dict):
                raise IncompleteDeterministicPackError(
                    f"situation signal #{index} market_constraint #{constraint_index} must be an object"
                )
            constraint_key = str(constraint.get("constraint_key") or "").strip()
            binding_strength = constraint.get("binding_strength")
            if not constraint_key:
                raise IncompleteDeterministicPackError(
                    f"situation signal #{index} market_constraint #{constraint_index} missing `constraint_key`"
                )
            if not isinstance(binding_strength, (int, float)):
                raise IncompleteDeterministicPackError(
                    f"situation signal #{index} market_constraint #{constraint_index} binding_strength must be numeric in [0,1]"
                )
            if float(binding_strength) < 0.0 or float(binding_strength) > 1.0:
                raise IncompleteDeterministicPackError(
                    f"situation signal #{index} market_constraint #{constraint_index} binding_strength must be in [0,1]"
                )

    return artifact
