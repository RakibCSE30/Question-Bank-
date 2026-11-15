from __future__ import annotations

import logging
import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models.curriculum import Chapter, Subject, SyllabusItem
from app.db.models.documents import Document, DocumentChunk
from app.db.models.logs import AIGenerationLog
from app.db.models.questions import PreviousQuestion
from app.schemas.analysis import (
    AuthorEntity,
    BanglaLiteratureAnalysisReport,
    LiteraryPeriodSummary,
    LiteraryWorkEntity,
    PreviousQuestionsTrendAnalysis,
    TopicPriorityItem,
)
from app.services.ai.base import LLMProvider
from app.services.ai.registry import get_llm_provider

logger = logging.getLogger(__name__)

# Standard BPSC Bangla Literature syllabus period divisions
STANDARD_BANGLA_PERIODS: list[dict[str, Any]] = [
    {
        "period_code": "ANCIENT",
        "period_name_bn": "প্রাচীন যুগ (চর্যাপদ)",
        "span_years": "৬৫০–১২০০ খ্রিস্টাব্দ (বা ৯৫০–১২০০)",
        "key_characteristics": "বাংলা সাহিত্যের আদি নিদর্শন; বৌদ্ধ সহজিয়া সাধকদের সাধন-সংগীত; সান্ধ্য বা আলো-আঁধারি ভাষা।",
        "core_topics": [
            "চর্যাপদের আবিষ্কার (১৯০৭) ও হরপ্রসাদ শাস্ত্রী",
            "চর্যাপদের ভাষা (ড. সুনীতিকুমার চট্টোপাধ্যায়ের ওডিবিএল)",
            "প্রধান পদকর্তা (লুইপা, কাহ্নপা, ভুসুকুপা, শবরপা)",
            "পদ সংখ্যা ও তিব্বতি অনুবাদ (প্রবোধচন্দ্র বাগচী)",
            "চর্যাপদের সমাজচিত্র ও ছন্দ (মাত্রাবৃত্ত)",
        ],
        "bcs_mark_weight": 2,
    },
    {
        "period_code": "MEDIEVAL",
        "period_name_bn": "মধ্যযুগ (১২০১–১৮০০)",
        "span_years": "১২০১–১৮০০ খ্রিস্টাব্দ (অন্ধকার যুগ: ১২০১–১৩৫০)",
        "key_characteristics": "ধর্মীয় ভাবাবেগ, দেবদেবী নির্ভর কাব্য, মঙ্গলকাব্য ও মুসলিম কবিদের মানবপ্রেমমূলক রোমান্টিক প্রণয়োপাখ্যান।",
        "core_topics": [
            "শ্রীকৃষ্ণকীর্তন কাব্য ও বড়ু চণ্ডীদাস",
            "বৈষ্ণব পদাবলী (বিদ্যাপতি, চণ্ডীদাস, জ্ঞানদাস, গোবিন্দদাস)",
            "মঙ্গলকাব্য (মনসামঙ্গল, চণ্ডীমঙ্গল, অন্নদামঙ্গল, ধর্মমঙ্গল)",
            "অনুবাদ সাহিত্য (কৃত্তিবাস ওঝা, কাশীরাম দাস, কবীন্দ্র পরমেশ্বর)",
            "আরাকান রাজসভা ও মুসলমান কবি (দৌলত কাজী, আলাওল, মাগন ঠাকুর)",
            "নাথ সাহিত্য, রোমান্টিক প্রণয়োপাখ্যান ও মর্সিয়া সাহিত্য",
            "যুগসন্ধিক্ষণের কবি ঈশ্বরচন্দ্র গুপ্ত",
        ],
        "bcs_mark_weight": 5,
    },
    {
        "period_code": "MODERN_EARLY",
        "period_name_bn": "আধুনিক যুগ: প্রথম পর্ব (১৮০১–১৯০০)",
        "span_years": "১৮০১–১৯০০ খ্রিস্টাব্দ",
        "key_characteristics": "গদ্যের সূচনা, মানবতাবাদ, পাশ্চাত্য শিক্ষা, রেনেসাঁস, দেশপ্রেম ও ব্যক্তিস্বাতন্ত্র্য।",
        "core_topics": [
            "ফোর্ট উইলিয়াম কলেজ ও বাংলা গদ্যের বিকাশ (উইলিয়াম কেরি, রামরাম বসু)",
            "শ্রীরামপুর মিশন ও সাময়িকপত্র (দিকদর্শন, সমাচার দর্পণ)",
            "ঈশ্বরচন্দ্র বিদ্যাসাগর ও যতিচিহ্নের সার্থক প্রয়োগ",
            "মাইকেল মধুসূদন দত্ত (মেঘনাদবধ কাব্য, সনেট, আধুনিক বাংলা নাটক ও প্রহসন)",
            "বঙ্কিমচন্দ্র চট্টোপাধ্যায় ও বাংলা উপন্যাসের ভিত্তি",
            "মীর মশাররফ হোসেন, দীনবন্ধু মিত্র ও নাট্য আন্দোলন",
            "বিহারীলাল চক্রবর্তী ও গীতি কবিতার সূচনা",
        ],
        "bcs_mark_weight": 5,
    },
    {
        "period_code": "MODERN_LATE",
        "period_name_bn": "আধুনিক যুগ: দ্বিতীয় পর্ব (১৯০১–১৯৪৭)",
        "span_years": "১৯০১–১৯৪৭ খ্রিস্টাব্দ",
        "key_characteristics": "রবীন্দ্র-নজরুল প্রতিভার বিকাশ, জাতীয়তাবাদী আন্দোলন, কল্লোলীয় আধুনিকতা ও রোমান্টিক বাস্তবতাবাদ।",
        "core_topics": [
            "রবীন্দ্রনাথ ঠাকুর (কাব্যগ্রন্থ, নাটক, ছোটগল্প, উপন্যাস, নোবেল পুরস্কার)",
            "কাজী নজরুল ইসলাম (বিদ্রোহী কবিতা, অগ্নিবীণা, নিষিদ্ধ গ্রন্থ, সাম্যবাদী চেতনা)",
            "শরৎচন্দ্র চট্টোপাধ্যায় ও কথাসাহিত্য",
            "আধুনিক পঞ্চপাণ্ডব (জীবনানন্দ দাশ, অমিয় চক্রবর্তী, বুদ্ধদেব বসু, সুধীন্দ্রনাথ দত্ত, বিষ্ণু দে)",
            "কল্লোল ও মুসলিম সাহিত্য সমাজ (শিখা পত্রিকা, বুদ্ধির মুক্তি আন্দোলন)",
            "জসীমউদ্দীন ও পল্লীসাহিত্য",
            "মানিক বন্দ্যোপাধ্যায়, তারাশঙ্কর বন্দ্যোপাধ্যায় ও বিভূতিভূষণ বন্দ্যোপাধ্যায়",
        ],
        "bcs_mark_weight": 5,
    },
    {
        "period_code": "CONTEMPORARY",
        "period_name_bn": "সমকালীন ও বাংলাদেশের সাহিত্য (১৯৪৭–বর্তমান)",
        "span_years": "১৯৪৭–বর্তমান",
        "key_characteristics": "দেশভাগ, ভাষা আন্দোলন, গণঅভ্যুত্থান, মুক্তিযুদ্ধ ও সমকালীন সমাজের নান্দনিক রূপায়ণ।",
        "core_topics": [
            "ভাষা আন্দোলনভিত্তিক সাহিত্য (কাব্য, নাটক যেমন কবর, উপন্যাস যেমন আরেক ফাল্গুন)",
            "মুক্তিযুদ্ধভিত্তিক উপন্যাস, কবিতা ও স্মৃতিচারণ",
            "প্রধান কবিগণ: শামসুর রাহমান, আল মাহমুদ, নির্মলেন্দু গুণ, সৈয়দ শামসুল হক",
            "প্রধান কথাসাহিত্যিক: শওকত ওসমান, হাসান আজিজুল হক, আখতারুজ্জামান ইলিয়াস, হুমায়ূন আহমেদ",
            "বাংলাদেশের নাটক, প্রবন্ধ ও গবেষণা সাহিত্য",
        ],
        "bcs_mark_weight": 3,
    },
]

