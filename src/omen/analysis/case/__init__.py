"""Case-scoped analysis capabilities.

Contains non-OSS baseline deep-analysis helpers used by `omen case ...` workflows.
"""

from __future__ import annotations

from .formation import build_strategic_formation_chain
from .insight import generate_persona_insight, generate_unified_insight, generate_why_insight
from .loader import FounderSliceLoadError, load_founder_ontology, validate_founder_ref

__all__ = [
    "FounderSliceLoadError",
    "build_strategic_formation_chain",
    "generate_persona_insight",
    "generate_unified_insight",
    "generate_why_insight",
    "load_founder_ontology",
    "validate_founder_ref",
]
