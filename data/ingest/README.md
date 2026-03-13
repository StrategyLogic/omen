# Ingest Workspace

This is Omen's native ingest workspace.

## Directory layout

- `data/ingest/sources/`: source documents (PDF/TXT/MD) for ingest runs
- `data/ingest/extracted/`: extracted text artifacts
- `data/ingest/knowledge/`: structured knowledge markdown artifacts (`*.md`)
- `data/ingest/graph/`: graph JSON artifacts (`*.json`)

## Notes

- This project no longer depends on a legacy-named ingest module.
- Legacy code can be used as reference, but Omen ingest runtime should remain self-contained.
