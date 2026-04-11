"""Core type aliases and shared models for Omen simulation foundations."""

from __future__ import annotations

from typing import Dict, Any

from pydantic import BaseModel, Field, model_validator

State = Dict[str, Any]
Action = Dict[str, Any]
Scenario = Dict[str, Any]


DETERMINISTIC_PACK_NOKIA = "strategic_actor_nokia_v1"
DETERMINISTIC_PACK_REQUIRED_SLOTS = ("A", "B", "C")


class CaseManifest(BaseModel):
    case_id: str = Field(min_length=1)
    case_name: str = Field(min_length=1)
    domain: str = Field(min_length=1)
    version: str = Field(min_length=1)
    scenario_entry: str = Field(min_length=1)
    narrative_entry: str = Field(min_length=1)
    tags: list[str] = Field(default_factory=list)


class RuntimeSupportDeclaration(BaseModel):
    simulate_supported: bool
    explain_supported: bool
    compare_supported: bool
    semantic_conditions_supported: bool
    rule_trace_supported: bool

    @model_validator(mode="after")
    def all_core_workflows_supported(self) -> "RuntimeSupportDeclaration":
        if not (self.simulate_supported and self.explain_supported and self.compare_supported):
            raise ValueError("simulate/explain/compare must all be supported")
        if not (self.semantic_conditions_supported and self.rule_trace_supported):
            raise ValueError("semantic_conditions_supported and rule_trace_supported must be true")
        return self


class CasePackage(BaseModel):
    manifest: CaseManifest
    scenario_file: str = Field(min_length=1)
    case_doc_file: str = Field(min_length=1)
    required_artifacts: list[str] = Field(min_length=1)
    ontology_presence: bool = True
    runtime_support: RuntimeSupportDeclaration


class CapabilityDilemmaFit(BaseModel):
    scenario_key: str = Field(min_length=1)
    fit: str = Field(min_length=1)
    capability_scores: dict[str, float] = Field(default_factory=dict)


class ResistanceBaselineScore(BaseModel):
    structural_conflict: float = Field(ge=0.0, le=1.0)
    resource_reallocation_drag: float = Field(ge=0.0, le=1.0)
    cultural_misalignment: float = Field(ge=0.0, le=1.0)
    veto_node_intensity: float = Field(ge=0.0, le=1.0)
    aggregate_resistance: float = Field(ge=0.0, le=1.0)


class ScenarioConditions(BaseModel):
    required: list[str] = Field(default_factory=list)
    warning: list[str] = Field(default_factory=list)
    blocking: list[str] = Field(default_factory=list)


class ScenarioSelectedDimensions(BaseModel):
    scenario_key: str = Field(min_length=1)
    selected_dimension_keys: list[str] = Field(default_factory=list)
    selection_rationale: list[str] = Field(default_factory=list)


class ConditionDerivationTrace(BaseModel):
    scenario_key: str = Field(min_length=1)
    ontology_refs: list[str] = Field(default_factory=list)
    selected_dimensions: list[str] = Field(default_factory=list)
    derivation_steps: list[str] = Field(default_factory=list)
    missing_evidence_reasons: list[str] = Field(default_factory=list)


class DeterministicScenarioResult(BaseModel):
    scenario_key: str = Field(min_length=1)
    capability_dilemma_fit: CapabilityDilemmaFit
    resistance: ResistanceBaselineScore
    scenario_conditions: ScenarioConditions
    selected_dimensions: ScenarioSelectedDimensions | None = None
    derivation_trace: ConditionDerivationTrace | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    confidence_level: str = Field(min_length=1)


class DeterministicRunComparability(BaseModel):
    comparable: bool
    blocking_reasons: list[str] = Field(default_factory=list)
    actor_profile_version: str = Field(min_length=1)
    scenario_pack_version: str = Field(min_length=1)
    calculation_policy_version: str = Field(min_length=1)


class DeterministicRunArtifact(BaseModel):
    run_id: str = Field(min_length=1)
    run_timestamp: str = Field(min_length=1)
    actor_profile_ref: str = Field(min_length=1)
    scenario_pack_ref: str = Field(min_length=1)
    scenario_results: list[DeterministicScenarioResult] = Field(default_factory=list)
    recommendation_summary: str = Field(min_length=1)
    gap_summary: str = Field(min_length=1)
    required_actions: str = Field(min_length=1)
    comparability: DeterministicRunComparability
    export_status: str = Field(min_length=1)
