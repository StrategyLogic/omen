"""LLM Insight engine for deep Persona & Strategy Gap analysis."""

from __future__ import annotations

import datetime
import json
from typing import Any


PERSONA_PROMPT = """
Analyze the character and mental patterns of the following founder based on provided ontology data.
Founder name: {founder_name}
Profile Facts: {profile_facts}
Mental Patterns: {mental_patterns}
Strategic Style: {strategic_style}

Generate a cohesive narrative (150-200 words) describing their "Persona". 
Highlight their consistency between beliefs and actions.
"""

STRATEGY_GAP_PROMPT = """
Review the following strategic formation process and its real-world execution.
Event: {event_name}
Description: {event_description}
Perception: {perception}
Decision Logic: {decision_logic}
Execution Delta: {execution_delta}

Identify 2-3 significant "Strategy-Reality Gaps". For each gap, provide:
1. The underlying Assumption (what the founder believed would happen).
2. The observed Observation (what actually happened).
3. Significance (why it matters for the case).
4. A "What-if" scenario: What if the assumption were true, or if a specific constraint was removed?
"""

def generate_unified_insight(
    *,
    case_id: str,
    founder_ontology: dict[str, Any],
    formation_payload: dict[str, Any] | None = None,
    llm_client: Any = None
) -> dict[str, Any]:
    """
    Generate a unified insight JSON containing:
    1. Persona Narrative
    2. Strategy Gap Analysis (if formation_payload is provided)
    """
    actors = founder_ontology.get("actors") or []
    founder_actor = next((a for a in actors if "founder" in str(a.get("type", "")).lower()), None)
    
    if not founder_actor:
        founder_actor = actors[0] if actors else {}

    founder_name = founder_actor.get("name", "Unknown Founder")
    profile = founder_actor.get("profile", {})
    
    # 1. Persona Insight
    # In skeleton mode (no llm_client), we produce a deterministic summary
    persona_narrative = (
        f"{founder_name} is characterized by a strong alignment with their core beliefs: "
        f"'{', '.join(profile.get('mental_patterns', {}).get('core_beliefs', [])[:2])}'. "
        f"Their strategic style reflects a '{profile.get('strategic_style', {}).get('decision_style', 'intentional')}' approach, "
        f"often prioritizing '{', '.join(profile.get('strategic_style', {}).get('non_negotiables', [])[:1])}' over external pressures. "
        "This indicates a founder persona that is deeply principle-driven, favoring evidence and internal logic over conventional process."
    )
    
    key_traits = [
        {"trait": "Principle-Driven", "evidence_summary": "Prioritizes non-negotiables in strategic decisions."},
        {"trait": "Evidence-Based", "evidence_summary": "Uses data/signals for market perception."}
    ]
    
    # 2. Strategy Gaps
    strategy_gaps = []
    if formation_payload:
        f_chain = formation_payload.get("formation_chain", {})
        d_logic = f_chain.get("decision_logic", {})
        exec_delta = f_chain.get("execution_delta", [])
        
        # Real logic would use LLM to compare assumption vs reality
        # For skeleton, we derive one gap from execution delta or constraints
        strategy_gaps.append({
            "assumption": "The initial strategic formation would lead to linear validation of core products.",
            "observation": f"The execution resulted in {len(exec_delta)} delta points affecting {', '.join([e.get('target_name') for e in exec_delta[:2]])}.",
            "gap_significance": "Highlight the mismatch between internal constraints and external scalability.",
            "what_if_scenario": "What if the founder had abandoned the non-negotiables to match external maturity standards?"
        })
    else:
        # Fallback if no specific formation provided
        strategy_gaps.append({
            "assumption": "Strategy would proceed without major pivots.",
            "observation": "Historical pivots recorded in timeline suggest recurring gaps in market perception.",
            "gap_significance": "Points to potential over-reliance on internal cognitive frames.",
            "what_if_scenario": "What if external market signals were weighted 2x more than internal beliefs?"
        })

    insight_result = {
        "query": {
            "type": "insight",
            "case_id": case_id,
            "target_event_id": formation_payload.get("query", {}).get("target_event_id") if formation_payload else None
        },
        "persona_insight": {
            "narrative": persona_narrative,
            "key_traits": key_traits,
            "consistency_score": 0.85
        },
        "strategy_gaps": strategy_gaps,
        "run_meta": {
            "timestamp": datetime.datetime.now().isoformat(),
            "prompt_version": "v1.0-skeleton"
        }
    }
    
    return insight_result
