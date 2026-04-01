"""Pydantic models for LLM ingestion, case documents, and extraction contracts."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


# --- Infrastructure & LLM Configuration ---

class LLMConfig(BaseModel):
    provider: Literal["deepseek"] = "deepseek"
    base_url: str = Field(min_length=1)
    chat_model: str = Field(min_length=1)
    embedding_model: str = Field(min_length=1)
    deepseek_api_key: str = Field(min_length=1)
    voyage_api_key: str = Field(default="chat-only")
    timeout_seconds: int = Field(default=120, ge=1)
    temperature: float = Field(default=0.1, ge=0.0, le=1.0)
    max_chunks: int = Field(default=12, ge=1)
    chunk_size: int = Field(default=1800, ge=200)
    chunk_overlap: int = Field(default=200, ge=0)


# --- Core Domain Objects ---

class CaseDocument(BaseModel):
    case_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    content_type: Literal["markdown", "text", "pdf"]
    source_path: str = Field(min_length=1)
    raw_text: str = Field(min_length=1)
    known_outcome: str = Field(min_length=1)


# --- Extraction & Evidence Candidates ---

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


# --- Output & Evaluation Results ---

class OntologyGenerationResult(BaseModel):
    case_id: str
    strategy_ontology: dict[str, Any]
    inferred_known_outcome: str | None = None
    validation_passed: bool
    validation_issues: list[dict[str, Any]] = Field(default_factory=list)
    generated_at: datetime


class PrecisionEvaluationProfile(BaseModel):
    profile_id: str = Field(min_length=1)
    case_id: str = Field(min_length=1)
    repeatability_threshold: float = Field(ge=0.0, le=1.0)
    directional_correctness_threshold: float = Field(ge=0.0, le=1.0)
    trace_completeness_threshold: float = Field(ge=0.0, le=1.0)
    status: str = Field(pattern="^(draft|active|retired)$")


class BaselineReplayArtifact(BaseModel):
    case_id: str
    ontology_path: str
    baseline_result_path: str
    baseline_explanation_path: str
    view_model_path: str
