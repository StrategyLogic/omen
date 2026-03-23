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
        - known_outcome
        - meta
        - tbox
        - abox
        - reasoning_profile
        - tech_space_ontology
        - market_space_ontology
        - shared_actors
        - case_package
        - scenario_id
        - name
        - time_steps
        - seed
        - user_overlap_threshold
        - actors
        - capabilities

        Constraints:
        - known_outcome MUST be a concise final outcome phrase; return empty string only when evidence is insufficient.
        - meta MUST include: version, case_id, domain, strategy.
        - meta.strategy MUST be a reusable strategy-family slug in snake_case, not a case-specific title.
        - If the caller provides a preferred strategy label, use it exactly.
        - Use actor concepts ending with Actor.
        - tbox.concepts MUST be a list of objects, not strings. Each concept item requires: name, description, category.
        - concept.category MUST be one of: actor, capability, constraint, event, outcome, game, other.
        - If you discover new concept types beyond current taxonomy, keep category="other" and encode the concrete type in the name.
        - Naming principle: concepts use PascalCase nouns; actor concepts end with Actor; capabilities use snake_case where practical.
        - tbox.relations MUST be a list of objects with keys: name, source, target, description.
        - Prefer semantic relation names: has_capability, competes_with, depends_on, substitutes, complements, constrains, influences.
        - If the case clearly needs a different relation such as addresses or leads_to, you may emit a case-specific relation name.
        - relation source/target MUST reference names declared in tbox.concepts.
        - tbox.axioms MUST be a list of objects with keys: id, statement, type.
        - axiom type may be activation, propagation, counterfactual, or case-specific custom type.
        - abox.actors MUST be a list of objects with keys: actor_id, actor_type, labels.
        - actor_type should reference actor concept names from tbox.concepts where possible.
        - abox.capabilities and abox.constraints SHOULD be provided when evidence exists; keep capability scores in [0,1].
        - Keep capability scores in [0,1].
        - Keep all actors in abox.actors mapped into scenario actors by actor_id.
        - Keep available_actions among: grow_semantic_layer, defend_core, attack_competitor, partner_ecosystem.
        - reasoning_profile MUST include activation_rules, propagation_rules, counterfactual_rules as arrays (can be empty).
        - Ensure reasoning_profile rule IDs exist in tbox.axioms.
        - tech_space_ontology MUST describe technology capability evolution (actors, capabilities, tech axioms).
        - market_space_ontology MUST describe market dynamics (actors, market attributes, market axioms).
        - market_space_ontology MUST include adoption_resistance as an explicit attribute or constraint.
        - shared_actors MUST list actor_ids that appear in both tech_space_ontology.actors and market_space_ontology.actors.
        - Focus this case on the process of adoption resistance when a new technology product enters market.
        - Provide case_package references with ontology_presence=true and runtime support booleans all true.

                Minimal structural example (shape only):
                {
                    "meta": {"version": "1.0", "case_id": "...", "domain": "...", "strategy": "new_tech_market_entry"},
                    "tbox": {
                        "concepts": [{"name": "ExampleActor", "description": "...", "category": "actor"}],
                        "relations": [{"name": "has_capability", "source": "ExampleActor", "target": "example_capability", "description": "..."}],
                        "axioms": [{"id": "AX-1", "statement": "...", "type": "activation"}]
                    },
                    "abox": {
                        "actors": [{"actor_id": "example_actor", "actor_type": "ExampleActor", "labels": []}],
                        "capabilities": [{"actor_id": "example_actor", "name": "example_capability", "score": 0.8}],
                        "constraints": [{"name": "budget", "value": 100}]
                    },
                    "reasoning_profile": {
                        "activation_rules": [{"rule_id": "AX-1"}],
                        "propagation_rules": [],
                        "counterfactual_rules": []
                    },
                    "tech_space_ontology": {
                        "actors": [{"actor_id": "example_actor"}],
                        "capabilities": [{"name": "example_capability", "score": 0.8}],
                        "axioms": [{"id": "T-AX-1", "statement": "capability improves with integration"}]
                    },
                    "market_space_ontology": {
                        "actors": [{"actor_id": "example_actor"}],
                        "market_attributes": {"adoption_resistance": 0.7},
                        "axioms": [{"id": "M-AX-1", "statement": "high adoption_resistance slows expansion"}]
                    },
                    "shared_actors": ["example_actor"]
                }
        """
    ).strip()


def build_user_prompt(
    doc: CaseDocument,
    chunks: list[str],
    strategy: str | None = None,
) -> str:
    chunk_text = "\n\n---\n\n".join(chunks)
    preferred_strategy = strategy or "infer from the case evidence"
    return dedent(
        f"""
        Case ID: {doc.case_id}
        Case title: {doc.title}
        Known outcome: {doc.known_outcome}
        Source path: {doc.source_path}
        Preferred strategy label: {preferred_strategy}

        Build a StrategyOntology JSON for this case.
        Extract and output top-level known_outcome in the same JSON response.
        If input Known outcome is unknown/empty, infer from evidence.
        The ontology must classify the case into a reusable strategy family under meta.strategy.
        Preserve meaningful narrative signals, but convert them into explicit concepts, axioms, actors, capabilities, constraints, and scenario fields.

        Case content:
        {chunk_text}
        """
    ).strip()


def build_timeline_events_prompt(doc: CaseDocument, excerpt: str) -> str:
    return dedent(
        f"""
        You are an ontology extraction assistant.
        Extract timeline events from the case document as JSON array only.

        Required item fields:
        - id (string)
        - time (string, e.g. 2016 or 2016-06)
        - event (string enum type only, short token: launch|release|pilot|pricing|expansion|other)
        - description (string, concrete event narrative)
        - evidence_refs (string array)
        - confidence (number in [0,1])
        - is_strategy_related (boolean)

        Rules:
        - Do NOT emit phase/stage fields.
        - Keep only historically grounded events with evidence.
        - Output JSON array only, no markdown.

        Case ID: {doc.case_id}
        Title: {doc.title}
        Known outcome: {doc.known_outcome}

        Content:
        {excerpt}
        """
    ).strip()


def build_founder_ontology_prompt(
    doc: CaseDocument,
    excerpt: str,
    timeline_json: str,
) -> str:
    return dedent(
        f"""
        You are an ontology extraction assistant.
        Build founder_ontology JSON only.

        Required top-level keys:
        - meta
        - actors
        - events
        - constraints
        - influences
        - query_skeleton

        Required constraints:
        - meta includes version/case_id/slice/generated_at
        - events must use time evidence from timeline input
        - events should include short type labels for graph display (e.g. launch/release/pilot)
        - keep long narrative in description fields when available
        - do not use phase/stage field
        - query_skeleton.query_types must be: status, why, persona

        Case ID: {doc.case_id}
        Title: {doc.title}
        Known outcome: {doc.known_outcome}

        Timeline events (JSON):
        {timeline_json}

        Source excerpt:
        {excerpt}
        """
    ).strip()


def build_actor_semantic_enhancement_prompt(actor_payload_json: str) -> str:
    return dedent(
        f"""
        Analyze decision-making and influence relationships among the provided actors.

        Rules:
        - Only use these actor IDs as source/target.
        - Do not reference founder actor.
        - Do not reference events, constraints, or any other node types.
        - Return only JSON array.
        - Each item must include: source, target, type, description.

        Actors (JSON):
        {actor_payload_json}
        """
    ).strip()
