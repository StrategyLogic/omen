"""Scenario schema validation for ontology battle MVP."""

from __future__ import annotations

from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator

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
    try:
        return validate_scenario(payload)
    except ValidationError:
        raise
