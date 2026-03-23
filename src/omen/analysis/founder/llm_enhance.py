"""LLM-enhanced founder analysis placeholders."""

from __future__ import annotations

import json
from typing import Any


STRATEGIC_FORMATION_PROMPT = """
You are a startup strategy analyst expert. Your task is to generate a cohesive "Strategic Formation Narrative" for a founder's decision.

Given the following raw strategic formation data:
Founder: {founder}
Decision Event: {event_name} - {event_description}

Perception (Signals from market/tech):
{perception_list}

Constraint Conflict (Internal vs External):
- Internal Constraints: {internal_constraints}
- External Pressures: {external_pressures}

Founder Mediation (Beliefs & Style):
- Core Beliefs: {core_beliefs}
- Cognitive Frames: {cognitive_frames}
- Decision Style: {decision_style}
- Non-negotiables: {non_negotiables}

Outcome (Execution Delta):
{execution_list}

TASK:
Write a highly analytical and structured narrative (2-3 paragraphs) that explains HOW the founder's mental patterns mediated the external signals and constraints to reach this specific decision. 
Focus on the tension between "What was happening" and "How they thought about it".

Format the output as a JSON object with a single key "narrative".
"""


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
    event_description = decision_logic.get("description", "")

    perception_list = "\n".join(
        [f"- {p.get('source_name')}: {p.get('description')}" for p in chain.get("perception", [])]
    )
    execution_list = "\n".join(
        [
            f"- {e.get('target_name')}: {e.get('description')}"
            for e in chain.get("execution_delta", [])
        ]
    )

    conflict = chain.get("constraint_conflict", {})
    ext_pressure_list = ", ".join(
        [p.get("description") for p in conflict.get("external_pressures", [])]
    )

    mediation = chain.get("mediation", {})

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
        narrative = "Enhanced narrative generation with LLM is not yet active in this session."

    if "decision_logic" in chain:
        chain["decision_logic"]["narrative"] = narrative

    return formation_payload