# Baseline authentic previous BCS questions (Real 10th to 45th BCS sample items)
BASELINE_PREVIOUS_BCS_QUESTIONS: list[dict[str, Any]] = [
    {
        "bcs_batch": "45th BCS",
        "year": 2023,
        "question_text_bn": "চর্যাপদ কোন ছন্দে রচিত?",
        "options_json": {"ক": "অক্ষরবৃত্ত", "খ": "মাত্রাবৃত্ত", "গ": "স্বরবৃত্ত", "ঘ": "অমিত্রাক্ষর"},
        "correct_option": "খ",
        "question_type": "FACTUAL",
        "difficulty": "MEDIUM",
        "extracted_authors_works": {"work": "চর্যাপদ", "topic": "ছন্দ", "period": "প্রাচীন যুগ"},
        "page_number": 1,
    },
    {
        "bcs_batch": "44th BCS",
        "year": 2022,
        "question_text_bn": "'মহাভারতের কথা অমৃত সমান / কাশীরাম দাস কহে শুনে পুণ্যবান'—চরণ দুটির রচয়িতা কে?",
        "options_json": {"ক": "কৃত্তিবাস ওঝা", "খ": "মালাধর বসু", "গ": "কাশীরাম দাস", "ঘ": "কবীন্দ্র পরমেশ্বর"},
        "correct_option": "গ",
        "question_type": "STATEMENT",
        "difficulty": "EASY",
        "extracted_authors_works": {"author": "কাশীরাম দাস", "work": "মহাভারত অনুবাদ", "period": "মধ্যযুগ"},
        "page_number": 1,
    },
    {
        "bcs_batch": "43rd BCS",
        "year": 2021,
        "question_text_bn": "'পদ্মাবতী' কাব্যের রচয়িতা আলাওল কোন শতাব্দীর কবি?",
        "options_json": {"ক": "পঞ্চদশ শতক", "খ": "ষোড়শ শতক", "গ": "সপ্তদশ শতক", "ঘ": "অষ্টাদশ শতক"},
        "correct_option": "গ",
        "question_type": "CHRONOLOGY",
        "difficulty": "HARD",
        "extracted_authors_works": {"author": "আলাওল", "work": "পদ্মাবতী", "period": "মধ্যযুগ (আরাকান রাজসভা)"},
        "page_number": 2,
    },
    {
        "bcs_batch": "42nd BCS",
        "year": 2021,
        "question_text_bn": "বাংলা সাহিত্যের প্রথম মহাকাব্য কোনটি?",
        "options_json": {"ক": "মেঘনাদবধ কাব্য", "খ": "বৃত্রসংহার", "গ": "কুরুক্ষেত্র", "ঘ": "মহাশ্মশান"},
        "correct_option": "ক",
        "question_type": "FACTUAL",
        "difficulty": "EASY",
        "extracted_authors_works": {"author": "মাইকেল মধুসূদন দত্ত", "work": "মেঘনাদবধ কাব্য", "period": "আধুনিক যুগ"},
        "page_number": 3,
    },
    {
        "bcs_batch": "41st BCS",
        "year": 2020,
        "question_text_bn": "রবীন্দ্রনাথ ঠাকুর তাঁর কোন নাটকটি কাজী নজরুল ইসলামকে উৎসর্গ করেছিলেন?",
        "options_json": {"ক": "কালের যাত্রা", "খ": "বসন্ত", "গ": "তাসের দেশ", "ঘ": "রক্তকরবী"},
        "correct_option": "খ",
        "question_type": "AUTHOR_WORK",
        "difficulty": "MEDIUM",
        "extracted_authors_works": {"author": "রবীন্দ্রনাথ ঠাকুর", "work": "বসন্ত", "dedication": "কাজী নজরুল ইসলাম"},
        "page_number": 4,
    },
    {
        "bcs_batch": "40th BCS",
        "year": 2019,
        "question_text_bn": "'আরেক ফাল্গুন' উপন্যাসের পটভূমি কী?",
        "options_json": {"ক": "তেভাগা আন্দোলন", "খ": "ভাষা আন্দোলন", "গ": "ছয় দফা আন্দোলন", "ঘ": "মুক্তিযুদ্ধ"},
        "correct_option": "খ",
        "question_type": "CONCEPTUAL",
        "difficulty": "EASY",
        "extracted_authors_works": {"author": "জহির রায়হান", "work": "আরেক ফাল্গুন", "topic": "ভাষা আন্দোলন"},
        "page_number": 5,
    },
]


