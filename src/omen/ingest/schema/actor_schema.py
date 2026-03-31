"""Shared actor schema constants for ingest runtime and validation."""

from __future__ import annotations

VERSION = "v0.1.0-actor"
DISCLOSURE_LEVEL = "public-structure"
STRATEGIC_DIMENSIONS = ("mental_patterns", "strategic_style")
QUERY_TYPES = ("status", "persona")
REDACTION_MARKER = {"redacted": True}
BACKGROUND_FACT_FIELDS = (
	"birth_year",
	"origin",
	"education",
	"career_trajectory",
	"key_experiences",
)
