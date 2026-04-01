"""Pydantic models for ontology packages."""

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
    category: Literal["actor", "capability", "constraint", "event", "outcome", "game", "other"] = (
        "other"
    )


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
