from __future__ import annotations

import hashlib
from pathlib import Path

from fastapi import HTTPException, status

ALLOWED_EXTENSIONS: dict[str, set[str]] = {
    ".pdf": {"application/pdf"},
    ".docx": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
    ".txt": {"text/plain"},
    ".png": {"image/png"},
    ".jpg": {"image/jpeg"},
    ".jpeg": {"image/jpeg"},
    ".webp": {"image/webp"},
}


def validate_upload_metadata(
    *,
    filename: str | None,
    content_type: str | None,
    size_bytes: int,
    max_size_mb: int,
) -> str:
    if not filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Filename is required.")

    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file extension '{ext}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    allowed_mimes = ALLOWED_EXTENSIONS[ext]
    if content_type and content_type not in allowed_mimes and content_type != "application/octet-stream":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"MIME type '{content_type}' does not match extension '{ext}'.",
        )

    if size_bytes <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty.")

    max_bytes = max_size_mb * 1024 * 1024
    if size_bytes > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum allowed size of {max_size_mb} MB.",
        )
    return ext


def compute_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _char_trigrams(text: str) -> set[str]:
    compact = " ".join(text.split())
    if len(compact) < 3:
        return {compact} if compact else set()
    return {compact[i : i + 3] for i in range(len(compact) - 2)}


def compute_text_similarity(text_a: str, text_b: str) -> float:
    """Jaccard similarity over character 3-grams for near-duplicate Bengali/English document detection."""
    tri_a = _char_trigrams(text_a)
    tri_b = _char_trigrams(text_b)
    if not tri_a or not tri_b:
        return 0.0
    intersection = len(tri_a & tri_b)
    union = len(tri_a | tri_b)
    return round(intersection / union, 3) if union else 0.0
