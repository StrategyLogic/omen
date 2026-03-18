"""Data models for Spec 6 case replay workflow."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class LLMConfig(BaseModel):
    provider: Literal["deepseek"] = "deepseek"
    base_url: str = Field(min_length=1)
    chat_model: str = Field(min_length=1)
    embedding_model: str = Field(min_length=1)
    deepseek_api_key: str = Field(min_length=1)
    voyage_api_key: str = Field(min_length=1)
    timeout_seconds: int = Field(default=120, ge=1)
    temperature: float = Field(default=0.1, ge=0.0, le=1.0)
    max_chunks: int = Field(default=12, ge=1)
    chunk_size: int = Field(default=1800, ge=200)
    chunk_overlap: int = Field(default=200, ge=0)


class CaseDocument(BaseModel):
    case_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    content_type: Literal["markdown", "text", "pdf"]
    source_path: str = Field(min_length=1)
    raw_text: str = Field(min_length=1)
    known_outcome: str = Field(min_length=1)


class OntologyGenerationResult(BaseModel):
    case_id: str
    strategy_ontology: dict[str, Any]
    validation_passed: bool
    validation_issues: list[dict[str, Any]] = Field(default_factory=list)
    generated_at: datetime


class BaselineReplayArtifact(BaseModel):
    case_id: str
    ontology_path: str
    baseline_result_path: str
    baseline_explanation_path: str
    view_model_path: str
