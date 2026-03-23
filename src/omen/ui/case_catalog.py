"""Case selection helpers for Spec 6 UI and artifact layout."""

from __future__ import annotations

from pathlib import Path

_CANONICAL_CASE_IDS: dict[str, str] = {
    "x-developer": "xd",
    "x-developer-replay": "xd",
    "shenda-replay": "shenda",
}

_KNOWN_CASE_METADATA: dict[str, dict[str, str]] = {
    "xd": {
        "document": "cases/x-developer.md",
        "strategy": "new_tech_market_entry",
        "known_outcome": "project failed in market expansion",
        "title": "X-Developer Replay",
    },
    "shenda": {
        "document": "cases/shenda.md",
        "strategy": "platform_transition_competition",
        "known_outcome": "core entertainment businesses were sold off and the group shifted toward investment holding",
        "title": "Shanda / Chen Tianqiao Replay",
    },
}


def normalize_case_id(value: str | Path) -> str:
    stem = Path(str(value)).stem.strip().lower()
    if not stem:
        return ""
    canonical = _CANONICAL_CASE_IDS.get(stem)
    if canonical:
        return canonical
    if stem.startswith("case-"):
        stem = stem.removeprefix("case-")
    return stem


def case_id_from_markdown(file_path: Path) -> str:
    return normalize_case_id(file_path)


def list_case_ids_from_cases(cases_root: str | Path = "cases") -> list[str]:
    root = Path(cases_root)
    if not root.exists() or not root.is_dir():
        return []

    case_ids = {
        case_id_from_markdown(item)
        for item in root.glob("*.md")
        if item.is_file() and not item.stem.endswith("-source")
    }
    return sorted(case_ids)


def default_case_id(case_ids: list[str], loaded_case_id: str | Path | None = None) -> str:
    normalized_loaded_case_id = normalize_case_id(loaded_case_id or "")
    if normalized_loaded_case_id and normalized_loaded_case_id in case_ids:
        return normalized_loaded_case_id
    if case_ids:
        return case_ids[0]
    return ""


def case_output_dir(case_id: str, output_root: str | Path = "output/case_replay") -> Path:
    return Path(output_root) / normalize_case_id(case_id)


def resolve_existing_case_output_dir(case_id: str, output_root: str | Path = "output/case_replay") -> Path:
    canonical_dir = case_output_dir(case_id, output_root=output_root)
    if canonical_dir.exists():
        return canonical_dir

    canonical = normalize_case_id(case_id)
    legacy_candidates = {
        "xd": ["x-developer", "x-developer-replay"],
        "shenda": ["shenda-replay"],
    }.get(canonical, [])
    for candidate in legacy_candidates:
        candidate_dir = Path(output_root) / candidate
        if candidate_dir.exists():
            return candidate_dir

    return canonical_dir


def suggest_document_path(case_id: str) -> str:
    canonical = normalize_case_id(case_id)
    metadata = _KNOWN_CASE_METADATA.get(canonical)
    if metadata:
        document_path = Path(metadata["document"])
        if document_path.exists():
            return str(document_path)
    cases_root = Path("cases")
    if cases_root.exists():
        for item in sorted(cases_root.glob("*.md")):
            if item.is_file() and normalize_case_id(item) == canonical:
                return str(item)
    return str(Path("cases") / f"{canonical}.md")


def suggest_strategy(case_id: str) -> str:
    canonical = normalize_case_id(case_id)
    metadata = _KNOWN_CASE_METADATA.get(canonical)
    if metadata:
        return metadata["strategy"]
    return "new_tech_market_entry"


def suggest_known_outcome(case_id: str) -> str:
    canonical = normalize_case_id(case_id)
    metadata = _KNOWN_CASE_METADATA.get(canonical)
    if metadata:
        return metadata["known_outcome"]
    return "unknown"


def case_display_title(case_id: str) -> str:
    canonical = normalize_case_id(case_id)
    metadata = _KNOWN_CASE_METADATA.get(canonical)
    if metadata:
        return metadata["title"]
    return canonical.replace("-", " ").replace("_", " ").title()