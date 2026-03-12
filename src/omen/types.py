"""Core type aliases and shared models for Omen simulation foundations."""

from __future__ import annotations

from typing import Dict, Any

from pydantic import BaseModel, Field, model_validator

State = Dict[str, Any]
Action = Dict[str, Any]
Scenario = Dict[str, Any]


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