def seed_bangla_literature_baseline(db: Session) -> dict[str, Any]:
    """Seed standard chapters, syllabus items, and authentic previous questions for Bangla Literature."""
    subject = db.scalar(select(Subject).where(Subject.code == "BANGLA_LIT"))
    if not subject:
        subject = Subject(
            code="BANGLA_LIT",
            name_bn="বাংলা সাহিত্য",
            name_en="Bangla Literature",
            bcs_total_marks=20,
            is_active=True,
        )
        db.add(subject)
        db.flush()

    # 1. Seed or update standard 5 chapters
    created_chapters = 0
    chapter_map: dict[str, Chapter] = {}
    for idx, period in enumerate(STANDARD_BANGLA_PERIODS, start=1):
        chap = db.scalar(
            select(Chapter).where(
                Chapter.subject_id == subject.id,
                Chapter.order_index == idx,
            )
        )
        if not chap:
            chap = Chapter(
                subject_id=subject.id,
                order_index=idx,
                title_bn=period["period_name_bn"],
                title_en=period["period_code"],
            )
            db.add(chap)
            db.flush()
            created_chapters += 1
        chapter_map[period["period_code"]] = chap

        # Seed core syllabus topics under each chapter
        for topic_text in period["core_topics"]:
            existing_item = db.scalar(
                select(SyllabusItem).where(
                    SyllabusItem.subject_id == subject.id,
                    SyllabusItem.chapter_id == chap.id,
                    SyllabusItem.topic_bn == topic_text,
                )
            )
            if not existing_item:
                db.add(
                    SyllabusItem(
                        subject_id=subject.id,
                        chapter_id=chap.id,
                        topic_bn=topic_text,
                        topic_en=None,
                        weight_percentage=Decimal(str(round(100.0 / (len(STANDARD_BANGLA_PERIODS) * 5), 2))),
                        priority="HIGH" if idx in (1, 2, 4) else "MEDIUM",
                        priority_reason=f"বিসিএস সিলেবাসের মূল স্তম্ভ: {period['period_name_bn']}",
                        source_reference=f"{period['period_name_bn']} সিলেবাস মানদণ্ড",
                    )
                )

    # 2. Seed baseline previous BCS questions if none exist
    created_prev_q = 0
    for q_data in BASELINE_PREVIOUS_BCS_QUESTIONS:
        existing_q = db.scalar(
            select(PreviousQuestion).where(
                PreviousQuestion.subject_id == subject.id,
                PreviousQuestion.question_text_bn == q_data["question_text_bn"],
            )
        )
        if not existing_q:
            # Map chapter
            chap_order = 1
            if "মধ্যযুগ" in q_data.get("extracted_authors_works", {}).get("period", ""):
                chap_order = 2
            elif "আধুনিক" in q_data.get("extracted_authors_works", {}).get("period", ""):
                chap_order = 3 if "মধুসূদন" in q_data["question_text_bn"] else 4
            elif "ভাষা আন্দোলন" in q_data.get("extracted_authors_works", {}).get("topic", ""):
                chap_order = 5

            target_chap = db.scalar(
                select(Chapter).where(
                    Chapter.subject_id == subject.id,
                    Chapter.order_index == chap_order,
                )
            )

            prev_q = PreviousQuestion(
                subject_id=subject.id,
                chapter_id=target_chap.id if target_chap else None,
                bcs_batch=q_data["bcs_batch"],
                year=q_data["year"],
                question_text_bn=q_data["question_text_bn"],
                options_json=q_data["options_json"],
                correct_option=q_data["correct_option"],
                question_type=q_data["question_type"],
                difficulty=q_data["difficulty"],
                extracted_authors_works=q_data["extracted_authors_works"],
                page_number=q_data.get("page_number", 1),
            )
            db.add(prev_q)
            created_prev_q += 1

    db.commit()
    return {
        "subject_id": str(subject.id),
        "subject_code": subject.code,
        "created_chapters": created_chapters,
        "created_previous_questions": created_prev_q,
    }


