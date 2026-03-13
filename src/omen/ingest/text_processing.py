"""Deterministic text normalization and chunking helpers.

Adapted from legacy extraction utilities and kept dependency-light for Omen.
"""

from __future__ import annotations

import re
import unicodedata
from typing import List

_SENTENCE_TERMINATORS = {".", "!", "?"}
_CLOSING_QUOTES = {"'", '"', "\u2019", "\u201d", ")", "]", "}", "\u00bb", "\u203a"}
_HYPHEN_LINEBREAK_PATTERN = re.compile(r"(?<=\w)-\n(?=\w)")


def _merge_single_newlines(text: str) -> str:
    chars: List[str] = []
    length = len(text)
    i = 0

    while i < length:
        ch = text[i]

        if ch == "\n":
            prev = i - 1
            while prev >= 0 and text[prev] in " \t":
                prev -= 1

            if prev >= 0 and text[prev] == "\n":
                chars.append("\n")
            else:
                prev_idx = prev
                while prev_idx >= 0 and text[prev_idx] in _CLOSING_QUOTES:
                    prev_idx -= 1
                prev_char = text[prev_idx] if prev_idx >= 0 else ""

                if prev_char and prev_char in _SENTENCE_TERMINATORS:
                    chars.append("\n")
                else:
                    if chars and chars[-1] != " ":
                        chars.append(" ")
                    elif not chars:
                        chars.append(" ")

            i += 1
            continue

        chars.append(ch)
        i += 1

    return "".join(chars)


def clean_text(raw: str) -> str:
    """Normalize extracted text into stable ingest-ready content."""

    normalized = raw.replace("\r\n", "\n").replace("\r", "\n")
    normalized = _HYPHEN_LINEBREAK_PATTERN.sub("", normalized)
    normalized = unicodedata.normalize("NFKC", normalized)
    normalized = _merge_single_newlines(normalized)
    normalized = re.sub(r"[ \t]+", " ", normalized)
    normalized = re.sub(r" +\n", "\n", normalized)
    normalized = re.sub(r"\n +", "\n", normalized)
    return normalized.strip()


def split_into_chunks(text: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> list[str]:
    """Chunk text with deterministic overlap.

    Falls back to pure character slicing to keep runtime dependency-free.
    """

    if chunk_size <= 0:
        raise ValueError("chunk_size must be > 0")
    if chunk_overlap < 0:
        raise ValueError("chunk_overlap must be >= 0")
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size")

    chunks: list[str] = []
    start = 0
    length = len(text)

    while start < length:
        end = min(length, start + chunk_size)
        chunks.append(text[start:end])
        if end >= length:
            break
        start = end - chunk_overlap

    return chunks
