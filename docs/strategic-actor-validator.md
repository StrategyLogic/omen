# Strategic Actor Validator Guide

## Command Surface

Case-level validation:

```bash
omen validate actor --doc <doc_name> --output-dir output/actors
```

Single-file validation:

```bash
omen validate actor --file output/actors/<case-id>/actor_ontology.json
```

## Output Contract

Validator returns deterministic JSON:

- `status`: `pass` or `fail`
- `target_artifact`
- `schema_version`
- `errors[]`
- `warnings[]`

No third status is allowed.

## Common Failure Cases

- missing `meta` in `actor_ontology.json`
- missing `actors` or `events` array
- missing `actor_ref` in `strategy_ontology.json`
- wrong `actor_ref.path` filename
