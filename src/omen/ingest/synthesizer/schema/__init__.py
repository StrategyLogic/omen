"""Schema definitions for LLM ontology extraction."""

from omen.ingest.synthesizer.schema.actor import (
    BACKGROUND_FACT_FIELDS,
    VERSION,
    ACTOR_SUFFIX,
    looks_like_actor_concept,
)
from omen.ingest.synthesizer.schema.relation import (
    APPROVED_RELATIONS,
    is_relation_approved,
)

__all__ = [
    "APPROVED_RELATIONS",
    "ACTOR_SUFFIX",
    "BACKGROUND_FACT_FIELDS",
    "VERSION",
    "is_relation_approved",
    "looks_like_actor_concept",
]
