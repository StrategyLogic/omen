"""Ontology and scenario/situation contract models."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class OntologyMeta(BaseModel):
  version: str = Field(min_length=1)
  case_id: str = Field(min_length=1)
  domain: str = Field(min_length=1)
  strategy: str = Field(min_length=1, default="case_specific_strategy")


class ConceptDef(BaseModel):
  name: str = Field(min_length=1)
  description: str = ""
  category: Literal["actor", "capability", "constraint", "event", "outcome", "game", "other"] = "other"


class RelationDef(BaseModel):
  name: str = Field(min_length=1)
  source: str = Field(min_length=1)
  target: str = Field(min_length=1)
  description: str = Field(min_length=1)


class AxiomDef(BaseModel):
  id: str = Field(min_length=1)
  statement: str | None = None
  type: str | None = None


class TBoxDefinition(BaseModel):
  concepts: list[ConceptDef] = Field(min_length=1)
  relations: list[RelationDef] = Field(min_length=1)
  axioms: list[AxiomDef] = Field(min_length=1)


class ActorInstance(BaseModel):
  actor_id: str = Field(min_length=1)
  actor_type: Literal["Actor", "StrategicActor"] = "Actor"
  role: str = Field(min_length=1)
  shared_id: str | None = None
  labels: list[str] = Field(default_factory=list)
  profile: dict[str, Any] | None = None

  @model_validator(mode="after")
  def strategic_actor_profile_required(self) -> "ActorInstance":
    if self.actor_type == "StrategicActor" and not isinstance(self.profile, dict):
      raise ValueError("StrategicActor instances must include profile")
    return self


class CapabilityInstance(BaseModel):
  actor_id: str = Field(min_length=1)
  name: str = Field(min_length=1)
  score: float = Field(ge=0.0, le=1.0)


class ConstraintInstance(BaseModel):
  name: str = Field(min_length=1)
  value: float | int | str | bool
  unit: str | None = None


class EventInstance(BaseModel):
  event_type: str = Field(min_length=1)
  target: str | None = None
  payload: dict[str, Any]


class ABoxDefinition(BaseModel):
  actors: list[ActorInstance] = Field(min_length=1)
  capabilities: list[CapabilityInstance] = Field(default_factory=list)
  constraints: list[ConstraintInstance] = Field(default_factory=list)
  events: list[EventInstance] = Field(default_factory=list)


class RuleRef(BaseModel):
  rule_id: str = Field(min_length=1)
  description: str | None = None


class ReasoningProfile(BaseModel):
  activation_rules: list[RuleRef] = Field(default_factory=list)
  propagation_rules: list[RuleRef] = Field(default_factory=list)
  counterfactual_rules: list[RuleRef] = Field(default_factory=list)


class OntologyInputPackage(BaseModel):
  meta: OntologyMeta
  tbox: TBoxDefinition
  abox: ABoxDefinition
  reasoning_profile: ReasoningProfile = Field(default_factory=ReasoningProfile)
  tech_space_ontology: dict[str, Any] | None = None
  market_space_ontology: dict[str, Any] | None = None
  shared_actors: list[str] = Field(default_factory=list)


class ActorOntologyEnvelope(BaseModel):
  meta: dict[str, Any]
  actors: list[dict[str, Any]] = Field(default_factory=list)
  events: list[dict[str, Any]] = Field(default_factory=list)
  influences: list[dict[str, Any]] = Field(default_factory=list)
  query_skeleton: dict[str, Any] = Field(default_factory=dict)


class SituationSourceDocument(BaseModel):
  situation_id: str = Field(min_length=1)
  source_path: str = Field(min_length=1)
  title: str = Field(min_length=1)
  company_context: str = Field(min_length=1)
  dilemma_narrative: str = Field(min_length=1)
  analysis_scope: str = Field(min_length=1)
  created_at: str = Field(min_length=1)


class SituationAnalysisRequest(BaseModel):
  situation_id: str = Field(min_length=1)
  doc: str = Field(min_length=1)
  actor_ref: str | None = None
  target_pack_id: str = Field(min_length=1)
  target_pack_version: str = Field(min_length=1)
  output_path: str | None = None


class SituationContextModel(BaseModel):
  title: str = Field(min_length=1)
  core_question: str = Field(min_length=1)
  current_state: str = Field(min_length=1)
  core_dilemma: str = Field(min_length=1)
  key_decision_point: str = Field(min_length=1)
  target_outcomes: list[str] = Field(min_length=1)
  hard_constraints: list[str] = Field(min_length=1)
  known_unknowns: list[str] = Field(default_factory=list)
  actor_ref: str | None = None


class SituationEnhanceRequestModel(BaseModel):
  situation_id: str = Field(min_length=1)
  source_doc_ref: str = Field(min_length=1)
  context: SituationContextModel
  target_pack_id: str = Field(min_length=1)
  target_pack_version: str = Field(min_length=1)


class SituationArtifactModel(BaseModel):
  version: str = Field(min_length=1)
  id: str = Field(min_length=1)
  context: SituationContextModel
  signals: list[dict[str, Any]] = Field(min_length=1)
  tech_space_seed: list[dict[str, Any]] = Field(default_factory=list)
  market_space_seed: list[dict[str, Any]] = Field(default_factory=list)
  uncertainty_space: dict[str, Any] = Field(default_factory=dict)
  source_trace: list[dict[str, Any]] = Field(default_factory=list)
  source_meta: dict[str, Any] = Field(default_factory=dict)


class ScenarioSplitRequestModel(BaseModel):
  situation_artifact_path: str = Field(min_length=1)
  target_pack_id: str = Field(min_length=1)
  target_pack_version: str = Field(min_length=1)
  output_path: str | None = None


class ResistanceAssumptionsModel(BaseModel):
  structural_conflict: float = Field(ge=0.0, le=1.0)
  resource_reallocation_drag: float = Field(ge=0.0, le=1.0)
  cultural_misalignment: float = Field(ge=0.0, le=1.0)
  veto_node_intensity: float = Field(ge=0.0, le=1.0)
  aggregate_resistance: float = Field(ge=0.0, le=1.0)
  assumption_rationale: list[str] = Field(min_length=1)


class SceneModel(BaseModel):
  scenario_key: Literal["A", "B", "C"]
  title: str = Field(min_length=1)
  goal: str = Field(min_length=1)
  target: str = Field(min_length=1)
  objective: str = Field(min_length=1)
  variables: list[dict[str, Any]] = Field(min_length=1)
  constraints: list[str] = Field(min_length=1)
  tradeoff_pressure: list[str] = Field(min_length=1)
  resistance_assumptions: ResistanceAssumptionsModel
  modeling_notes: list[str] = Field(min_length=1)


class ScenarioOntologySliceModel(BaseModel):
  pack_id: str = Field(min_length=1)
  pack_version: str = Field(min_length=1)
  derived_from_situation_id: str = Field(min_length=1)
  ontology_version: str = Field(min_length=1)
  planning_query_ref: str = Field(default="traces/planning_query.json", min_length=1)
  prior_snapshot_ref: str = Field(default="traces/prior_snapshot.json", min_length=1)
  scenarios: list[SceneModel] = Field(min_length=1)

  @model_validator(mode="after")
  def unique_scenario_keys(self) -> "ScenarioOntologySliceModel":
    keys = [item.scenario_key for item in self.scenarios]
    if len(keys) != len(set(keys)):
      raise ValueError("scenario_key values must be unique")
    return self


class NLScenarioDescription(BaseModel):
  slot: Literal["A", "B", "C"]
  title: str = Field(min_length=1)
  description: str = Field(min_length=1)


class ScenarioCompilationRequest(BaseModel):
  pack_id: str = Field(min_length=1)
  pack_version: str = Field(min_length=1)
  case_id: str = Field(min_length=1)
  scenarios: list[NLScenarioDescription] = Field(min_length=1)

  @model_validator(mode="after")
  def unique_slots(self) -> "ScenarioCompilationRequest":
    slots = [item.slot for item in self.scenarios]
    if len(slots) != len(set(slots)):
      raise ValueError("scenario slots must be unique")
    return self


class ResistanceBaselineModel(BaseModel):
  structural_conflict: float = Field(ge=0.0, le=1.0)
  resource_reallocation_drag: float = Field(ge=0.0, le=1.0)
  cultural_misalignment: float = Field(ge=0.0, le=1.0)
  veto_node_intensity: float = Field(ge=0.0, le=1.0)
  aggregate_resistance: float = Field(ge=0.0, le=1.0)


class DeterministicScenarioModel(BaseModel):
  scenario_key: str = Field(min_length=1)
  title: str = Field(min_length=1)
  target_outcome: str = Field(min_length=1)
  constraints: list[str] = Field(min_length=1)
  dilemma_tradeoffs: list[str] = Field(min_length=1)
  resistance_baseline: ResistanceBaselineModel


class DeterministicScenarioPackModel(BaseModel):
  pack_id: str = Field(min_length=1)
  pack_version: str = Field(min_length=1)
  scenarios: list[DeterministicScenarioModel] = Field(min_length=1)

  @model_validator(mode="after")
  def unique_scenario_keys(self) -> "DeterministicScenarioPackModel":
    keys = [item.scenario_key for item in self.scenarios]
    if len(keys) != len(set(keys)):
      raise ValueError("scenario_key values must be unique")
    return self
