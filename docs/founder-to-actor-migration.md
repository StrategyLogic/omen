# Founder to Actor Migration Note

Spec 7 is a hard-cut migration for OSS public contracts.

## Public Contract Changes

- `omen analyze founder` -> `omen analyze actor`
- `output/founder/<case_id>/` -> `output/actors/<case_id>/`
- `founder_ontology.json` -> `actor_ontology.json`
- `founder_ref` -> `actor_ref`

## Compatibility Policy

- No founder compatibility alias is provided in Spec 7 OSS contract.
- Founder-specific semantics are deferred to a future founder extension plugin.

## UI Naming Policy

- UI and docs should use `Strategic Actor` terminology.
- CLI and file contracts should use `actor` terminology.
