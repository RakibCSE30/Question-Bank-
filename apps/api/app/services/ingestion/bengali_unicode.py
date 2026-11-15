from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field


# Common Bijoy / SutonnyMJ ASCII-mapped Bengali artifacts & CP1252 glyphs
_BIJOY_LEGACY_CHARS = set("†‡©š˜Ö¨¸¹º»¼½¾¿¢£¤¥¦§ª«¬®¯°±²³´µ¶·ÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕ×ØÙÚÛÜÝÞßàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ")

_BIJOY_SEQUENCES_RE = re.compile(
    r"(?:"
    r"Av[a-zA-Z]|"          # আ (Av) + consonant
    r"ev[a-zA-Z]|"          # বা (ev)
    r"[†‡][a-zA-Z]|"        # e-kar / oi-kar before consonant
    r"cÖ|"                  # প্র
    r"mvwnZ¨|"              # সাহিত্য
    r"evsjv|"               # বাংলা
    r"Avgvi|"               # আমার
    r"Avwg|"                # আমি
    r"cÖkœ|"                # প্রশ্ন
    r"[a-z]{2,}[A-Z][a-z]+" # mixed internal uppercase common in Bijoy (e.g. mvwnZ¨, KweZv)
    r")"
)

_WHITESPACE_LINE_RE = re.compile(r"[ \t\f\v]+")
_MULTI_NEWLINE_RE = re.compile(r"\n{3,}")


@dataclass(frozen=True)
class TextQualityAnalysis:
    normalized_text: str
    quality_score: float
    legacy_encoding_detected: bool
    needs_ocr: bool
    bengali_ratio: float
    replacement_ratio: float
    reasons: list[str] = field(default_factory=list)


def normalize_bengali_nfc(text: str) -> str:
    """Normalize text to Unicode NFC and clean horizontal whitespace while keeping paragraph breaks."""
    if not text:
        return ""
    nfc = unicodedata.normalize("NFC", text)
    # Normalize Windows/old Mac line endings
    nfc = nfc.replace("\r\n", "\n").replace("\r", "\n")
    # Remove NULL bytes and soft hyphens
    nfc = nfc.replace("\x00", "").replace("\u00ad", "")
    lines = [_WHITESPACE_LINE_RE.sub(" ", line).strip() for line in nfc.split("\n")]
    cleaned = "\n".join(lines)
    return _MULTI_NEWLINE_RE.sub("\n\n", cleaned).strip()


def _is_bengali_char(ch: str) -> bool:
    code = ord(ch)
    return 0x0980 <= code <= 0x09FF


def _is_bengali_dependent_sign(ch: str) -> bool:
    code = ord(ch)
    # Matras (া..ৌ), chandrabindu/anusvara/visarga (ঁ..ঃ), hasanta (্), au length mark (ৗ)
    return (0x09BE <= code <= 0x09CC) or code in (0x0981, 0x0982, 0x0983, 0x09CD, 0x09D7)


def analyze_bengali_text(text: str, quality_threshold: float = 0.70) -> TextQualityAnalysis:
    """Evaluate Unicode cleanliness, detect Bijoy/SutonnyMJ legacy garbling, and compute a 0..1 quality score."""
    normalized = normalize_bengali_nfc(text)
    if not normalized:
        return TextQualityAnalysis(
            normalized_text="",
            quality_score=0.0,
            legacy_encoding_detected=False,
            needs_ocr=True,
            bengali_ratio=0.0,
            replacement_ratio=0.0,
            reasons=["empty_or_whitespace_only"],
        )

    non_ws = [ch for ch in normalized if not ch.isspace()]
    total = len(non_ws)
    if total < 10:
        return TextQualityAnalysis(
            normalized_text=normalized,
            quality_score=0.15,
            legacy_encoding_detected=False,
            needs_ocr=True,
            bengali_ratio=0.0,
            replacement_ratio=0.0,
            reasons=["insufficient_text_length"],
        )

    bengali_count = sum(1 for ch in non_ws if _is_bengali_char(ch))
    ascii_alpha_count = sum(1 for ch in non_ws if ("A" <= ch <= "Z") or ("a" <= ch <= "z"))
    legacy_symbol_count = sum(1 for ch in non_ws if ch in _BIJOY_LEGACY_CHARS)
    replacement_count = sum(
        1
        for ch in non_ws
        if ch in ("\ufffd", "\u25a1", "\u25af")
        or (0xE000 <= ord(ch) <= 0xF8FF)
        or (unicodedata.category(ch) == "Cc")
    )

    # Check orphaned Bengali dependent marks (preceded by whitespace or start of string)
    orphaned_marks = 0
    for idx, ch in enumerate(normalized):
        if _is_bengali_dependent_sign(ch):
            if idx == 0 or normalized[idx - 1].isspace():
                orphaned_marks += 1

    bengali_ratio = bengali_count / total
    replacement_ratio = replacement_count / total
    legacy_symbol_ratio = legacy_symbol_count / total
    ascii_alpha_ratio = ascii_alpha_count / total
    orphaned_ratio = orphaned_marks / max(1, bengali_count)

    bijoy_hits = len(_BIJOY_SEQUENCES_RE.findall(normalized))
    mixed_case_words = len(re.findall(r"\b[a-zA-Z]*[a-z][A-Z][a-zA-Z]*\b", normalized))

    reasons: list[str] = []
    legacy_detected = False

    if legacy_symbol_ratio >= 0.03 or (bijoy_hits >= 2 and bengali_ratio < 0.25):
        legacy_detected = True
        reasons.append("bijoy_or_legacy_font_encoding_detected")
    elif mixed_case_words >= 3 and bengali_ratio < 0.15 and ascii_alpha_ratio > 0.45:
        legacy_detected = True
        reasons.append("suspected_ascii_mapped_bangla_garble")

    # Start from 1.0 and apply deterministic penalties
    score = 1.0
    if replacement_ratio > 0:
        score -= min(0.60, replacement_ratio * 3.0)
        reasons.append("replacement_or_control_characters_found")

    if orphaned_ratio > 0.05:
        score -= min(0.35, orphaned_ratio * 1.5)
        reasons.append("broken_bengali_matra_or_conjuncts")

    if legacy_detected:
        score = min(score, 0.35)
        score -= min(0.25, legacy_symbol_ratio * 2.0 + bijoy_hits * 0.03)

    # Penalize texts that have almost no valid Unicode Bengali or standard ASCII words
    valid_readable = sum(
        1
        for ch in non_ws
        if _is_bengali_char(ch)
        or ("A" <= ch <= "Z")
        or ("a" <= ch <= "z")
        or ("0" <= ch <= "9")
        or ch in "।॥.,;:?!-–—()[]{}\"'/%+*=<>@#&"
    )
    readable_ratio = valid_readable / total
    if readable_ratio < 0.75:
        score -= (0.75 - readable_ratio) * 0.8
        reasons.append("low_readable_character_ratio")

    score = round(max(0.0, min(1.0, score)), 3)
    needs_ocr = legacy_detected or score < quality_threshold

    return TextQualityAnalysis(
        normalized_text=normalized,
        quality_score=score,
        legacy_encoding_detected=legacy_detected,
        needs_ocr=needs_ocr,
        bengali_ratio=round(bengali_ratio, 3),
        replacement_ratio=round(replacement_ratio, 3),
        reasons=reasons,
    )