def analyze_bangla_literature_topics_and_previous_trends(
    db: Session,
    subject_id: uuid.UUID,
) -> BanglaLiteratureAnalysisReport:
    """Analyze subject syllabus, extracted entities, and previous question patterns."""
    subject = db.scalar(select(Subject).where(Subject.id == subject_id))
    if not subject:
        raise ValueError(f"Subject {subject_id} not found")

    # 1. Fetch previous questions
    prev_questions = list(
        db.scalars(
            select(PreviousQuestion)
            .where(PreviousQuestion.subject_id == subject_id)
            .order_by(PreviousQuestion.bcs_batch.desc())
        ).all()
    )

    total_prev = len(prev_questions)
    factual_count = sum(1 for q in prev_questions if q.question_type == "FACTUAL")
    author_work_count = sum(1 for q in prev_questions if q.question_type == "AUTHOR_WORK")
    chronology_count = sum(1 for q in prev_questions if q.question_type == "CHRONOLOGY")
    conceptual_count = sum(1 for q in prev_questions if q.question_type in ("CONCEPTUAL", "STATEMENT", "ANALYTICAL"))

    author_freq: dict[str, int] = {}
    for q in prev_questions:
        if q.extracted_authors_works and isinstance(q.extracted_authors_works, dict):
            auth = q.extracted_authors_works.get("author")
            if auth:
                author_freq[auth] = author_freq.get(auth, 0) + 1

    sorted_authors = [
        {"author": k, "question_count": v}
        for k, v in sorted(author_freq.items(), key=lambda x: x[1], reverse=True)
    ]

    trends = PreviousQuestionsTrendAnalysis(
        total_previous_questions=total_prev,
        subject_code=subject.code,
        factual_percentage=round((factual_count / total_prev * 100), 1) if total_prev else 0.0,
        author_work_percentage=round((author_work_count / total_prev * 100), 1) if total_prev else 0.0,
        chronology_percentage=round((chronology_count / total_prev * 100), 1) if total_prev else 0.0,
        conceptual_percentage=round((conceptual_count / total_prev * 100), 1) if total_prev else 0.0,
        most_tested_authors=sorted_authors,
        frequently_tested_topics=[
            "চর্যাপদের আবিষ্কারক ও পদকর্তাগণ",
            "শ্রীকৃষ্ণকীর্তন ও মঙ্গলকাব্যের শাখা",
            "মাইকেল মধুসূদনের কাব্য ও প্রহসন",
            "রবীন্দ্রনাথ ঠাকুরের নোবেল ও উৎসর্গকৃত নাটক",
            "কাজী নজরুল ইসলামের নিষিদ্ধ গ্রন্থ ও সাম্যবাদী কাব্য",
            "ভাষা আন্দোলন ও মুক্তিযুদ্ধভিত্তিক উপন্যাস",
        ],
        underrepresented_topics=[
            "নাথ সাহিত্য ও ময়নামতীর গান",
            "ফোর্ট উইলিয়াম কলেজের পাঠ্যপুস্তক রচয়িতাগণ",
            "কল্লোল যুগের কবিদের নান্দনিক আন্দোলন",
            "উনিশ শতকের মুসলমান সাহিত্যিকদের প্রবন্ধ",
        ],
    )

    # 2. Build periods list
    periods = [LiteraryPeriodSummary(**p) for p in STANDARD_BANGLA_PERIODS]

    # 3. Topic priorities from database
    syllabus_items = list(
        db.scalars(
            select(SyllabusItem)
            .where(SyllabusItem.subject_id == subject_id)
            .order_by(SyllabusItem.created_at.asc())
        ).all()
    )

    chapters = {c.id: c for c in db.scalars(select(Chapter).where(Chapter.subject_id == subject_id)).all()}
    topic_priorities: list[TopicPriorityItem] = []
    for item in syllabus_items:
        chap_title = chapters[item.chapter_id].title_bn if item.chapter_id in chapters else "সাধারণ"
        topic_priorities.append(
            TopicPriorityItem(
                topic_bn=item.topic_bn,
                chapter_name_bn=chap_title,
                priority=item.priority,  # type: ignore
                priority_reason=item.priority_reason or "সিলেবাস নির্দেশিত গুরুত্ব",
                weight_percentage=float(item.weight_percentage),
                previous_bcs_frequency=sum(1 for q in prev_questions if item.topic_bn in q.question_text_bn),
            )
        )

    # 4. Standard verified entities for Bangla literature baseline
    sample_authors = [
        AuthorEntity(
            name_bn="হরপ্রসাদ শাস্ত্রী",
            pen_name_or_title="মহামহোপাধ্যায়",
            era_or_period="প্রাচীন যুগ আবিষ্কারক ও আধুনিক গবেষক",
            notable_works=["হাজার বছরের পুরাণ বাঙ্গালা ভাষায় রচিত বৌদ্ধ গান ও দোহা", "বেনের মেয়ে"],
            significance="১৯০৭ সালে নেপালের রাজদরবারের রয়েল লাইব্রেরি থেকে চর্যাপদ আবিষ্কার করেন।",
        ),
        AuthorEntity(
            name_bn="বড়ু চণ্ডীদাস",
            pen_name_or_title="অনন্ত বড়ু চণ্ডীদাস",
            era_or_period="মধ্যযুগ",
            notable_works=["শ্রীকৃষ্ণকীর্তন কাব্য"],
            significance="মধ্যযুগের প্রথম এবং একমাত্র বাংলা ভাষায় রচিত একক কবির প্রামাণ্য গ্রন্থ।",
        ),
        AuthorEntity(
            name_bn="আলাওল",
            pen_name_or_title="পণ্ডিত আলাওল",
            era_or_period="মধ্যযুগ (সপ্তদশ শতক)",
            notable_works=["পদ্মাবতী", "সতীময়না ও লোরচন্দ্রানী", "সয়ফুলমুলুক বদিউজ্জামাল", "তোহফা"],
            significance="আরাকান রাজসভার শ্রেষ্ঠ বাঙালি কবি; হিন্দি পদুমাবতের বাংলা কাব্যানুবাদ।",
        ),
        AuthorEntity(
            name_bn="মাইকেল মধুসূদন দত্ত",
            pen_name_or_title="মাইকেল (খ্রিস্টধর্ম গ্রহণের পর)",
            era_or_period="আধুনিক যুগ: প্রথম পর্ব",
            notable_works=["মেঘনাদবধ কাব্য", "শর্মিষ্ঠা", "পদ্মাবতী", "একেই কি বলে সভ্যতা", "বুড়ো শালিকের ঘাড়ে রোঁ"],
            significance="বাংলা সাহিত্যের প্রথম মহাকবি, অমিত্রাক্ষর ছন্দ ও বাংলা সনেটের প্রবর্তক।",
        ),
        AuthorEntity(
            name_bn="রবীন্দ্রনাথ ঠাকুর",
            pen_name_or_title="বিশ্বকবি / ভানুসিংহ ঠাকুর",
            era_or_period="আধুনিক যুগ: দ্বিতীয় পর্ব",
            notable_works=["গীতাঞ্জলি", "বলাকা", "সোনার তরী", "গোরা", "ডাকঘর", "রক্তকরবী"],
            significance="১৯১৩ সালে নোবেল পুরস্কার বিজয়ী; বাংলা সাহিত্যকে বিশ্বদরবারে প্রতিষ্ঠা করেন।",
        ),
        AuthorEntity(
            name_bn="কাজী নজরুল ইসলাম",
            pen_name_or_title="বিদ্রোহী কবি / ধুমকেতু",
            era_or_period="আধুনিক যুগ: দ্বিতীয় পর্ব",
            notable_works=["অগ্নিবীণা", "বিষের বাঁশী", "রিক্তের বেদন", "মৃত্যুক্ষুধা", "কুহেলিকা"],
            significance="বাংলাদেশের জাতীয় কবি; বাংলা কাব্যে বিদ্রোহ, সাম্য ও মানবতার অনন্য রূপকার।",
        ),
    ]

    sample_works = [
        LiteraryWorkEntity(
            title_bn="চর্যাপদ",
            author_name_bn="লুইপা, কাহ্নপা প্রমুখ (মোট ২৪ জন পদকর্তা)",
            genre="গীতিকাব্য / সাধন-সংগীত",
            publication_year_or_era="১৯১৬ (বঙ্গীয় সাহিত্য পরিষদ থেকে হরপ্রসাদ শাস্ত্রী কর্তৃক প্রকাশ)",
            major_characters=["শবর-শবরী", "ডোম ও কাপালিক সাধক"],
            themes=["বৌদ্ধ সহজিয়া কায়াসাধনা ও তৎকালীন প্রান্তিক জনগোষ্ঠীর জীবনযাপন"],
        ),
        LiteraryWorkEntity(
            title_bn="শ্রীকৃষ্ণকীর্তন",
            author_name_bn="বড়ু চণ্ডীদাস",
            genre="নাট্যগীতি কাব্য",
            publication_year_or_era="১৩৫০–১৪০০ খ্রিস্টাব্দ (১৯০৯ সালে বসন্তরঞ্জন রায় বিদ্বদ্বল্লভ কর্তৃক বাঁকুড়া থেকে আবিষ্কার)",
            major_characters=["রাধা", "কৃষ্ণ", "বড়াই"],
            themes=["রাধা-কৃষ্ণের প্রেমলীলা ও বিরহভাব"],
        ),
        LiteraryWorkEntity(
            title_bn="মেঘনাদবধ কাব্য",
            author_name_bn="মাইকেল মধুসূদন দত্ত",
            genre="মহাকাব্য (৯টি সর্গ)",
            publication_year_or_era="১৮৬১ খ্রিস্টাব্দ",
            major_characters=["মেঘনাদ (ইন্দ্রজিৎ)", "প্রমীলা", "রাবণ", "লক্ষ্মণ", "রাম"],
            themes=["রামায়ণের নবমূল্যায়ন, দেশপ্রেম ও নিয়তির বিরুদ্ধে বীরোচিত লড়াই"],
        ),
        LiteraryWorkEntity(
            title_bn="অগ্নিবীণা",
            author_name_bn="কাজী নজরুল ইসলাম",
            genre="কাব্যগ্রন্থ (১২টি কবিতা)",
            publication_year_or_era="১৯২২ খ্রিস্টাব্দ",
            major_characters=[],
            themes=["প্রলয়োল্লাস, বিদ্রোহ, ধূমকেতু ও সাম্রাজ্যবাদবিরোধী চেতনা"],
        ),
    ]

    return BanglaLiteratureAnalysisReport(
        subject_code=subject.code,
        subject_name_bn=subject.name_bn,
        authors=sample_authors,
        literary_works=sample_works,
        periods=periods,
        topic_priorities=topic_priorities,
        previous_trends=trends,
    )
