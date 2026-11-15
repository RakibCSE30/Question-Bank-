from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path

import fitz  # PyMuPDF
import pytesseract
from docx import Document as DocxDocument
from PIL import Image

from app.core.config import get_settings
from app.services.ingestion.bengali_unicode import analyze_bengali_text, normalize_bengali_nfc
from app.services.ingestion.chunker import ExtractedPage


@dataclass(frozen=True)
class ExtractedDocumentResult:
    pages: list[ExtractedPage]
    extraction_method: str
    legacy_encoding_detected: bool
    extraction_quality_score: float
    page_count: int


def _detect_pdf_heading(page: fitz.Page) -> str | None:
    """Detect prominent heading span on a PDF page using font size heuristics."""
    try:
        blocks = page.get_text("dict").get("blocks", [])
    except Exception:
        return None

    spans: list[tuple[float, str]] = []
    for block in blocks:
        for line in block.get("lines", []):
            line_text_parts = []
            max_size = 0.0
            for span in line.get("spans", []):
                text = span.get("text", "").strip()
                if text:
                    line_text_parts.append(text)
                    max_size = max(max_size, float(span.get("size", 0.0)))
            joined = " ".join(line_text_parts).strip()
            if joined and 3 <= len(joined) <= 120:
                spans.append((max_size, joined))

    if not spans:
        return None
    sizes = [s[0] for s in spans]
    median_size = sorted(sizes)[len(sizes) // 2]
    for size, text in spans[:6]:
        if size >= median_size * 1.18:
            return normalize_bengali_nfc(text)
    return None


def _ocr_pixmap_image(img: Image.Image, ocr_languages: str) -> str:
    return pytesseract.image_to_string(img, lang=ocr_languages)


def _extract_pdf(
    file_path: Path,
    *,
    force_ocr: bool,
    quality_threshold: float,
    ocr_languages: str,
) -> ExtractedDocumentResult:
    doc = fitz.open(str(file_path))
    pages: list[ExtractedPage] = []
    ocr_used_pages = 0
    any_legacy_detected = False
    last_heading: str | None = None

    try:
        page_count = len(doc)
        for idx in range(page_count):
            page = doc[idx]
            page_num = idx + 1
            heading = _detect_pdf_heading(page) or last_heading
            if heading:
                last_heading = heading

            raw_text = page.get_text("text") or ""
            analysis = analyze_bengali_text(raw_text, quality_threshold=quality_threshold)
            if analysis.legacy_encoding_detected:
                any_legacy_detected = True

            chosen_text = analysis.normalized_text
            chosen_score = analysis.quality_score

            # Automatic page-by-page Tesseract OCR fallback when scanned, empty, or Bijoy-garbled
            if force_ocr or analysis.needs_ocr or len(raw_text.strip()) < 30:
                pix = page.get_pixmap(dpi=260)
                png_bytes = pix.tobytes("png")
                pix = None
                with Image.open(io.BytesIO(png_bytes)) as img:
                    ocr_raw = _ocr_pixmap_image(img, ocr_languages)
                ocr_analysis = analyze_bengali_text(ocr_raw, quality_threshold=quality_threshold)
                ocr_used_pages += 1

                if force_ocr or analysis.legacy_encoding_detected or ocr_analysis.quality_score >= analysis.quality_score:
                    chosen_text = ocr_analysis.normalized_text
                    chosen_score = ocr_analysis.quality_score
                    # Derive heading from first short non-empty OCR line if none detected
                    if not heading and chosen_text:
                        first_line = chosen_text.splitlines()[0].strip()
                        if 3 <= len(first_line) <= 100:
                            heading = first_line
                            last_heading = heading

            pages.append(
                ExtractedPage(
                    page_number=page_num,
                    heading_path=heading,
                    text=chosen_text,
                    confidence=chosen_score,
                )
            )
    finally:
        doc.close()

    avg_score = round(sum(p.confidence for p in pages) / max(1, len(pages)), 3)
    method = "OCR_TESSERACT" if ocr_used_pages > 0 else "PYMUPDF"

    return ExtractedDocumentResult(
        pages=pages,
        extraction_method=method,
        legacy_encoding_detected=any_legacy_detected,
        extraction_quality_score=avg_score,
        page_count=len(pages),
    )


def _extract_docx(file_path: Path, *, quality_threshold: float) -> ExtractedDocumentResult:
    doc = DocxDocument(str(file_path))
    pages: list[ExtractedPage] = []
    current_heading: str | None = None
    section_buffer: list[str] = []
    page_counter = 1

    def flush_section() -> None:
        nonlocal page_counter
        if not section_buffer:
            return
        combined = "\n\n".join(section_buffer)
        analysis = analyze_bengali_text(combined, quality_threshold=quality_threshold)
        pages.append(
            ExtractedPage(
                page_number=page_counter,
                heading_path=current_heading,
                text=analysis.normalized_text,
                confidence=analysis.quality_score,
            )
        )
        page_counter += 1
        section_buffer.clear()

    for para in doc.paragraphs:
        text = normalize_bengali_nfc(para.text)
        if not text:
            continue
        style_name = (para.style.name or "").lower() if para.style else ""
        if "heading" in style_name or "title" in style_name:
            flush_section()
            current_heading = text
        else:
            section_buffer.append(text)

    flush_section()

    if not pages:
        pages.append(ExtractedPage(page_number=1, heading_path=None, text="", confidence=0.0))

    avg_score = round(sum(p.confidence for p in pages) / len(pages), 3)
    any_legacy = any(
        analyze_bengali_text(p.text, quality_threshold=quality_threshold).legacy_encoding_detected
        for p in pages
    )

    return ExtractedDocumentResult(
        pages=pages,
        extraction_method="DOCX",
        legacy_encoding_detected=any_legacy,
        extraction_quality_score=avg_score,
        page_count=len(pages),
    )


def _extract_txt(file_path: Path, *, quality_threshold: float) -> ExtractedDocumentResult:
    raw_bytes = file_path.read_bytes()
    decoded = ""
    for encoding in ("utf-8-sig", "utf-8", "utf-16"):
        try:
            decoded = raw_bytes.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    if not decoded:
        decoded = raw_bytes.decode("utf-8", errors="replace")

    analysis = analyze_bengali_text(decoded, quality_threshold=quality_threshold)
    return ExtractedDocumentResult(
        pages=[
            ExtractedPage(
                page_number=1,
                heading_path=None,
                text=analysis.normalized_text,
                confidence=analysis.quality_score,
            )
        ],
        extraction_method="TXT",
        legacy_encoding_detected=analysis.legacy_encoding_detected,
        extraction_quality_score=analysis.quality_score,
        page_count=1,
    )


def _extract_image(file_path: Path, *, quality_threshold: float, ocr_languages: str) -> ExtractedDocumentResult:
    with Image.open(str(file_path)) as img:
        ocr_raw = _ocr_pixmap_image(img, ocr_languages)
    analysis = analyze_bengali_text(ocr_raw, quality_threshold=quality_threshold)
    heading = None
    if analysis.normalized_text:
        first_line = analysis.normalized_text.splitlines()[0].strip()
        if 3 <= len(first_line) <= 100:
            heading = first_line
    return ExtractedDocumentResult(
        pages=[
            ExtractedPage(
                page_number=1,
                heading_path=heading,
                text=analysis.normalized_text,
                confidence=analysis.quality_score,
            )
        ],
        extraction_method="IMAGE_OCR",
        legacy_encoding_detected=analysis.legacy_encoding_detected,
        extraction_quality_score=analysis.quality_score,
        page_count=1,
    )


def extract_document(
    file_path: str | Path,
    *,
    force_ocr: bool = False,
) -> ExtractedDocumentResult:
    settings = get_settings()
    path = Path(file_path)
    ext = path.suffix.lower()

    if ext == ".pdf":
        return _extract_pdf(
            path,
            force_ocr=force_ocr,
            quality_threshold=settings.OCR_QUALITY_THRESHOLD,
            ocr_languages=settings.OCR_LANGUAGES,
        )
    if ext == ".docx":
        return _extract_docx(path, quality_threshold=settings.OCR_QUALITY_THRESHOLD)
    if ext == ".txt":
        return _extract_txt(path, quality_threshold=settings.OCR_QUALITY_THRESHOLD)
    if ext in {".png", ".jpg", ".jpeg", ".webp"}:
        return _extract_image(
            path,
            quality_threshold=settings.OCR_QUALITY_THRESHOLD,
            ocr_languages=settings.OCR_LANGUAGES,
        )
    raise ValueError(f"Unsupported file extension: {ext}")
