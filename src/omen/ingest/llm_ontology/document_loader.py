"""Case document loaders for Spec 6 ontology generation."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from omen.ingest.pdf_extract import extract_pdf_pages
from omen.ingest.text_processing import clean_text, split_into_chunks
from omen.models.case_replay_models import CaseDocument


def _guess_content_type(path: Path) -> Literal["markdown", "text", "pdf"]:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return "pdf"
    if suffix in {".md", ".markdown"}:
        return "markdown"
    return "text"


def load_case_document(
    path: str | Path,
    *,
    case_id: str,
    title: str,
    known_outcome: str,
) -> CaseDocument:
    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(f"case document not found: {source}")

    content_type = _guess_content_type(source)
    if content_type == "pdf":
        text = extract_pdf_pages(source)
    else:
        text = source.read_text(encoding="utf-8")

    normalized = clean_text(text)
    if not normalized:
        raise ValueError("case document has no usable text content")

    return CaseDocument(
        case_id=case_id,
        title=title,
        content_type=content_type,
        source_path=str(source),
        raw_text=normalized,
        known_outcome=known_outcome,
    )


def chunk_case_document(doc: CaseDocument, *, chunk_size: int, chunk_overlap: int) -> list[str]:
    chunks = split_into_chunks(doc.raw_text, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    return [chunk.strip() for chunk in chunks if chunk.strip()]
