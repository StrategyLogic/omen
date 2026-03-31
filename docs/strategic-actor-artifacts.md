# Strategic Actor Artifact Structure

Spec 7 baseline output root:

- `output/actors/<case_id>/`

Required files:

- `strategy_ontology.json`
- `actor_ontology.json`
- `generation.json`
- `analyze_status.json`
- `analyze_persona.json`

## `strategy_ontology.json`

Required contract points:

- `meta.case_id`
- `actor_ref.path == "actor_ontology.json"`
- `actor_ref.hash` present
- `abox.events` list available for timeline processing

## `actor_ontology.json`

Required contract points:

- `meta` object
- `actors` array
- `events` array

Constraint:

- no source-domain extension fields are required by the core contract.

## `analyze_status.json`

Primary payload:

- `timeline[]` rows with id/time/name and normalized description fallback

## `analyze_persona.json`

Primary payload:

- `persona_insight.narrative`
- `persona_insight.key_traits`
- `run_meta.prompt_version`
