"""Pydantic models for ingest and precision contracts."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class PrecisionEvaluationProfile(BaseModel):
    profile_id: str = Field(min_length=1)
    case_id: str = Field(min_length=1)
    repeatability_threshold: float = Field(ge=0.0, le=1.0)
    directional_correctness_threshold: float = Field(ge=0.0, le=1.0)
    trace_completeness_threshold: float = Field(ge=0.0, le=1.0)
    status: str = Field(pattern="^(draft|active|retired)$")


class EvidenceSpan(BaseModel):
    page: int = Field(ge=1)
    start: int = Field(ge=0)
    end: int = Field(ge=0)

    @field_validator("end")
    @classmethod
    def end_must_be_gte_start(cls, value: int, info) -> int:
        start = info.data.get("start", 0)
        if value < start:
            raise ValueError("evidence_span.end must be >= start")
        return value


class ExtractedEntityCandidate(BaseModel):
    candidate_id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    entity_text: str = Field(min_length=1)
    entity_type: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_span: EvidenceSpan
    mapping_status: str = Field(pattern="^(mapped|unmapped|conflict)$")
    proposed_concept_id: str | None = None


class OntologyAssertionCandidate(BaseModel):
    assertion_id: str = Field(min_length=1)
    subject_concept: str = Field(min_length=1)
    predicate: str = Field(min_length=1)
    object_concept: str = Field(min_length=1)
    source_candidates: list[str] = Field(min_length=1)
    review_state: str = Field(pattern="^(pending|approved|rejected)$")
    review_notes: str | None = None


class OutcomeEvidenceLink(BaseModel):
    link_id: str = Field(min_length=1)
    outcome_delta_id: str = Field(min_length=1)
    condition_refs: list[str] = Field(default_factory=list)
    rule_chain_refs: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    trace_completeness: float = Field(ge=0.0, le=1.0)
