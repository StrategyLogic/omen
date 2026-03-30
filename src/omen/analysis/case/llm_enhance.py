"""LLM-enhanced founder analysis placeholders."""

from __future__ import annotations

import json
from typing import Any

from omen.ingest.llm_ontology.prompts import build_strategic_formation_prompt

def build_persona_prompt_payload(founder_ontology: dict[str, Any], question: str) -> dict[str, Any]:
    return {
        "question": question,
        "query_skeleton": founder_ontology.get("query_skeleton") or {},
        "actors": founder_ontology.get("actors") or [],
        "events": founder_ontology.get("events") or [],
        "constraints": founder_ontology.get("constraints") or [],
    }


def enhance_formation_with_narrative(
    formation_payload: dict[str, Any], llm_client: Any = None
) -> dict[str, Any]:
    """Enhance the formation chain with a narrative explanation."""
    chain = formation_payload.get("formation_chain", {})
    summary = formation_payload.get("summary", {})

    founder = summary.get("founder", "the founder")
    decision_logic = chain.get("decision_logic", {})
    event_name = decision_logic.get("event_name", "Unknown Event")

    conflict = chain.get("constraint_conflict", {})
    ext_pressure_list = ", ".join(
        [p.get("description") for p in conflict.get("external_pressures", [])]
    )

    mediation = chain.get("mediation", {})
    formation_prompt_template = build_strategic_formation_prompt()

    if llm_client is None:
        # Mock LLM narrative logic as a skeleton (Spec 6 - Phase 5 approach)
        # Using specific strings if it's the known founder, otherwise generic
        belief = (mediation.get("core_beliefs") or ["principled driven"])[0]
        style = mediation.get("decision_style") or "intentional"
        negotiable = (mediation.get("non_negotiables") or ["strategic alignment"])[0]

        narrative = (
            f"Driven by the core belief that '{belief}', "
            f"{founder} perceived signals like '{ext_pressure_list if ext_pressure_list else 'market demand'}' "
            f"not just as tasks, but as evidence to be filtered through a '{style}' lens. "
            f"The resulting decision to '{event_name}' represents a mediation where "
            f"internal constraints like {', '.join(conflict.get('internal_constraints', []))} were prioritized over "
            f"standard industrial processes, sticking to the non-negotiables of '{negotiable}'."
        )
    else:
        # Placeholder for actual LLM call integration
        narrative = (
            "Enhanced narrative generation with LLM is not yet active in this session. "
            f"Prompt template length={len(formation_prompt_template)}"
        )

    if "decision_logic" in chain:
        chain["decision_logic"]["narrative"] = narrative

    return formation_payload

