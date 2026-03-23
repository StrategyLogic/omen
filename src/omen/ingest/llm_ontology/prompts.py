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
        - abox.actors MUST be a list of objects with keys: actor_id, actor_type, shared_id, labels.
        - shared_id MUST be the literal name/brand from the document (e.g., "X-Developer") to facilitate entity linking.
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
                        "actors": [{"actor_id": "example_actor", "actor_type": "ExampleActor", "shared_id": "Example Inc.", "labels": []}],
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
        Build founder_ontology JSON only (v0.1.0-founder-centric).

        Required top-level keys:
        - meta (version, case_id, slice)
        - identity (shared_ids)
        - actors (detailed founder profile)
        - products (product/platform/tool assets)
        - events (strategic points)
        - influences (causal relationships)
        - query_skeleton (supported queries)

        Actor Schema (Multi-Role):
        - IMPORTANT: Extract ALL actors mentioned in the case (founder, investors, team members, customers, competitors, etc.).
        - id: unique slug (e.g. 'founder-1', 'customer-apple').
        - shared_id: The primary identifier string (e.g. "X-Developer") for mapping to StrategyOntology.
        - name: The display name (e.g. "X-Developer Founder").
        - type: 'founder' (primary), 'investor', 'competitor', 'customer', 'partner', 'team_member', 'organization'.
        - Profile for Founder:
            - background_facts: birth_year, origin, education[], career_trajectory[], key_experiences[]
            - mental_patterns: core_beliefs[], cognitive_frames[], founder_dna, risk_profile{{technical_risk, market_risk, financial_risk}}
            - strategic_style: decision_style, value_proposition, decision_preferences[], non_negotiables[]
        - Profile for all other Actors (investor, customer, etc.):
            - profile: interest, influence_level, alignment_with_founder, key_constraints[]

        Events Schema:
        - id, name, type, date, description, context_constraints[], actors_involved[], evidence_refs[]
        Rules:
        - philosophy: "Facts & Structures only. Narratives/Personas are generated via Query."
        - actors[].type: MUST be 'founder' for the primary decision maker.
        - mental_patterns.core_beliefs: Stable convictions (e.g., "Data is the only truth").
        - strategic_style.non_negotiables: Active constraints chosen by the founder (e.g., "No manual input").
        - events: MUST use time evidence from timeline input. Include 'context_constraints' for external pressures (e.g., "Cash flow < 6 months").
        - influences: Link mental_patterns/background to strategic_style/decisions (e.g., manifests_as_principle, shapes_belief).
        - IMPORTANT: Also link between Entities:
            - Product -> competes_with -> Competitor
            - Competitor -> influences/constrains -> Actors
            - Actors -> participates_in -> Events
            - Events -> affects -> Product (e.g., launch, pricing update)

        query_skeleton: status, why, persona, cognitive_tracing, decision_trade_offs.

        Case ID: {doc.case_id}
        Title: {doc.title}
        Known outcome: {doc.known_outcome}

        Timeline events (JSON):
        {timeline_json}

        Source excerpt:
        {excerpt}
        """
    ).strip()


def build_actor_semantic_enhancement_prompt(actor_payload_json: str, existing_relations_json: str) -> str:
    return dedent(
        f"""
        Analyze strategic influence and competitive dynamics among the provided organizations, stakeholders, and competitor products.

        Focus Areas:
        1. STRATEGIC INFLUENCE: How do these entities influence each other's market positioning, decision-making, or survival?
        2. COMPETITIVE IMPACT: For 'competitor' products, identify how they exert pressure (pricing, features, market defense) on specific actors.
        3. EXCLUSION: Do NOT analyze the primary Founder/CEO. Focus only on secondary actors and competitor products.

        Rules:
        - Use ONLY the provided IDs as source/target.
        - DIRECTION: Influencer -> [Relation Type] -> Impacted Entity.
        - EXTREME SELECTIVITY: Only create a relationship if there is a CLEAR STRATEGIC or COMPETITIVE link. If no strategic relationship exists between two nodes, do NOT create one.
        - NO REPETITION: Do NOT repeat or synonymize any relationship already listed in "Existing Relations".
        - Return only a JSON array of influence objects. If nothing new is found, return empty array [].
        - Semantic types: influences, constrains, pressures, substitutes, complements, competes_with.

        Entities to Analyze (JSON):
        {actor_payload_json}

        Existing Relations (Do NOT repeat or duplicate these):
        {existing_relations_json}
        """
    ).strip()
