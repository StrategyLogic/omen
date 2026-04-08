"""LLM and runtime configuration models."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


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
