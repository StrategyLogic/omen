"""Prompt builders for Spec 6 document-to-ontology generation."""

from __future__ import annotations

from textwrap import dedent

from omen.models.case_replay_models import CaseDocument


def build_system_prompt() -> str:
    return dedent(
        """
        You are a strategic ontology engineer.
        Convert case documents into a single strict JSON object that is directly runnable by Omen.
        Output MUST be valid JSON only.

        Required top-level keys:
        - meta
        - tbox
        - abox
        - reasoning_profile
        - case_package
        - scenario_id
        - name
        - time_steps
        - seed
        - user_overlap_threshold
        - actors
        - capabilities

        Constraints:
        - Use actor concepts ending with Actor.
        - Use semantic relation names: has_capability, competes_with, depends_on, substitutes, complements, constrains, influences.
        - Keep capability scores in [0,1].
        - Keep all actors in abox.actors mapped into scenario actors by actor_id.
        - Keep available_actions among: grow_semantic_layer, defend_core, attack_competitor, partner_ecosystem.
        - Ensure reasoning_profile rule IDs exist in tbox.axioms.
        - Provide case_package references with ontology_presence=true and runtime support booleans all true.
        """
    ).strip()


def build_user_prompt(doc: CaseDocument, chunks: list[str]) -> str:
    chunk_text = "\n\n---\n\n".join(chunks)
    return dedent(
        f"""
        Case ID: {doc.case_id}
        Case title: {doc.title}
        Known outcome: {doc.known_outcome}
        Source path: {doc.source_path}

        Build a StrategyOntology JSON for this case.
        Preserve meaningful narrative signals, but convert them into explicit concepts, axioms, actors, capabilities, constraints, and scenario fields.

        Case content:
        {chunk_text}
        """
    ).strip()
