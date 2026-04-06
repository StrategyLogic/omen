"""Scenario planning models for deterministic A/B/C planning pipeline."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class PlanningSlotPolicyModel(BaseModel):
    scenario_key: Literal["A", "B", "C"]
    label: str = Field(min_length=1)
    intent: str = Field(min_length=1)
    default_prior: float = Field(ge=0.0)


class ScenarioPlanningRuleTemplateModel(BaseModel):
    template_id: str = Field(min_length=1)
    template_version: str = Field(min_length=1)
    required_query_fields: list[str] = Field(min_length=1)
    slot_policy: list[PlanningSlotPolicyModel] = Field(min_length=3)
    prompt_contract: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_slot_policy(self) -> "ScenarioPlanningRuleTemplateModel":
        keys = [item.scenario_key for item in self.slot_policy]
        if sorted(keys) != ["A", "B", "C"]:
            raise ValueError("slot_policy must define A/B/C exactly once")
        return self


class StrategyActorPlanningQueryResultModel(BaseModel):
    situation_id: str = Field(min_length=1)
    actor_ref: str = Field(min_length=1)
    space_inputs: list[dict[str, Any]] = Field(min_length=1)
    constraint_signals: list[dict[str, Any]] = Field(default_factory=list)
    similarity_scores: list[dict[str, Any]] = Field(min_length=3)
    query_version: str = Field(min_length=1)


class ScenarioPriorProbabilitySnapshotModel(BaseModel):
    pack_id: str = Field(min_length=1)
    pack_version: str = Field(min_length=1)
    situation_id: str = Field(min_length=1)
    actor_ref: str = Field(min_length=1)
    raw_prior_scores: list[dict[str, Any]] = Field(min_length=3)
    normalized_priors: list[dict[str, Any]] = Field(min_length=3)
    planning_query_ref: str = Field(min_length=1)
    snapshot_version: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_abcs(self) -> "ScenarioPriorProbabilitySnapshotModel":
        for field_name in ("raw_prior_scores", "normalized_priors"):
            if field_name == "raw_prior_scores":
                score_items = self.raw_prior_scores
            else:
                score_items = self.normalized_priors

            keys = sorted(str(item.get("scenario_key") or "") for item in score_items)
            if keys != ["A", "B", "C"]:
                raise ValueError(f"{field_name} must include A/B/C exactly once")
        return self
