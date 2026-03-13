"""Ingest source inventory helpers for Omen workspace assets."""

from __future__ import annotations

from pathlib import Path


DEFAULT_SOURCE_ASSETS_DIR = Path("data/ingest/sources")


def list_source_assets(source_dir: str | Path = DEFAULT_SOURCE_ASSETS_DIR) -> list[str]:
    root = Path(source_dir)
    if not root.exists():
        return []
    files: list[str] = []
    for path in root.rglob("*"):
        if path.is_file():
            files.append(str(path.relative_to(root)))
    return sorted(files)


def build_source_inventory(source_dir: str | Path = DEFAULT_SOURCE_ASSETS_DIR) -> dict:
    files = list_source_assets(source_dir)
    sample_outputs = [
        file for file in files if file.endswith((".json", ".jsonl", ".md")) and "extracted" in file
    ]
    return {
        "inventory_id": "ingest-source-inventory",
        "source_dir": str(Path(source_dir)),
        "module_inventory": [file for file in files if file.startswith("src/")],
        "sample_output_files": sample_outputs,
        "compatibility_state": "unreviewed",
        "file_count": len(files),
    }
