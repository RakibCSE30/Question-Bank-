from __future__ import annotations

import unicodedata

from app.services.ingestion.bengali_unicode import analyze_bengali_text, normalize_bengali_nfc
from app.services.ingestion.chunker import ExtractedPage, chunk_pages, split_sentences_bengali_safe


def test_nfc_normalization_for_bengali() -> None:
    # Synthetic decomposed (NFD-style) vs composed (NFC) check using standard Unicode normalization
    sample = "বাংলা সাহিত্য ও ব্যাকরণ।"
    decomposed = unicodedata.normalize("NFD", sample)
    normalized = normalize_bengali_nfc(decomposed)
    assert unicodedata.is_normalized("NFC", normalized)
    assert normalized == unicodedata.normalize("NFC", sample)


def test_clean_unicode_bangla_scores_high() -> None:
    # Synthetic test fixture (not from any real book)
    clean_fixture = (
        "প্রথম অধ্যায়: বাংলা ভাষার ইতিহাস ও প্রাচীন নিদর্শন। "
        "এই অনুচ্ছেদটি শুধুমাত্র ইউনিকোড বাংলা যাচাইয়ের জন্য একটি কৃত্রিম নমুনা। "
        "এতে যুক্তাক্ষর যেমন ক্ষ, জ্ঞ, ন্ত, ন্দ এবং দাঁড়ি সঠিকভাবে রয়েছে।"
    )
    analysis = analyze_bengali_text(clean_fixture, quality_threshold=0.70)
    assert analysis.legacy_encoding_detected is False
    assert analysis.needs_ocr is False
    assert analysis.quality_score >= 0.85
    assert analysis.bengali_ratio > 0.70


def test_bijoy_style_garbled_fixture_is_flagged_for_ocr() -> None:
    # Synthetic Bijoy/SutonnyMJ-style garbled test fixture (not real book content)
    bijoy_fixture = (
        "Avgvi †mvbvi evsjv, Avwg †Zvgvq fv‡jvevwm। "
        "cÖkœcÎ I mvwnZ¨ cvV¨µg hvPvB‡qi Rb¨ GB K…wÎg bgybv e¨eüZ n‡q‡Q।"
    )
    analysis = analyze_bengali_text(bijoy_fixture, quality_threshold=0.70)
    assert analysis.legacy_encoding_detected is True
    assert analysis.needs_ocr is True
    assert analysis.quality_score < 0.70
    assert any("bijoy" in r or "garble" in r for r in analysis.reasons)


def test_replacement_char_garble_scores_low() -> None:
    # Synthetic corrupted-extraction fixture
    corrupted_fixture = "\ufffd\ufffd\ufffd\ufffd কিছু শব্দ \ufffd\ufffd অস্পষ্ট \ufffd\ufffd\ufffd"
    analysis = analyze_bengali_text(corrupted_fixture, quality_threshold=0.70)
    assert analysis.needs_ocr is True
    assert analysis.quality_score < 0.70


def test_chunker_preserves_page_heading_and_never_splits_bengali_sentence() -> None:
    # Synthetic multi-sentence Bangla fixture
    sentences = [
        "প্রথম বাক্যটি শুধুমাত্র পরীক্ষার জন্য তৈরি করা হয়েছে।",
        "দ্বিতীয় বাক্যে কোনো প্রকৃত বইয়ের তথ্য নেই এবং এটি যথেষ্ট দীর্ঘ রাখা হয়েছে।",
        "তৃতীয় বাক্যটিও সম্পূর্ণভাবে আলাদা থাকতে হবে এবং মাঝপথে ভাঙা যাবে না।",
        "চতুর্থ বাক্যটি শেষ অনুচ্ছেদের অংশ হিসেবে যুক্ত রয়েছে।",
    ]
    page = ExtractedPage(
        page_number=7,
        heading_path="অধ্যায় ২: নমুনা শিরোনাম",
        text=" ".join(sentences),
        confidence=0.95,
    )

    chunks = chunk_pages([page], max_chars=130)
    assert len(chunks) >= 2

    reconstructed_sentences: list[str] = []
    for chunk in chunks:
        assert chunk.page_number == 7
        assert chunk.heading_path == "অধ্যায় ২: নমুনা শিরোনাম"
        # Every chunk must end cleanly at a Bengali sentence terminator (।)
        assert chunk.content_nfc.endswith("।")
        reconstructed_sentences.extend(split_sentences_bengali_safe(chunk.content_nfc))

    assert reconstructed_sentences == sentences


def test_sentence_splitter_handles_missing_space_after_danda_and_abbreviations() -> None:
    ocr_text = "ড. মুহম্মদ শহীদুল্লাহ ভাষা নিয়ে গবেষণা করেন।দ্বিতীয় বাক্যে কোনো ফাঁকা ছিল না।"
    parts = split_sentences_bengali_safe(ocr_text)
    assert len(parts) == 2
    assert parts[0] == "ড. মুহম্মদ শহীদুল্লাহ ভাষা নিয়ে গবেষণা করেন।"
    assert parts[1] == "দ্বিতীয় বাক্যে কোনো ফাঁকা ছিল না।"

