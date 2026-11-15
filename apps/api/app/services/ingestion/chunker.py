from __future__ import annotations

import re
from dataclasses import dataclass

from app.services.ingestion.bengali_unicode import normalize_bengali_nfc


@dataclass(frozen=True)
class ExtractedPage:
    page_number: int
    heading_path: str | None
    text: str
    confidence: float


@dataclass(frozen=True)
class ChunkRecord:
    chunk_index: int
    page_number: int
    heading_path: str | None
    content_nfc: str
    token_count: int
    extraction_confidence: float


# Split after Bengali danda (।), double danda (॥), ?, ! (even if OCR omits space),
# or period followed by whitespace/EOL, while avoiding decimals (১.৫ / 1.5) and common abbreviations.
_ABBREV_RE = re.compile(r"\b(?:ড|মো|প্র|অ|খ্রি|Dr|Mr|Mrs|Ms|Prof)\.$")
_SENTENCE_BOUNDARY_RE = re.compile(r"(?<=[।॥?!])(?:\s+|(?=[^\s\"'\)\]]))|(?<!\d)\.(?=\s|$)")


def split_sentences_bengali_safe(text: str) -> list[str]:
    """Split text into complete sentences preserving Bengali (। / ॥) and English punctuation."""
    normalized = normalize_bengali_nfc(text)
    if not normalized:
        return []

    sentences: list[str] = []
    for paragraph in re.split(r"\n{2,}", normalized):
        para_clean = " ".join(line.strip() for line in paragraph.split("\n") if line.strip())
        if not para_clean:
            continue

        start = 0
        for match in _SENTENCE_BOUNDARY_RE.finditer(para_clean):
            matched_text = para_clean[match.start() : match.end()]
            end = match.end()
            # Include '.' if regex matched '.' directly; keep '।'/'॥'/'?'/'!' (lookbehind already places match.start() after them)
            slice_end = match.start() + (1 if matched_text == "." else 0)
            part = para_clean[start:slice_end].strip()
            if not part:
                start = end
                continue
            # Do not split right after known Bangla/English abbreviations
            if matched_text == "." and _ABBREV_RE.search(part):
                continue
            sentences.append(part)
            start = end

        tail = para_clean[start:].strip()
        if tail:
            sentences.append(tail)

    return sentences


def chunk_pages(
    pages: list[ExtractedPage],
    *,
    max_chars: int = 1100,
) -> list[ChunkRecord]:
    """Pack complete sentences into page- and heading-preserving chunks without mid-sentence splits."""
    chunks: list[ChunkRecord] = []
    chunk_index = 0

    for page in pages:
        sentences = split_sentences_bengali_safe(page.text)
        if not sentences:
            continue

        buffer: list[str] = []
        buffer_len = 0

        for sentence in sentences:
            sent_len = len(sentence)
            if buffer and (buffer_len + 1 + sent_len > max_chars):
                content = " ".join(buffer).strip()
                chunks.append(
                    ChunkRecord(
                        chunk_index=chunk_index,
                        page_number=page.page_number,
                        heading_path=page.heading_path,
                        content_nfc=content,
                        token_count=max(1, len(content.split())),
                        extraction_confidence=round(page.confidence, 3),
                    )
                )
                chunk_index += 1
                buffer = [sentence]
                buffer_len = sent_len
            else:
                buffer.append(sentence)
                buffer_len += sent_len + (1 if len(buffer) > 1 else 0)

        if buffer:
            content = " ".join(buffer).strip()
            chunks.append(
                ChunkRecord(
                    chunk_index=chunk_index,
                    page_number=page.page_number,
                    heading_path=page.heading_path,
                    content_nfc=content,
                    token_count=max(1, len(content.split())),
                    extraction_confidence=round(page.confidence, 3),
                )
            )
            chunk_index += 1

    return chunks
