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
                - meta MUST include: version, case_id, domain.
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
        - Provide case_package references with ontology_presence=true and runtime support booleans all true.

                Minimal structural example (shape only):
                {
                    "meta": {"version": "1.0", "case_id": "...", "domain": "..."},
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
                    }
                }
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
