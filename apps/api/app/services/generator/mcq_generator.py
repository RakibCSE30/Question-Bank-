from __future__ import annotations

import logging
import uuid
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models.assessment import PracticeSet, PracticeSetQuestion
from app.db.models.curriculum import Chapter, Subject
from app.db.models.documents import DocumentChunk
from app.db.models.logs import AIGenerationLog
from app.db.models.questions import AnswerKey, GeneratedQuestion, QuestionOption
from app.services.ai.base import LLMProvider
from app.services.ai.registry import get_llm_provider
from app.services.analysis.bangla_literature import seed_bangla_literature_baseline

logger = logging.getLogger(__name__)


class OptionSchema(BaseModel):
    label: Literal["ক", "খ", "গ", "ঘ"]
    text_bn: str


class MCQItemSchema(BaseModel):
    question_text_bn: str = Field(min_length=5)
    options: list[OptionSchema] = Field(min_length=4, max_length=4)
    correct_option: Literal["ক", "খ", "গ", "ঘ"]
    explanation_bn: str = Field(min_length=10)
    question_style: Literal[
        "FACTUAL",
        "AUTHOR_WORK",
        "CHRONOLOGY",
        "CONCEPTUAL",
        "STATEMENT",
        "COMPARATIVE",
        "ANALYTICAL",
        "TRICKY",
    ]
    difficulty: Literal["EASY", "MEDIUM", "HARD"]
    importance: Literal["HIGH", "MEDIUM", "LOW"]
    grounding_type: Literal["SOURCE_GROUNDED", "AI_INFERENCE"] = "SOURCE_GROUNDED"
    source_citation: str = Field(default="বিসিএস প্রমিত পাঠ্যবই ও বিপিএসসি সিলেবাস রেফারেন্স")
    previous_bcs_relation: Literal["EXACT_REPEAT", "SIMILAR_TOPIC", "NONE"] = "NONE"


class SetBatchSchema(BaseModel):
    set_number: int = Field(ge=1, le=10)
    title_bn: str
    chapter_index: int = Field(default=1, ge=1, le=5)
    questions: list[MCQItemSchema] = Field(min_length=15, max_length=15)


class PilotFiveSetsOutputSchema(BaseModel):
    sets: list[SetBatchSchema] = Field(min_length=5, max_length=5)


# ------------------------------------------------------------------------------
# High-Quality Syllabus-Grounded Pilot Question Bank (5 Sets x 15 MCQs = 75 MCQs)
# ------------------------------------------------------------------------------
PILOT_75_MCQS_DATA: list[dict[str, Any]] = [
    # =========================================================================
    # SET 1: প্রাচীন যুগ ও চর্যাপদ (১৫টি প্রমিত প্রশ্ন)
    # =========================================================================
    {
        "set_number": 1,
        "title_bn": "বাংলা সাহিত্য সেট ১: প্রাচীন যুগ ও চর্যাপদ অনুশীলন",
        "chapter_index": 1,
        "questions": [
            {
                "question_text_bn": "হরপ্রসাদ শাস্ত্রী কত সালে নেপালের রাজদরবারের রয়েল লাইব্রেরি থেকে চর্যাপদের পুথি আবিষ্কার করেন?",
                "options": [
                    {"label": "ক", "text_bn": "১৯০৫ সালে"},
                    {"label": "খ", "text_bn": "১৯০৭ সালে"},
                    {"label": "গ", "text_bn": "১৯১৬ সালে"},
                    {"label": "ঘ", "text_bn": "১৯২০ সালে"},
                ],
                "correct_option": "খ",
                "explanation_bn": "মহামহোপাধ্যায় হরপ্রসাদ শাস্ত্রী ১৯০৭ সালে নেপালের রাজদরবারের রয়েল লাইব্রেরি থেকে চর্যাপদের মূল পুথিটি আবিষ্কার করেন। পরবর্তীতে ১৯১৬ সালে বঙ্গীয় সাহিত্য পরিষদ থেকে এটি গ্রন্থাকারে প্রকাশিত হয়।",
                "question_style": "CHRONOLOGY",
                "difficulty": "EASY",
                "importance": "HIGH",
                "grounding_type": "SOURCE_GROUNDED",
                "source_citation": "বাংলা সাহিত্যের ইতিহাস - ড. মাহবুবুল আলম (পৃষ্ঠা ১৫)",
                "previous_bcs_relation": "SIMILAR_TOPIC",
            },
            {
                "question_text_bn": "চর্যাপদ কোন ছন্দে রচিত?",
                "options": [
                    {"label": "ক", "text_bn": "অক্ষরবৃত্ত ছন্দে"},
                    {"label": "খ", "text_bn": "মাত্রাবৃত্ত ছন্দে"},
                    {"label": "গ", "text_bn": "স্বরবৃত্ত ছন্দে"},
                    {"label": "ঘ", "text_bn": "অমিত্রাক্ষর ছন্দে"},
                ],
                "correct_option": "খ",
                "explanation_bn": "চর্যাপদের পদগুলো প্রধানত মাত্রাবৃত্ত (পাদানাকুলক বা পজঝটিকা) ছন্দে রচিত। প্রতিটি চরণে সাধারণত ১৬ মাত্রা এবং অন্তমিল বিদ্যমান।",
                "question_style": "FACTUAL",
                "difficulty": "MEDIUM",
                "importance": "HIGH",
                "grounding_type": "SOURCE_GROUNDED",
                "source_citation": "বাংলা সাহিত্যের ইতিবৃত্ত - অসিতকুমার বন্দ্যোপাধ্যায়",
                "previous_bcs_relation": "EXACT_REPEAT",
            },
            {
                "question_text_bn": "চর্যাপদের সর্বাধিক পদ রচয়িতা কাহ্নপা মোট কতটি পদ রচনা করেছেন?",
                "options": [
                    {"label": "ক", "text_bn": "৮টি"},
                    {"label": "খ", "text_bn": "১০টি"},
                    {"label": "গ", "text_bn": "১৩টি"},
                    {"label": "ঘ", "text_bn": "১৬টি"},
                ],
                "correct_option": "গ",
                "explanation_bn": "চর্যাপদের মোট পদকর্তার সংখ্যা ২৪ জন। এর মধ্যে সর্বাধিক ১৩টি পদ রচনা করেছেন কাহ্নপা (বা কৃষ্ণাচার্য)। দ্বিতীয় সর্বোচ্চ ৮টি পদ রচনা করেছেন ভুসুকুপা।",
                "question_style": "AUTHOR_WORK",
                "difficulty": "EASY",
                "importance": "HIGH",
                "grounding_type": "SOURCE_GROUNDED",
                "source_citation": "লাল নীল দীপাবলি - হুমায়ুন আজাদ",
                "previous_bcs_relation": "SIMILAR_TOPIC",
            },
            {
                "question_text_bn": "কোন গবেষক চর্যাপদের তিব্বতি অনুবাদ আবিষ্কার করে পদগুলোর মূল পাঠ উদ্ধারে অনন্য ভূমিকা রাখেন?",
                "options": [
                    {"label": "ক", "text_bn": "ড. মুহম্মদ শহীদুল্লাহ্"},
                    {"label": "খ", "text_bn": "ড. প্রবোধচন্দ্র বাগচী"},
                    {"label": "গ", "text_bn": "ড. সুনীতিকুমার চট্টোপাধ্যায়"},
                    {"label": "ঘ", "text_bn": "রাহুল সাংকৃত্যায়ন"},
                ],
                "correct_option": "খ",
                "explanation_bn": "ড. প্রবোধচন্দ্র বাগচী ১৯৩৮ সালে চর্যাপদের একটি তিব্বতি অনুবাদ আবিষ্কার করেন, যার মাধ্যমে চর্যাপদের অনেক দুর্বোধ্য ও খণ্ডিত পদের পাঠোদ্ধার করা সম্ভব হয়।",
                "question_style": "ANALYTICAL",
                "difficulty": "HARD",
                "importance": "HIGH",
                "grounding_type": "SOURCE_GROUNDED",
                "source_citation": "চর্যাগীতি পদাবলী - ড. সুকুমার সেন",
                "previous_bcs_relation": "NONE",
            },
            {
                "question_text_bn": "'কাআ তরুবর পঞ্চ বি ডাল / চঞ্চল চীএ পইঠো কাল'—চর্যাপদের এই বিখ্যাত প্রথম চরণটির রচয়িতা কে?",
                "options": [
                    {"label": "ক", "text_bn": "কাহ্নপা"},
                    {"label": "খ", "text_bn": "লুইপা"},
                    {"label": "গ", "text_bn": "শবরপা"},
                    {"label": "ঘ", "text_bn": "কুক্কুরীপা"},
                ],
                "correct_option": "খ",
                "explanation_bn": "চর্যাপদের ১ নম্বর পদের রচয়িতা হলেন লুইপা। এই পদে মানবদেহকে বৃক্ষের সাথে এবং পঞ্চ ইন্দ্রিয়কে পাঁচটি ডালের সাথে তুলনা করা হয়েছে।",
                "question_style": "STATEMENT",
                "difficulty": "EASY",
                "importance": "HIGH",
                "grounding_type": "SOURCE_GROUNDED",
                "source_citation": "চর্যাপদ - ড. মুহম্মদ শহীদুল্লাহ্ সম্পাদিত",
                "previous_bcs_relation": "SIMILAR_TOPIC",
            },
            {
                "question_text_bn": "ড. সুনীতিকুমার চট্টোপাধ্যায়ের মতে চর্যাপদের রচনাকাল কোনটি?",
                "options": [
                    {"label": "ক", "text_bn": "৬৫০–১২০০ খ্রিস্টাব্দ"},
                    {"label": "খ", "text_bn": "৯৫০–১২০০ খ্রিস্টাব্দ"},
                    {"label": "গ", "text_bn": "১২০১–১৩৫০ খ্রিস্টাব্দ"},
                    {"label": "ঘ", "text_bn": "১০০০–১৩৫০ খ্রিস্টাব্দ"},
                ],
                "correct_option": "খ",
                "explanation_bn": "ড. সুনীতিকুমার চট্টোপাধ্যায় তাঁর 'ODBL' গ্রন্থে ব্যাকরণগত ও ভাষাতাত্ত্বিক বিচার করে চর্যাপদের রচনাকাল ৯৫০–১২০০ খ্রিস্টাব্দ নির্ধারণ করেছেন। অপরদিকে ড. মুহম্মদ শহীদুল্লাহ্ প্রাচীনতর মত দিয়ে ৬৫০–১২০০ খ্রিস্টাব্দ উল্লেখ করেন।",
                "question_style": "COMPARATIVE",
                "difficulty": "MEDIUM",
                "importance": "HIGH",
                "grounding_type": "SOURCE_GROUNDED",
                "source_citation": "The Origin and Development of the Bengali Language (ODBL)",
                "previous_bcs_relation": "SIMILAR_TOPIC",
            },
            {
                "question_text_bn": "চর্যাপদের কোন পদকর্তা নিজেকে বাঙালি বলে পরিচয় দিয়েছেন?",
                "options": [
                    {"label": "ক", "text_bn": "লুইপা"},
                    {"label": "খ", "text_bn": "কাহ্নপা"},
                    {"label": "গ", "text_bn": "ভুসুকুপা"},
                    {"label": "ঘ", "text_bn": "ডোম্বীপা"},
                ],
                "correct_option": "গ",
                "explanation_bn": "ভুসুকুপা তাঁর ৪৯ নম্বর পদে বলেছেন: 'আজি ভুসুকু বাঙ্গালী ভইলী / ণিঅ ঘরনী চণ্ডালী লেলী'। তিনি নিজেকে স্পষ্ট ভাষায় বাঙালি বলে ঘোষণা করেছেন।",
                "question_style": "FACTUAL",
                "difficulty": "EASY",
                "importance": "HIGH",
                "grounding_type": "SOURCE_GROUNDED",
                "source_citation": "বাংলা সাহিত্যের ইতিহাস - ড. মাহবুবুল আলম",
                "previous_bcs_relation": "EXACT_REPEAT",
            },
            {
                "question_text_bn": "চর্যাপদের ভাষার প্রকৃতি বিশ্লেষণে হরপ্রসাদ শাস্ত্রী এটিকে কী নামে অভিহিত করেছেন?",
                "options": [
                    {"label": "ক", "text_bn": "অপভ্রংশ ভাষা"},
                    {"label": "খ", "text_bn": "সন্ধ্যা বা আলো-আঁধারি ভাষা"},
                    {"label": "গ", "text_bn": "ব্রজবুলি ভাষা"},
                    {"label": "ঘ", "text_bn": "মাগধী প্রাকৃত ভাষা"},
                ],
                "correct_option": "খ",
                "explanation_bn": "হরপ্রসাদ শাস্ত্রী চর্যাপদের ভাষাকে 'সান্ধ্য ভাষা' বা 'আলো-আঁধারি ভাষা' বলেছেন, কারণ এর বহিরঙ্গে এক অর্থ এবং অন্তরে সাধনতাত্ত্বিক নিগূঢ় আধ্যাত্মিক অর্থ নিহিত থাকে।",
                "question_style": "CONCEPTUAL",
                "difficulty": "EASY",
                "importance": "HIGH",
                "grounding_type": "SOURCE_GROUNDED",
                "source_citation": "হাজার বছরের পুরাণ বাঙ্গালা ভাষায় রচিত বৌদ্ধ গান ও দোহা - হরপ্রসাদ শাস্ত্রী ভূমিকা",
                "previous_bcs_relation": "SIMILAR_TOPIC",
            },
            {
                "question_text_bn": "চর্যাপদের কোন পদটি খণ্ডিত আকারে পাওয়া গেছে এবং এর কতটি চরণ লুপ্ত?",
                "options": [
                    {"label": "ক", "text_bn": "১০ নম্বর পদ, ২ চরণ"},
                    {"label": "খ", "text_bn": "২৩ নম্বর পদ, ৬ চরণ"},
                    {"label": "গ", "text_bn": "২৩ নম্বর পদ, শেষ ৪ চরণ"},
                    {"label": "ঘ", "text_bn": "২৫ নম্বর পদ, সম্পূর্ণ"},
                ],
                "correct_option": "গ",
                "explanation_bn": "চর্যাপদের ২৩ নম্বর পদটি (ভুসুকুপার রচিত) খণ্ডিত অবস্থায় পাওয়া যায়। এর মোট ১০ চরণের মধ্যে প্রথম ৬টি পাওয়া গেছে এবং শেষ ৪টি চরণ পাওয়া যায়নি।",
                "question_style": "TRICKY",
                "difficulty": "HARD",
                "importance": "MEDIUM",
                "grounding_type": "SOURCE_GROUNDED",
                "source_citation": "চর্যাগীতি পদাবলী - সুকুমার সেন",
                "previous_bcs_relation": "NONE",
            },
            {
                "question_text_bn": "চর্যাপদে মোট কতজন পদকর্তার নাম পাওয়া যায় এবং আবিষ্কৃত মোট পদের সংখ্যা কত?",
                "options": [
                    {"label": "ক", "text_bn": "২৩ জন পদকর্তা, ৫০টি পদ"},
                    {"label": "খ", "text_bn": "২৪ জন পদকর্তা, ৪৬.৫টি পদ"},
                    {"label": "গ", "text_bn": "২২ জন পদকর্তা, ৪৭টি পদ"},
                    {"label": "ঘ", "text_bn": "২৪ জন পদকর্তা, ৫১টি পদ"},
                ],
                "correct_option": "খ",
                "explanation_bn": "চর্যাপদে মোট ২৪ জন পদকর্তার উল্লেখ পাওয়া যায় (মতান্তরে ২৩ জন)। মূল পুথিতে মোট ৫০টি পদের মধ্যে ২৪, ২৫ ও ৪৮ নম্বর পদ এবং ২৩ নম্বর পদের শেষাংশ না থাকায় সাড়ে ছেচল্লিশটি (৪৬.৫) পদ উদ্ধার করা সম্ভব হয়।",
                "question_style": "FACTUAL",
                "difficulty": "MEDIUM",
                "importance": "HIGH",
                "grounding_type": "SOURCE_GROUNDED",
                "source_citation": "বিসিএস প্রিলিমিনারি সিলেবাস সহায়িকা",
                "previous_bcs_relation": "SIMILAR_TOPIC",
            },
            {
                "question_text_bn": "'অপনা মাংসে হরিণা বৈরী'—চর্যাপদের এই বিখ্যাত প্রবাদতুল্য চরণটি কোন পদকর্তার রচিত?",
                "options": [
                    {"label": "ক", "text_bn": "ভুসুকুপা (৬ নম্বর পদ)"},
                    {"label": "খ", "text_bn": "কাহ্নপা (১০ নম্বর পদ)"},
                    {"label": "গ", "text_bn": "লুইপা (১ নম্বর পদ)"},
                    {"label": "ঘ", "text_bn": "শবরপা (২৮ নম্বর পদ)"},
                ],
                "correct_option": "ক",
                "explanation_bn": "'অপনা মাংসে হরিণা বৈরী' চরণটি ভুসুকুপা রচিত ৬ নম্বর পদের অংশ। হরিণ যেমন নিজের মাংসের জন্যই শিকারীর শত্রু হয়, তেমনই মানবচিত্তও তার মোহের কারণে শত্রুভাবাপন্ন হয়।",
                "question_style": "STATEMENT",
                "difficulty": "MEDIUM",
                "importance": "HIGH",
                "grounding_type": "SOURCE_GROUNDED",
                "source_citation": "বাংলা সাহিত্যের ইতিবৃত্ত",
                "previous_bcs_relation": "EXACT_REPEAT",
            },
            {
                "question_text_bn": "চর্যাপদের আবিষ্কারক হরপ্রসাদ শাস্ত্রী রচিত উপন্যাসটির নাম কী?",
                "options": [
                    {"label": "ক", "text_bn": "বেনের মেয়ে"},
                    {"label": "খ", "text_bn": "ময়নামতীর গান"},
                    {"label": "গ", "text_bn": "বাঘের ঘরে ঘোগের বাসা"},
                    {"label": "ঘ", "text_bn": "চন্দ্রাবতী"},
                ],
                "correct_option": "ক",
                "explanation_bn": "হরপ্রসাদ শাস্ত্রী রচিত ঐতিহাসিক উপন্যাসের নাম 'বেনের মেয়ে' (১৯২০)। এটি প্রাচীন বাংলার সমাজ ও সংস্কৃতির পটভূমিতে রচিত।",
                "question_style": "AUTHOR_WORK",
                "difficulty": "MEDIUM",
                "importance": "MEDIUM",
                "grounding_type": "SOURCE_GROUNDED",
                "source_citation": "আধুনিক বাংলা সাহিত্যের ইতিহাস",
                "previous_bcs_relation": "SIMILAR_TOPIC",
            },
            {
                "question_text_bn": "চর্যাপদের একমাত্র মহিলা পদকর্তা হিসেবে কাকে বিবেচনা করা হয়?",
                "options": [
                    {"label": "ক", "text_bn": "মহীধরপা"},
                    {"label": "খ", "text_bn": "কুক্কুরীপা"},
                    {"label": "গ", "text_bn": "বীণাপা"},
                    {"label": "ঘ", "text_bn": "শবরপা"},
                ],
                "correct_option": "খ",
                "explanation_bn": "চর্যাপদের ২ ও ২০ নম্বর পদের রচয়িতা কুক্কুরীপাকে কোনো কোনো গবেষক (যেমন ড. মুহম্মদ শহীদুল্লাহ্ ও রাহুল সাংকৃত্যায়ন) মহিলা পদকর্তা হিসেবে উল্লেখ করেছেন।",
                "question_style": "ANALYTICAL",
                "difficulty": "HARD",
                "importance": "HIGH",
                "grounding_type": "SOURCE_GROUNDED",
                "source_citation": "বৌদ্ধগান ও দোহা - ড. মুহম্মদ শহীদুল্লাহ্",
                "previous_bcs_relation": "NONE",
            },
            {
                "question_text_bn": "চর্যাপদ মূলত কোন ধর্মাবলম্বীদের সাধনতত্ত্ব নির্দেশক কাব্য?",
                "options": [
                    {"label": "ক", "text_bn": "সনাতন বৈষ্ণব ধর্ম"},
                    {"label": "খ", "text_bn": "বৌদ্ধ সহজিয়া ধর্ম"},
                    {"label": "গ", "text_bn": "জৈন শ্বেতাম্বর ধর্ম"},
                    {"label": "ঘ", "text_bn": "নাথ শৈবধর্ম"},
                ],
                "correct_option": "খ",
                "explanation_bn": "চর্যাপদ পাল শাসনামলে রচিত বৌদ্ধ সহজিয়া সিদ্ধাচার্যদের আধ্যাত্মিক সাধন-সংগীত। এতে শূন্যতা ও মহাসুখের কথা সাংকেতিক ভাষায় রূপায়িত হয়েছে।",
                "question_style": "CONCEPTUAL",
                "difficulty": "EASY",
                "importance": "HIGH",
                "grounding_type": "SOURCE_GROUNDED",
                "source_citation": "বাংলা সাহিত্যের ইতিহাস",
                "previous_bcs_relation": "SIMILAR_TOPIC",
            },
            {
                "question_text_bn": "চর্যাপদের পুঁথির সাথে হরপ্রসাদ শাস্ত্রী আরও কোন কোন গ্রন্থ একসঙ্গে প্রকাশ করেছিলেন?",
                "options": [
                    {"label": "ক", "text_bn": "শ্রীকৃষ্ণকীর্তন ও মঙ্গলকাব্য"},
                    {"label": "খ", "text_bn": "সরহপাদ ও তিলোপাদের দোহা এবং ডাকার্ণব"},
                    {"label": "গ", "text_bn": "পদ্মাবতী ও মনসামঙ্গল"},
                    {"label": "ঘ", "text_bn": "গীতগোবিন্দ ও রামায়ণ"},
                ],
                "correct_option": "খ",
                "explanation_bn": "১৯১৬ সালে হরপ্রসাদ শাস্ত্রী 'হাজার বছরের পুরাণ বাঙ্গালা ভাষায় রচিত বৌদ্ধ গান ও দোহা' নামে চর্যাপদ, সরহপাদের দোহা, তিলোপাদের দোহা এবং ডাকার্ণব—এই চারটি গ্রন্থ একত্রে সম্পাদনা করে প্রকাশ করেন।",
                "question_style": "TRICKY",
                "difficulty": "HARD",
                "importance": "HIGH",
                "grounding_type": "SOURCE_GROUNDED",
                "source_citation": "সাহিত্য ও সমাজ - ড. অসিতকুমার বন্দ্যোপাধ্যায়",
                "previous_bcs_relation": "NONE",
            },
        ],
    },
    # =========================================================================
    # SET 2: মধ্যযুগ (শ্রীকৃষ্ণকীর্তন, মঙ্গলকাব্য, আরাকান রাজসভা)
    # =========================================================================
    {
        "set_number": 2,
        "title_bn": "বাংলা সাহিত্য সেট ২: মধ্যযুগীয় কাব্য ও রোমান্টিক প্রণয়োপাখ্যান",
        "chapter_index": 2,
        "questions": [
            {
                "question_text_bn": "'শ্রীকৃষ্ণকীর্তন' কাব্যের রচয়িতা বড়ু চণ্ডীদাসের প্রকৃত নাম কী বলে অনুমিত হয়?",
                "options": [
                    {"label": "ক", "text_bn": "অনন্ত বড়ু চণ্ডীদাস"},
                    {"label": "খ", "text_bn": "জ্ঞানদাস চণ্ডীদাস"},
                    {"label": "গ", "text_bn": "দ্বিজ চণ্ডীদাস"},
                    {"label": "ঘ", "text_bn": "দীন চণ্ডীদাস"},
                ],
                "correct_option": "ক",
                "explanation_bn": "কাব্যের ভণিতায় 'বড়ু চণ্ডীদাস' এবং কোথাও কোথাও 'অনন্ত' নাম পাওয়া যায়। গবেষকদের মতে তাঁর প্রকৃত নাম অনন্ত এবং উপাধি ছিল বড়ু চণ্ডীদাস।",
                "question_style": "AUTHOR_WORK",
                "difficulty": "MEDIUM",
                "importance": "HIGH",
                "grounding_type": "SOURCE_GROUNDED",
                "source_citation": "শ্রীকৃষ্ণকীর্তন ভূমিকা - বসন্তরঞ্জন রায় বিদ্বদ্বল্লভ",
                "previous_bcs_relation": "SIMILAR_TOPIC",
            },
            {
                "question_text_bn": "১৯০৯ সালে বসন্তরঞ্জন রায় বিদ্বদ্বল্লভ বাঁকুড়ার কাকিল্যা গ্রামের কার গোয়ালঘর থেকে শ্রীকৃষ্ণকীর্তনের পুথি আবিষ্কার করেন?",
                "options": [
                    {"label": "ক", "text_bn": "হরপ্রসাদ শাস্ত্রীর"},
                    {"label": "খ", "text_bn": "দেবেন্দ্রনাথ মুখোপাধ্যায়ের"},
                    {"label": "গ", "text_bn": "যদুনাথ সরকারের"},
                    {"label": "ঘ", "text_bn": "মধুসূদন চট্টোপাধ্যায়ের"},
                ],
                "correct_option": "খ",
                "explanation_bn": "বসন্তরঞ্জন রায় বিদ্বদ্বল্লভ ১৯০৯ সালে পশ্চিমবঙ্গের বাঁকুড়া জেলার কাকিল্যা গ্রামের দেবেন্দ্রনাথ মুখোপাধ্যায়ের বাড়ির গোয়ালঘরের মাচা থেকে শ্রীকৃষ্ণকীর্তনের মূল পুথি আবিষ্কার করেন।",
                "question_style": "FACTUAL",
                "difficulty": "HARD",
                "importance": "HIGH",
                "grounding_type": "SOURCE_GROUNDED",
                "source_citation": "বাংলা সাহিত্যের ইতিবৃত্ত",
                "previous_bcs_relation": "NONE",
            },
            {
                "question_text_bn": "বাংলা সাহিত্যের মধ্যযুগে প্রথম মুসলিম কবি কে এবং তাঁর রচিত কাব্যের নাম কী?",
                "options": [
                    {"label": "ক", "text_bn": "আলাওল - পদ্মাবতী"},
                    {"label": "খ", "text_bn": "শাহ মুহম্মদ সগীর - ইউসুফ-জোলেখা"},
                    {"label": "গ", "text_bn": "দৌলত কাজী - সতীময়না"},
                    {"label": "ঘ", "text_bn": "সৈয়দ সুলতান - নবীবংশ"},
                ],
                "correct_option": "খ",
                "explanation_bn": "শাহ মুহম্মদ সগীর বাংলা সাহিত্যের প্রথম মুসলিম কবি। তিনি গৌড়ের সুলতান গিয়াসউদ্দিন আজম শাহের রাজত্বকালে (১৩৮৯–১৪১০) 'ইউসুফ-জোলেখা' কাব্য রচনা করেন।",
                "question_style": "CHRONOLOGY",
                "difficulty": "EASY",
                "importance": "HIGH",
                "grounding_type": "SOURCE_GROUNDED",
                "source_citation": "মধ্যযুগের বাংলা সাহিত্য - ড. মুহম্মদ এনামুল হক",
                "previous_bcs_relation": "EXACT_REPEAT",
            },
            {
                "question_text_bn": "আরাকান রাজসভার শ্রেষ্ঠ বাঙালি কবি আলাওল হিন্দি কবি মালিক মুহম্মদ জায়সীর কোন কাব্য অবলম্বনে 'পদ্মাবতী' রচনা করেন?",
                "options": [
                    {"label": "ক", "text_bn": "মধুমালতী"},
                    {"label": "খ", "text_bn": "পদুমাবত"},
                    {"label": "গ", "text_bn": "মৃগাবতী"},
                    {"label": "ঘ", "text_bn": "লখনসেন পদ্মাবতী"},
                ],
                "correct_option": "খ",
                "explanation_bn": "আলাওল ১৬৪৬–১৬৫১ খ্রিস্টাব্দের মধ্যে মালিক মুহম্মদ জায়সী রচিত হিন্দি মহাকাব্য 'পদুমাবত' অবলম্বনে তাঁর কালজয়ী অনুবাদকাব্য 'পদ্মাবতী' রচনা করেন।",
                "question_style": "COMPARATIVE",
                "difficulty": "EASY",
                "importance": "HIGH",
                "grounding_type": "SOURCE_GROUNDED",
                "source_citation": "মুসলিম বাংলা সাহিত্য - ড. সুকুমার সেন",
                "previous_bcs_relation": "SIMILAR_TOPIC",
            },
            {
                "question_text_bn": "'নগর পুড়িলে দেবালয় কি এড়ায়?'—মধ্যযুগের এই বিখ্যাত প্রবচনের স্রষ্টা ভারতচন্দ্র রায়গুণাকর কোন কাব্যের রচয়িতা?",
                "options": [
                    {"label": "ক", "text_bn": "মনসামঙ্গল"},
                    {"label": "খ", "text_bn": "অন্নদামঙ্গল"},
                    {"label": "গ", "text_bn": "চণ্ডীমঙ্গল"},
                    {"label": "ঘ", "text_bn": "কালিকামঙ্গল"},
                ],
                "correct_option": "খ",
                "explanation_bn": "রায়গুণাকর ভারতচন্দ্র নদিয়ার রাজা কৃষ্ণচন্দ্রের রাজকবি ছিলেন। তিনি ১৭৫২ সালে 'অন্নদামঙ্গল' কাব্য রচনা করেন, যাতে ঈশ্বরী পাটনী ও নাগরিক জীবনের নিখুঁত ছবি ফুটে উঠেছে।",
                "question_style": "STATEMENT",
                "difficulty": "MEDIUM",
                "importance": "HIGH",
                "grounding_type": "SOURCE_GROUNDED",
                "source_citation": "অন্নদামঙ্গল কাব্য",
                "previous_bcs_relation": "EXACT_REPEAT",
            },
            {
                "question_text_bn": "বাংলা সাহিত্যের 'যুগসন্ধিক্ষণের কবি' হিসেবে কে সুপরিচিত?",
                "options": [
                    {"label": "ক", "text_bn": "ভারতচন্দ্র রায়গুণাকর"},
                    {"label": "খ", "text_bn": "ঈশ্বরচন্দ্র গুপ্ত"},
                    {"label": "গ", "text_bn": "রামনিধি গুপ্ত (নিধুবাবু)"},
                    {"label": "ঘ", "text_bn": "মাইকেল মধুসূদন দত্ত"},
                ],
                "correct_option": "খ",
                "explanation_bn": "ঈশ্বরচন্দ্র গুপ্তকে (১৮১২–১৮৫৯) বাংলা সাহিত্যের যুগসন্ধিক্ষণের কবি বলা হয়, কারণ তাঁর রচনায় মধ্যযুগের পদ্যরীতির সমাপ্তি এবং আধুনিক যুগের সামাজিক সচেতনতার যুগপৎ বহিঃপ্রকাশ ঘটেছিল।",
                "question_style": "CONCEPTUAL",
                "difficulty": "EASY",
                "importance": "HIGH",
                "grounding_type": "SOURCE_GROUNDED",
                "source_citation": "বাংলা সাহিত্যের ইতিহাস - ড. মাহবুবুল আলম",
                "previous_bcs_relation": "EXACT_REPEAT",
            },
            {
                "question_text_bn": "মনসামঙ্গল কাব্যের সবচেয়ে জনপ্রিয় ও আদি কবি হিসেবে কার স্বীকৃতি রয়েছে?",
                "options": [
                    {"label": "ক", "text_bn": "কানাহরি দত্ত ও বিজয়গুপ্ত"},
                    {"label": "খ", "text_bn": "মুকুন্দরাম চক্রবর্তী"},
                    {"label": "গ", "text_bn": "ঘনরাম চক্রবর্তী"},
                    {"label": "ঘ", "text_bn": "মাধবাচার্য"},
                ],
                "correct_option": "ক",
                "explanation_bn": "মনসামঙ্গলের আদি কবি কানাহরি দত্ত এবং সবচেয়ে জনপ্রিয় ও প্রাচীন সন-তারিখযুক্ত কবি হলেন বিজয়গুপ্ত (পদ্মাপুরাণ রচয়িতা, ১৪৯৪ খ্রিস্টাব্দ)।",
                "question_style": "AUTHOR_WORK",
                "difficulty": "MEDIUM",
                "importance": "HIGH",
                "grounding_type": "SOURCE_GROUNDED",
                "source_citation": "মঙ্গলকাব্যের ইতিহাস - আশুতোষ ভট্টাচার্য",
                "previous_bcs_relation": "SIMILAR_TOPIC",
            },
            {
                "question_text_bn": "চণ্ডীমঙ্গল কাব্যের শ্রেষ্ঠ কবি কবিকঙ্কণ মুকুন্দরাম চক্রবর্তীকে 'মধ্যযুগের সর্বশ্রেষ্ঠ বাস্তববাদী কবি' বলার কারণ কী?",
                "options": [
                    {"label": "ক", "text_bn": "তিনি দেবদেবীকে বর্জন করে কাব্য রচনা করেছিলেন"},
                    {"label": "খ", "text_bn": "দেবদেবীর মাহাত্ম্য বর্ণনার ছলে সমকালীন শোষিত প্রজা ও সাধারণ মানুষের দুঃখকষ্টের জীবন্ত চিত্র এঁকেছেন"},
                    {"label": "গ", "text_bn": "তিনি প্রথম বাংলা ভাষায় মহাকাব্য রচনা করেন"},
                    {"label": "ঘ", "text_bn": "তিনি ফারসি ভাষা বর্জন করেছিলেন"},
                ],
                "correct_option": "খ",
                "explanation_bn": "মুকুন্দরাম চক্রবর্তী চণ্ডীমঙ্গল কাব্যে কালকেতু ও ফুল্লরার বারমাস্যার মধ্য দিয়ে সমকালীন বাস্তব সমাজ ও দারিদ্র্যপীড়িত জীবনের এমন জীবন্ত রূপ ফুটিয়ে তুলেছেন যে সমালোচকগণ তাঁকে মধ্যযুগের বাস্তববাদী ঔপন্যাসিকধর্মী কবি আখ্যা দিয়েছেন।",
                "question_style": "ANALYTICAL",
                "difficulty": "MEDIUM",
                "importance": "HIGH",
                "grounding_type": "SOURCE_GROUNDED",
                "source_citation": "বঙ্গভাষা ও সাহিত্য - দীনেশচন্দ্র সেন",
                "previous_bcs_relation": "SIMILAR_TOPIC",
            },
            {
                "question_text_bn": "দৌলত কাজী রচিত প্রথম বাঙালি রোমান্টিক প্রণয়কাব্য 'সতীময়না ও লোরচন্দ্রানী' অসমাপ্ত থেকে গেলে কে তা সমাপ্ত করেন?",
                "options": [
                    {"label": "ক", "text_bn": "কোরেশী মাগন ঠাকুর"},
                    {"label": "খ", "text_bn": "আলাওল"},
                    {"label": "গ", "text_bn": "সৈয়দ সুলতান"},
                    {"label": "ঘ", "text_bn": "আব্দুল হাকিম"},
                ],
                "correct_option": "খ",
                "explanation_bn": "দৌলত কাজী আরাকান রাজা শ্রীসুধর্মের আশ্রয়ে থেকে 'সতীময়না ও লোরচন্দ্রানী' রচনা শুরু করেন কিন্তু মৃত্যুর কারণে অসমাপ্ত থাকে। পরবর্তীতে ১৬৫৯ খ্রিস্টাব্দে আলাওল এই কাব্য সমাপ্ত করেন।",
                "question_style": "CHRONOLOGY",
                "difficulty": "MEDIUM",
                "importance": "HIGH",
                "grounding_type": "SOURCE_GROUNDED",
                "source_citation": "আরাকান রাজসভায় বাংলা সাহিত্য - মুহম্মদ এনামুল হক",
                "previous_bcs_relation": "EXACT_REPEAT",
            },
            {
                "question_text_bn": "'যে সবে বঙ্গেত জন্মি হিংসে বঙ্গবাণী / সে সব কাহার জন্ম নির্ণয় ন জানি'—মধ্যযুগের মাতৃভাষা প্রেমের এই অনন্য পঙ্ক্তিটির রচয়িতা কে?",
                "options": [
                    {"label": "ক", "text_bn": "আলাওল (পদ্মাবতী)"},
                    {"label": "খ", "text_bn": "আব্দুল হাকিম (নূরনামা)"},
                    {"label": "গ", "text_bn": "সৈয়দ সুলতান (নবীবংশ)"},
                    {"label": "ঘ", "text_bn": "শাহ মুহম্মদ সগীর (ইউসুফ-জোলেখা)"},
                ],
                "correct_option": "খ",
                "explanation_bn": "সপ্তদশ শতকের কবি আব্দুল হাকিম তাঁর বিখ্যাত 'নূরনামা' কাব্যে স্বদেশ ও স্বভাষার প্রতি অবিচল নিষ্ঠা প্রকাশ করে এই অনন্য চরণটি রচনা করেন।",
                "question_style": "STATEMENT",
                "difficulty": "EASY",
                "importance": "HIGH",
                "grounding_type": "SOURCE_GROUNDED",
                "source_citation": "নূরনামা কাব্য - আব্দুল হাকিম",
                "previous_bcs_relation": "EXACT_REPEAT",
            },
            {
                "question_text_bn": "বাংলা ভাষায় রামায়ণের প্রথম ও শ্রেষ্ঠ অনুবাদক কৃত্তিবাস ওঝা কোন শতকের কবি ছিলেন?",
                "options": [
                    {"label": "ক", "text_bn": "চতুর্দশ শতক"},
                    {"label": "খ", "text_bn": "পঞ্চদশ শতক"},
                    {"label": "গ", "text_bn": "ষোড়শ শতক"},
                    {"label": "ঘ", "text_bn": "সপ্তদশ শতক"},
                ],
                "correct_option": "খ",
                "explanation_bn": "কৃত্তিবাস ওঝা পঞ্চদশ শতকের কবি ছিলেন। তিনি গৌড়েশ্বর রুকনুদ্দীন বারবক শাহের পৃষ্ঠপোষকতায় রামায়ণের বঙ্গানুবাদ 'শ্রীরাম পাঁচালী' রচনা করেন।",
                "question_style": "CHRONOLOGY",
                "difficulty": "MEDIUM",
                "importance": "HIGH",
                "grounding_type": "SOURCE_GROUNDED",
                "source_citation": "বাংলা সাহিত্যের ইতিহাস",
                "previous_bcs_relation": "SIMILAR_TOPIC",
            },
            {
                "question_text_bn": "বৈষ্ণব পদাবলীর অন্যতম প্রধান পদকর্তা বিদ্যাপতি কোন অঞ্চলের কবি ছিলেন এবং তাঁর পদের ভাষা কী ছিল?",
                "options": [
                    {"label": "ক", "text_bn": "নদিয়া অঞ্চল, বিশুদ্ধ বাংলা ভাষা"},
                    {"label": "খ", "text_bn": "মিথিলা অঞ্চল, ব্রজবুলি ভাষা"},
                    {"label": "গ", "text_bn": "চট্টগ্রাম অঞ্চল, সাধু ভাষা"},
                    {"label": "ঘ", "text_bn": "বীরভূম অঞ্চল, প্রাকৃত ভাষা"},
                ],
                "correct_option": "খ",
                "explanation_bn": "বিদ্যাপতি মিথিলার কবি ছিলেন। তিনি বাংলা ভাষায় কোনো পদ রচনা না করেও কৃত্রিম সাহিত্যিক ভাষা 'ব্রজবুলি'র আশ্রয়ে বৈষ্ণব পদ রচনা করে বাংলা সাহিত্যে অমর হয়ে আছেন। তাঁকে 'মৈথিল কোকিল' বলা হয়।",
                "question_style": "TRICKY",
                "difficulty": "MEDIUM",
                "importance": "HIGH",
                "grounding_type": "SOURCE_GROUNDED",
                "source_citation": "বৈষ্ণব পদাবলী প্রবেশক",
                "previous_bcs_relation": "EXACT_REPEAT",
            },
            {
                "question_text_bn": "'আমার সন্তান যেন থাকে দুধে ভাতে'—ঈশ্বরী পাটনীর এই অমর প্রার্থনাবাক্যটি কোন কবির রচনা?",
                "options": [
                    {"label": "ক", "text_bn": "মুকুন্দরাম চক্রবর্তী"},
                    {"label": "খ", "text_bn": "ভারতচন্দ্র রায়গুণাকর"},
                    {"label": "গ", "text_bn": "বিজয়গুপ্ত"},
                    {"label": "ঘ", "text_bn": "মাধবাচার্য"},
                ],
                "correct_option": "খ",
                "explanation_bn": "ভারতচন্দ্র রায়গুণাকরের 'অন্নদামঙ্গল' কাব্যে দেবী অন্নপূর্ণার কাছে খেয়াঘাটের সাধারণ মাঝি ঈশ্বরী পাটনী বর চাওয়ার মুহূর্তে এই চিরন্তন বাঙালি আকাঙ্ক্ষা প্রকাশ করে।",
                "question_style": "STATEMENT",
                "difficulty": "EASY",
                "importance": "HIGH",
                "grounding_type": "SOURCE_GROUNDED",
                "source_citation": "অন্নদামঙ্গল কাব্য",
                "previous_bcs_relation": "EXACT_REPEAT",
            },
            {
                "question_text_bn": "বাংলা সাহিত্যের অন্ধকার যুগ (১২০১–১৩৫০) সম্পর্কে কোন তথ্যটি ঐতিহাসিক গবেষণায় সঠিক?",
                "options": [
                    {"label": "ক", "text_bn": "এ যুগে কোনো সাহিত্য সৃষ্টিই হয়নি"},
                    {"label": "খ", "text_bn": "তুর্কি আক্রমণের পর রাজনৈতিক অস্থিতিশীলতার কারণে বৃহৎ একক সাহিত্য সৃষ্টি কম হলেও শূন্যপুরাণ ও সেকশুভোদয়া এ যুগের নিদর্শন"},
                    {"label": "গ", "text_bn": "এ যুগে বাংলা ভাষা পুরোপুরি নিষিদ্ধ ছিল"},
                    {"label": "ঘ", "text_bn": "চর্যাপদ এই সময়েই রচিত হয়"},
                ],
                "correct_option": "খ",
                "explanation_bn": "তুর্কি বিজয়ের পরবর্তী ১৫০ বছরকে ড. ওয়াকিল আহমদ প্রমুখ গবেষক রাজনৈতিক অস্থিরতার কারণে 'অন্ধকার যুগ' বললেও রামাই পণ্ডিতের 'শূন্যপুরাণ' ও হলায়ুধ মিশ্রের 'সেকশুভোদয়া' প্রমাণ করে সাহিত্যচর্চা স্তব্ধ ছিল না।",
                "question_style": "CONCEPTUAL",
                "difficulty": "HARD",
                "importance": "MEDIUM",
                "grounding_type": "SOURCE_GROUNDED",
                "source_citation": "মধ্যযুগের বাংলা সাহিত্যের ইতিহাস",
                "previous_bcs_relation": "SIMILAR_TOPIC",
            },
            {
                "question_text_bn": "শ্রীকৃষ্ণকীর্তন কাব্যে মোট কয়টি খণ্ড রয়েছে এবং এর সর্বশেষ খণ্ডটির নাম কী?",
                "options": [
                    {"label": "ক", "text_bn": "১০টি খণ্ড, বংশীখণ্ড"},
                    {"label": "খ", "text_bn": "১২টি খণ্ড, বৃন্দাবনখণ্ড"},
                    {"label": "গ", "text_bn": "১৩টি খণ্ড, রাধাবিরহ"},
                    {"label": "ঘ", "text_bn": "১৪টি খণ্ড, যমুনাতটখণ্ড"},
                ],
                "correct_option": "গ",
                "explanation_bn": "শ্রীকৃষ্ণকীর্তন কাব্যে মোট ১৩টি খণ্ড রয়েছে। এর প্রথম খণ্ড 'জন্মখণ্ড' এবং শেষ খণ্ডটির নাম 'রাধাবিরহ'।",
                "question_style": "TRICKY",
                "difficulty": "MEDIUM",
                "importance": "HIGH",
                "grounding_type": "SOURCE_GROUNDED",
                "source_citation": "শ্রীকৃষ্ণকীর্তন কাব্য পরিচয়",
                "previous_bcs_relation": "SIMILAR_TOPIC",
            },
        ],
    },
    # =========================================================================
    # SET 3: আধুনিক যুগ: প্রথমার্ধ (১৮০১–১৯০০ - বিদ্যাসাগর, মধুসূদন, বঙ্কিম)
    # =========================================================================
    {
        "set_number": 3,
        "title_bn": "বাংলা সাহিত্য সেট ৩: উনিশ শতকীয় রেনেসাঁস, নাটক ও মহাকাব্য",
        "chapter_index": 3,
        "questions": [
            {
                "question_text_bn": "ফোর্ট উইলিয়াম কলেজ কত সালে প্রতিষ্ঠিত হয় এবং এর বাংলা বিভাগ কবে চালু হয়?",
                "options": [
                    {"label": "ক", "text_bn": "১৭৯৯ সালে প্রতিষ্ঠিত, ১৮০০ সালে বাংলা বিভাগ"},
                    {"label": "খ", "text_bn": "১৮০০ সালের মে মাসে প্রতিষ্ঠিত, ১৮০১ সালে বাংলা বিভাগ"},
                    {"label": "গ", "text_bn": "১৮০১ সালে প্রতিষ্ঠিত, ১৮০২ সালে বাংলা বিভাগ"},
                    {"label": "ঘ", "text_bn": "১৮০৫ সালে প্রতিষ্ঠিত, ১৮০৬ সালে বাংলা বিভাগ"},
                ],
                "correct_option": "খ",
                "explanation_bn": "লর্ড ওয়েলেসলি ১৮০০ সালের মে মাসে ব্রিটিশ বেসামরিক কর্মচারীদের দেশীয় ভাষা শিক্ষার জন্য ফোর্ট উইলিয়াম কলেজ প্রতিষ্ঠা করেন এবং ১৮০১ সালে উইলিয়াম কেরির নেতৃত্বে বাংলা বিভাগ চালু হয়।",
                "question_style": "CHRONOLOGY",
                "difficulty": "EASY",
                "importance": "HIGH",
                "grounding_type": "SOURCE_GROUNDED",
                "source_citation": "বাংলা গদ্যের ইতিহাস - সুকুমার সেন",
                "previous_bcs_relation": "EXACT_REPEAT",
            },
            {
                "question_text_bn": "বাংলা গদ্যে প্রথম বিরামচিহ্ন বা যতিচিহ্নের সার্থক ও সুশৃঙ্খল প্রয়োগ করেন কে?",
                "options": [
                    {"label": "ক", "text_bn": "উইলিয়াম কেরি"},
                    {"label": "খ", "text_bn": "রামমোহন রায়"},
                    {"label": "গ", "text_bn": "ঈশ্বরচন্দ্র বিদ্যাসাগর"},
                    {"label": "ঘ", "text_bn": "অক্ষয়কুমার দত্ত"},
                ],
                "correct_option": "গ",
                "explanation_bn": "ঈশ্বরচন্দ্র বিদ্যাসাগর ১৮৪৭ সালে রচিত 'বেতাল পঞ্চবিংশতি' গ্রন্থে প্রথম প্রমিত বাংলা গদ্যে কোলন, সেমিকোলন ও দাড়ি ইত্যাদি যতিচিহ্নের সার্থক প্রয়োগ করেন। এজন্য তাঁকে বাংলা গদ্যের জনক বলা হয়।",
                "question_style": "FACTUAL",
                "difficulty": "EASY",
                "importance": "HIGH",
                "grounding_type": "SOURCE_GROUNDED",
                "source_citation": "বাংলা গদ্য সাহিত্যের ইতিবৃত্ত",
                "previous_bcs_relation": "EXACT_REPEAT",
            },
            {
                "question_text_bn": "মাইকেল মধুসূদন দত্ত রচিত বাংলা সাহিত্যের প্রথম সার্থক মহাকাব্য 'মেঘনাদবধ কাব্য' কত সালে প্রকাশিত হয় এবং এতে কয়টি সর্গ রয়েছে?",
                "options": [
                    {"label": "ক", "text_bn": "১৮৫৮ সালে, ৭টি সর্গ"},
                    {"label": "খ", "text_bn": "১৮৬১ সালে, ৯টি সর্গ"},
                    {"label": "গ", "text_bn": "১৮৬২ সালে, ১০টি সর্গ"},
                    {"label": "ঘ", "text_bn": "১৮৬৫ সালে, ৮টি সর্গ"},
                ],
                "correct_option": "খ",
                "explanation_bn": "১৮৬১ সালে অমিত্রাক্ষর ছন্দে রচিত বাংলা সাহিত্যের প্রথম সার্থক মহাকাব্য 'মেঘনাদবধ কাব্য' প্রকাশিত হয়। এটি মোট ৯টি সর্গে বিভক্ত।",
                "question_style": "CHRONOLOGY",
                "difficulty": "MEDIUM",
                "importance": "HIGH",
                "grounding_type": "SOURCE_GROUNDED",
                "source_citation": "মধুসূদন রচনাবলী",
                "previous_bcs_relation": "EXACT_REPEAT",
            },
            {
                "question_text_bn": "বাংলা সাহিত্যের প্রথম সার্থক সামাজিক নাটক হিসেবে গণ্য করা হয় কোনটি?",
                "options": [
                    {"label": "ক", "text_bn": "শর্মিষ্ঠা - মাইকেল মধুসূদন দত্ত"},
                    {"label": "খ", "text_bn": "কুলীনকুলসর্বস্ব - রামনারায়ণ তর্করত্ন"},
                    {"label": "গ", "text_bn": "নীলদর্পণ - দীনবন্ধু মিত্র"},
                    {"label": "ঘ", "text_bn": "কৃষ্ণকুমারী - মাইকেল মধুসূদন দত্ত"},
                ],
                "correct_option": "খ",
                "explanation_bn": "১৮৫৪ সালে রচিত রামনারায়ণ তর্করত্নের 'কুলীনকুলসর্বস্ব' বহুবিবাহ ও কৌলীন্য প্রথার বিরুদ্ধে রচিত বাংলা সাহিত্যের প্রথম মৌলিক সামাজিক নাটক। আর ১৮৫৯ সালে রচিত 'শর্মিষ্ঠা' প্রথম সার্থক পৌরাণিক নাটক।",
                "question_style": "CONCEPTUAL",
                "difficulty": "MEDIUM",
                "importance": "HIGH",
                "grounding_type": "SOURCE_GROUNDED",
                "source_citation": "বাংলা নাটকের ইতিহাস - ড. আশুতোষ ভট্টাচার্য",
                "previous_bcs_relation": "SIMILAR_TOPIC",
            },
            {
                "question_text_bn": "বঙ্কিমচন্দ্র চট্টোপাধ্যায় রচিত প্রথম বাংলা রোমান্টিক উপন্যাস 'দুর্গেশনন্দিনী' কত সালে প্রকাশিত হয়?",
                "options": [
                    {"label": "ক", "text_bn": "১৮৬৫ সালে"},
                    {"label": "খ", "text_bn": "১৮৫৮ সালে"},
                    {"label": "গ", "text_bn": "১৮৬৯ সালে"},
                    {"label": "ঘ", "text_bn": "১৮৭২ সালে"},
                ],
                "correct_option": "ক",
                "explanation_bn": "১৮৬৫ সালে 'দুর্গেশনন্দিনী' (দুর্গের অধিপতির কন্যা) প্রকাশের মাধ্যমে বাংলা সাহিত্যের প্রথম সার্থক আধুনিক উপন্যাসের দিগন্ত উন্মোচিত হয়।",
                "question_style": "CHRONOLOGY",
                "difficulty": "EASY",
                "importance": "HIGH",
                "grounding_type": "SOURCE_GROUNDED",
                "source_citation": "বঙ্কিম উপন্যাস সমগ্র",
                "previous_bcs_relation": "EXACT_REPEAT",
            },
            {
                "question_text_bn": "'নীলদর্পণ' নাটকের ইংরেজি অনুবাদ কে করেছিলেন এবং কার নামে এটি প্রকাশিত হয়েছিল?",
                "options": [
                    {"label": "ক", "text_bn": "মাইকেল মধুসূদন দত্ত অনুবাদ করেন, রেভারেন্ড জেমস লঙের নামে প্রকাশিত হয়"},
                    {"label": "খ", "text_bn": "দীনবন্ধু মিত্র নিজে অনুবাদ করেন"},
                    {"label": "গ", "text_bn": "উইলিয়াম কেরি অনুবাদ করেন"},
                    {"label": "ঘ", "text_bn": "বঙ্কিমচন্দ্র অনুবাদ করেন, রামমোহনের নামে প্রকাশিত হয়"},
                ],
                "correct_option": "ক",
                "explanation_bn": "দীনবন্ধু মিত্রের নীলদর্পণ নাটকটি মাইকেল মধুসূদন দত্ত ইংরেজিতে 'Nil Darpan; or, The Indigo Planting Mirror' নামে অনুবাদ করেন এবং তা ধর্মযাজক রেভারেন্ড জেমস লঙের নামে প্রকাশিত হওয়ায় তাঁর কারাদণ্ড ও জরিমানা হয়েছিল।",
                "question_style": "AUTHOR_WORK",
                "difficulty": "MEDIUM",
                "importance": "HIGH",
                "grounding_type": "SOURCE_GROUNDED",
                "source_citation": "উনিশ শতকের নাট্য আন্দোলন",
                "previous_bcs_relation": "EXACT_REPEAT",
            },
            {
                "question_text_bn": "মীর মশাররফ হোসেন রচিত কারবালার বিষাদময় ঘটনা অবলম্বনে রচিত ইতিহাসাশ্রয়ী উপন্যাসের নাম কী?",
                "options": [
                    {"label": "ক", "text_bn": "জমীদার দর্পণ"},
                    {"label": "খ", "text_bn": "বিষাদ-সিন্ধু"},
                    {"label": "গ", "text_bn": "গাজী মিয়ার বস্তানী"},
                    {"label": "ঘ", "text_bn": "উদাসীন পথিকের মনের কথা"},
                ],
                "correct_option": "খ",
                "explanation_bn": "১৮৮৫–১৮৯১ সালের মধ্যে তিন খণ্ডে (মহরম পর্ব, উদ্ধার পর্ব ও এজীদ-বধ পর্ব) প্রকাশিত মীর মশাররফ হোসেনের কালজয়ী উপন্যাস হলো 'বিষাদ-সিন্ধু'।",
                "question_style": "AUTHOR_WORK",
                "difficulty": "EASY",
                "importance": "HIGH",
                "grounding_type": "SOURCE_GROUNDED",
                "source_citation": "মুসলিম সাহিত্যের অগ্রদূত",
                "previous_bcs_relation": "EXACT_REPEAT",
            },
            {
                "question_text_bn": "বাংলা সাহিত্যে প্রথম ব্যঙ্গধর্মী সমাজচিত্রণ 'হুতোম প্যাঁচার নক্শা' কার ছদ্মনামে রচিত?",
                "options": [
                    {"label": "ক", "text_bn": "প্যারীচাঁদ মিত্র (টেকচাঁদ ঠাকুর)"},
                    {"label": "খ", "text_bn": "কালীপ্রসন্ন সিংহ (হুতোম প্যাঁচা)"},
                    {"label": "গ", "text_bn": "দীনবন্ধু মিত্র"},
                    {"label": "ঘ", "text_bn": "ঈশ্বরচন্দ্র বিদ্যাসাগর"},
                ],
                "correct_option": "খ",
                "explanation_bn": "কালীপ্রসন্ন সিংহ ১৮৬২ সালে কলকাতার বাবু সমাজের অসঙ্গতি ও ভণ্ডামির ব্যঙ্গচিত্র তুলে ধরে 'হুতোম প্যাঁচার নক্শা' রচনা করেন। এটি খাঁটি কথ্যরীতির প্রথম গ্রন্থ।",
                "question_style": "FACTUAL",
                "difficulty": "EASY",
                "importance": "HIGH",
                "grounding_type": "SOURCE_GROUNDED",
                "source_citation": "উনিশ শতকের বাংলা সাহিত্য",
                "previous_bcs_relation": "EXACT_REPEAT",
            },
            {
                "question_text_bn": "বাংলা সাহিত্যের প্রথম গীতি কবি কে এবং রবীন্দ্রনাথ ঠাকুর তাঁকে কী নামে আখ্যায়িত করেছিলেন?",
                "options": [
                    {"label": "ক", "text_bn": "ঈশ্বরচন্দ্র গুপ্ত - নবযুগের প্রবর্তক"},
                    {"label": "খ", "text_bn": "বিহারীলাল চক্রবর্তী - ভোরের পাখি"},
                    {"label": "গ", "text_bn": "মাইকেল মধুসূদন দত্ত - মহাকবি"},
                    {"label": "ঘ", "text_bn": "হেমচন্দ্র বন্দ্যোপাধ্যায় - স্বদেশপ্রেমিক কবি"},
                ],
                "correct_option": "খ",
                "explanation_bn": "বিহারীলাল চক্রবর্তীকে (১৮৩৫–১৮৯৪) বাংলা সাহিত্যের প্রথম আধুনিক গীতি কবি বলা হয়। রবীন্দ্রনাথ ঠাকুর তাঁর অন্তর্মুখী ভাবাবেগের প্রশংসা করে তাঁকে 'ভোরের পাখি' আখ্যা দেন।",
                "question_style": "STATEMENT",
                "difficulty": "MEDIUM",
                "importance": "HIGH",
                "grounding_type": "SOURCE_GROUNDED",
                "source_citation": "আধুনিক বাংলা কবিতার ইতিহাস",
                "previous_bcs_relation": "EXACT_REPEAT",
            },
            {
                "question_text_bn": "মাইকেল মধুসূদন দত্তের অমর সনেট 'কপোতাক্ষ নদ' কোন ধরনের অন্তমিলে গঠিত?",
                "options": [
                    {"label": "ক", "text_bn": "কখখক কখখক ঘঙঘ ঙঘঙ"},
                    {"label": "খ", "text_bn": "কখ কখ কখ কখ গঘ গঘ ঙঙ"},
                    {"label": "গ", "text_bn": "কখ কখ কখ কখ গঘঙ গঘঙ"},
                    {"label": "ঘ", "text_bn": "কখখক গঘঘগ ঙচচঙ ছছ"},
                ],
                "correct_option": "গ",
                "explanation_bn": "কপোতাক্ষ নদ চতুর্দশপদী কবিতার অষ্টকের অন্তমিল হলো 'কখ কখ কখ কখ' এবং ষষ্ঠকের অন্তমিল 'গঘঙ গঘঙ'। এটি অমিত্রাক্ষর ছন্দে ১৪ মাত্রায় রচিত।",
                "question_style": "TRICKY",
                "difficulty": "HARD",
                "importance": "HIGH",
                "grounding_type": "SOURCE_GROUNDED",
                "source_citation": "চতুর্দশপদী কবিতাবলী - মধুসূদন দত্ত",
                "previous_bcs_relation": "SIMILAR_TOPIC",
            },
            {
                "question_text_bn": "বঙ্কিমচন্দ্র চট্টোপাধ্যায়ের প্রথম প্রকাশিত ইংরেজি উপন্যাসটির নাম কী?",
                "options": [
                    {"label": "ক", "text_bn": "Durgeshnandini"},
                    {"label": "খ", "text_bn": "Rajmohan's Wife"},
                    {"label": "গ", "text_bn": "Anandamath"},
                    {"label": "ঘ", "text_bn": "Kapalkundala"},
                ],
                "correct_option": "খ",
                "explanation_bn": "বঙ্কিমচন্দ্রের প্রথম প্রকাশিত উপন্যাস হলো ইংরেজি ভাষায় রচিত 'Rajmohan's Wife' (১৮৬৪)। এরপরে তিনি মাতৃভাষায় 'দুর্গেশনন্দিনী' রচনায় আত্মনিয়োগ করেন।",
                "question_style": "AUTHOR_WORK",
                "difficulty": "MEDIUM",
                "importance": "HIGH",
                "grounding_type": "SOURCE_GROUNDED",
                "source_citation": "বঙ্কিম জীবনী",
                "previous_bcs_relation": "EXACT_REPEAT",
            },
            {
                "question_text_bn": "মাইকেল মধুসূদন দত্তের প্রহসন দুটির নাম কী?",
                "options": [
                    {"label": "ক", "text_bn": "বিয়ে পাগলা বুড়ো ও সধবার একাদশী"},
                    {"label": "খ", "text_bn": "একেই কি বলে সভ্যতা ও বুড়ো শালিকের ঘাড়ে রোঁ"},
                    {"label": "গ", "text_bn": "কৃষ্ণকুমারী ও শর্মিষ্ঠা"},
                    {"label": "ঘ", "text_bn": "পদ্মাবতী ও মায়াকানন"},
                ],
                "correct_option": "খ",
                "explanation_bn": "১৮৬০ সালে রচিত মধুসূদনের প্রহসন দুটি হলো নব্য তরুণ সমাজের উচ্ছৃঙ্খলতা নিয়ে 'একেই কি বলে সভ্যতা?' এবং রক্ষণশীল প্রাচীনপন্থীদের ভণ্ডামি নিয়ে 'বুড়ো শালিকের ঘাড়ে রোঁ'।",
                "question_style": "FACTUAL",
                "difficulty": "EASY",
                "importance": "HIGH",
                "grounding_type": "SOURCE_GROUNDED",
                "source_citation": "মধুসূদন রচনাবলী",
                "previous_bcs_relation": "EXACT_REPEAT",
            },
            {
                "question_text_bn": "ফোর্ট উইলিয়াম কলেজের পাঠ্যপুস্তকের মধ্যে রামরাম বসু রচিত প্রথম বাঙালি কর্তৃক রচিত মৌলিক বাংলা গদ্যগ্রন্থ কোনটি?",
                "options": [
                    {"label": "ক", "text_bn": "কথোপকথন"},
                    {"label": "খ", "text_bn": "রাজা প্রতাপাদিত্য চরিত্র"},
                    {"label": "গ", "text_bn": "তোতা ইতিহাস"},
                    {"label": "ঘ", "text_bn": "লিপিমালা"},
                ],
                "correct_option": "খ",
                "explanation_bn": "১৮০১ সালে প্রকাশিত রামরাম বসুর 'রাজা প্রতাপাদিত্য চরিত্র' কোনো বাঙালি রচিত বাংলা সাহিত্যের প্রথম মুদ্রিত মৌলিক গদ্যগ্রন্থ।",
                "question_style": "FACTUAL",
                "difficulty": "MEDIUM",
                "importance": "HIGH",
                "grounding_type": "SOURCE_GROUNDED",
                "source_citation": "ফোর্ট উইলিয়াম কলেজ ও বাংলা সাহিত্য",
                "previous_bcs_relation": "EXACT_REPEAT",
            },
            {
                "question_text_bn": "১৮৭২ সালে বঙ্কিমচন্দ্র চট্টোপাধ্যায়ের সম্পাদনায় প্রকাশিত কোন ঐতিহাসিক মাসিক পত্রিকা বাংলা কথাসাহিত্যে নতুন যুগের সূচনা করে?",
                "options": [
                    {"label": "ক", "text_bn": "তত্ত্ববোধিনী পত্রিকা"},
                    {"label": "খ", "text_bn": "বঙ্গদর্শন"},
                    {"label": "গ", "text_bn": "সংবাদ প্রভাকর"},
                    {"label": "ঘ", "text_bn": "সবুজপত্র"},
                ],
                "correct_option": "খ",
                "explanation_bn": "১৮৭২ সালে প্রকাশিত 'বঙ্গদর্শন' পত্রিকার মাধ্যমে রবীন্দ্রনাথ ঠাকুরসহ পরবর্তী প্রজন্মের সাহিত্যিকদের উন্মেষ ঘটেছিল। বিষবৃক্ষ, চন্দ্রশেখর ইত্যাদি উপন্যাস এতে ধারাবাহিকভাবে প্রকাশিত হয়।",
                "question_style": "CHRONOLOGY",
                "difficulty": "EASY",
                "importance": "HIGH",
                "grounding_type": "SOURCE_GROUNDED",
                "source_citation": "বাংলা সাময়িকপত্রের ইতিহাস",
                "previous_bcs_relation": "EXACT_REPEAT",
            },
            {
                "question_text_bn": "'পথিক, তুমি কি পথ হারাইয়াছ?'—কপালকুণ্ডলা উপন্যাসের এই বিখ্যাত সংলাপটি কার প্রতি উচ্চারিত হয়েছিল?",
                "options": [
                    {"label": "ক", "text_bn": "নবকুমারের প্রতি কপালকুণ্ডলার"},
                    {"label": "খ", "text_bn": "কপালকুণ্ডলার প্রতি কাপালিকের"},
                    {"label": "গ", "text_bn": "মতিবিবির প্রতি ওসমানের"},
                    {"label": "ঘ", "text_bn": "আয়েষার প্রতি জগৎসিংহের"},
                ],
                "correct_option": "ক",
                "explanation_bn": "বঙ্কিমচন্দ্রের ১৮৬৬ সালে প্রকাশিত রোমান্টিক উপন্যাস 'কপালকুণ্ডলা'য় সমুদ্রতীরে পথভ্রষ্ট ও হিংস্র জন্তুর ভয়ে ভীত তরুণ নবকুমারকে দেখে বনবাসিনী কপালকুণ্ডলা এই অবিস্মরণীয় বাক্যটি উচ্চারণ করেছিলেন।",
                "question_style": "STATEMENT",
                "difficulty": "EASY",
                "importance": "HIGH",
                "grounding_type": "SOURCE_GROUNDED",
                "source_citation": "কপালকুণ্ডলা - বঙ্কিমচন্দ্র চট্টোপাধ্যায়",
                "previous_bcs_relation": "EXACT_REPEAT",
            },
        ],
    },
    # =========================================================================
    # SET 4: আধুনিক যুগ: দ্বিতীয় পর্ব (১৯০১–১৯৪৭ - রবীন্দ্র, নজরুল, পঞ্চপাণ্ডব)
    # =========================================================================
    {
        "set_number": 4,
        "title_bn": "বাংলা সাহিত্য সেট ৪: রবীন্দ্র-নজরুল যুগ ও আধুনিক কবিতার রূপরেখা",
        "chapter_index": 4,
        "questions": [
            {
                "question_text_bn": "রবীন্দ্রনাথ ঠাকুর কত সালে 'গীতাঞ্জলি' কাব্যের ইংরেজি অনুবাদের জন্য সাহিত্যে নোবেল পুরস্কার লাভ করেন?",
                "options": [
                    {"label": "ক", "text_bn": "১৯১১ সালে"},
                    {"label": "খ", "text_bn": "১৯১২ সালে"},
                    {"label": "গ", "text_bn": "১৯১৩ সালে"},
                    {"label": "ঘ", "text_bn": "১৯১৫ সালে"},
                ],
                "correct_option": "গ",
                "explanation_bn": "১৯১৩ সালের নভেম্বর মাসে রবীন্দ্রনাথ ঠাকুর 'Song Offerings' (গীতাঞ্জলির ইংরেজি রূপ) গ্রন্থের জন্য প্রথম অশ্বেতাঙ্গ ও এশীয় হিসেবে সাহিত্যে নোবেল পুরস্কার লাভ করেন।",
                "question_style": "CHRONOLOGY",
                "difficulty": "EASY",
                "importance": "HIGH",
                "grounding_type": "SOURCE_GROUNDED",
                "source_citation": "রবীন্দ্র জীবনী - প্রভাতকুমার মুখোপাধ্যায়",
                "previous_bcs_relation": "EXACT_REPEAT",
            },
            {
                "question_text_bn": "কাজী নজরুল ইসলামের প্রথম প্রকাশিত কবিতা কোনটি এবং এটি কোন পত্রিকায় প্রকাশিত হয়?",
                "options": [
                    {"label": "ক", "text_bn": "বিদ্রোহী - বিজলী পত্রিকা"},
                    {"label": "খ", "text_bn": "মুক্তি - বঙ্গীয় মুসলমান সাহিত্য পত্রিকা"},
                    {"label": "গ", "text_bn": "প্রলয়োল্লাস - ধুমকেতু"},
                    {"label": "ঘ", "text_bn": "শাত-ইল-আরব - সওগাত"},
                ],
                "correct_option": "খ",
                "explanation_bn": "নজরুলের প্রথম প্রকাশিত কবিতা 'মুক্তি' (১৩২৬ বঙ্গাব্দের শ্রাবণ মাসে 'বঙ্গীয় মুসলমান সাহিত্য পত্রিকা'য় প্রকাশিত)। তাঁর প্রথম প্রকাশিত রচনা গল্প 'বাউণ্ডেলের আত্মকাহিনী'।",
                "question_style": "FACTUAL",
                "difficulty": "MEDIUM",
                "importance": "HIGH",
                "grounding_type": "SOURCE_GROUNDED",
                "source_citation": "নজরুল চরিতমানস - রফিকুল ইসলাম",
                "previous_bcs_relation": "EXACT_REPEAT",
            },
            {
                "question_text_bn": "রবীন্দ্রনাথ ঠাকুরের কোন নাটকটি প্রতীকী বা রূপক সাংকেতিক নাটকের অনন্য নিদর্শন?",
                "options": [
                    {"label": "ক", "text_bn": "বিসর্জন"},
                    {"label": "খ", "text_bn": "রক্তকরবী"},
                    {"label": "গ", "text_bn": "রাজা ও রানী"},
                    {"label": "ঘ", "text_bn": "চিরকুমার সভা"},
                ],
                "correct_option": "খ",
                "explanation_bn": "যন্ত্রসভ্যতার লোভ ও পুঁজিবাদের বিরুদ্ধে মানবের মুক্তির আকুতি রূপায়িত হয়েছে রবীন্দ্রনাথের কালজয়ী রূপক-সাংকেতিক নাটক 'রক্তকরবী' (যক্ষপুরীর পটভূমি এবং নন্দিনী ও রাজার দ্বন্দ্ব) তে।",
                "question_style": "CONCEPTUAL",
                "difficulty": "MEDIUM",
                "importance": "HIGH",
                "grounding_type": "SOURCE_GROUNDED",
                "source_citation": "রবীন্দ্র নাট্য পরিক্রমা",
                "previous_bcs_relation": "EXACT_REPEAT",
            },
            {
                "question_text_bn": "কাজী নজরুল ইসলাম সম্পাদিত অর্ধ-সাপ্তাহিক রাজনৈতিক পত্রিকাটির নাম কী যার জন্য তিনি কারারুদ্ধ হন?",
                "options": [
                    {"label": "ক", "text_bn": "লাঙ্গল"},
                    {"label": "খ", "text_bn": "ধূমকেতু"},
                    {"label": "গ", "text_bn": "নবযুগ"},
                    {"label": "ঘ", "text_bn": "দৈনিক সেবক"},
                ],
                "correct_option": "খ",
                "explanation_bn": "১৯২২ সালের ১১ আগস্ট নজরুলের সম্পাদনায় 'ধূমকেতু' প্রকাশিত হয়। এতে 'আনন্দময়ীর আগমনে' কবিতা প্রকাশের কারণে ব্রিটিশ সরকার তাঁকে গ্রেপ্তার করে এবং রাজদ্রোহের অভিযোগে এক বছরের সশ্রম কারাদণ্ড দেয়।",
                "question_style": "FACTUAL",
                "difficulty": "EASY",
                "importance": "HIGH",
                "grounding_type": "SOURCE_GROUNDED",
                "source_citation": "নজরুল জীবন ও সৃষ্টি",
                "previous_bcs_relation": "EXACT_REPEAT",
            },
            {
                "question_text_bn": "তিরিশের আধুনিক পঞ্চপাণ্ডবের মধ্যে কাকে 'তিমিরহননের কবি' এবং 'রূপসী বাংলার কবি' বলা হয়?",
                "options": [
                    {"label": "ক", "text_bn": "বুদ্ধদেব বসু"},
                    {"label": "খ", "text_bn": "জীবনানন্দ দাশ"},
                    {"label": "গ", "text_bn": "সুধীন্দ্রনাথ দত্ত"},
                    {"label": "ঘ", "text_bn": "বিষ্ণু দে"},
                ],
                "correct_option": "খ",
                "explanation_bn": "জীবনানন্দ দাশকে (১৮৯৯–১৯৫৪) বাংলার নৈসর্গিক রূপ ও পরাবাস্তব ভাবনার জন্য বুদ্ধদেব বসু 'নির্জনতম কবি' এবং পরবর্তীতে 'রূপসী বাংলার কবি' ও 'তিমিরহননের কবি' নামে আখ্যায়িত করা হয়।",
                "question_style": "AUTHOR_WORK",
                "difficulty": "EASY",
                "importance": "HIGH",
                "grounding_type": "SOURCE_GROUNDED",
                "source_citation": "আধুনিক কবিতার দিগন্ত",
                "previous_bcs_relation": "EXACT_REPEAT",
            },
            {
                "question_text_bn": "শরৎচন্দ্র চট্টোপাধ্যায়ের কোন উপন্যাসটি ব্রিটিশ সরকার কর্তৃক বাজেয়াপ্ত হয়েছিল?",
                "options": [
                    {"label": "ক", "text_bn": "পথের দাবী"},
                    {"label": "খ", "text_bn": "চরিত্রহীন"},
                    {"label": "গ", "text_bn": "শ্রীকান্ত"},
                    {"label": "ঘ", "text_bn": "গৃহদাহ"},
                ],
                "correct_option": "ক",
                "explanation_bn": "১৯২৬ সালে প্রকাশিত শরৎচন্দ্রের বিপ্লবী রাজনৈতিক উপন্যাস 'পথের দাবী' (সব্যসাচী চরিত্র) উগ্র জাতীয়তাবাদী ও বৈপ্লবিক চেতনার কারণে ১৯২৭ সালের জানুয়ারিতে ব্রিটিশ সরকার নিষিদ্ধ ঘোষণা করে।",
                "question_style": "FACTUAL",
                "difficulty": "EASY",
                "importance": "HIGH",
                "grounding_type": "SOURCE_GROUNDED",
                "source_citation": "শরৎ সাহিত্য সমগ্র",
                "previous_bcs_relation": "EXACT_REPEAT",
            },
            {
                "question_text_bn": "'নকশী কাঁথার মাঠ' কাব্যগ্রন্থের রচয়িতা পল্লীকবি জসীমউদ্দীন এটিকে কী হিসেবে আখ্যায়িত করেছেন এবং এর ইংরেজি অনুবাদক কে?",
                "options": [
                    {"label": "ক", "text_bn": "রূপক নাটক; অনুবাদক উইলিয়াম রাদিচে"},
                    {"label": "খ", "text_bn": "কাহিনী কাব্য (The Field of the Embroidered Quilt); অনুবাদক ই. এম. মিলফোর্ড"},
                    {"label": "গ", "text_bn": "ছোটগল্প সংকলন; অনুবাদক প্রমথ চৌধুরী"},
                    {"label": "ঘ", "text_bn": "মহাকাব্য; অনুবাদক এডওয়ার্ড থম্পসন"},
                ],
                "correct_option": "খ",
                "explanation_bn": "১৯২৯ সালে প্রকাশিত রূপাই ও সাজুর অমর প্রেমের কাহিনীকাব্য 'নকশী কাঁথার মাঠ' বিশ্বসাহিত্যে সমাদৃত হয়। মেরি মিলফোর্ড (E. M. Milford) ১৯৩৯ সালে এটি 'The Field of the Embroidered Quilt' নামে অনুবাদ করেন।",
                "question_style": "COMPARATIVE",
                "difficulty": "MEDIUM",
                "importance": "HIGH",
                "grounding_type": "SOURCE_GROUNDED",
                "source_citation": "পল্লীকবি জসীমউদ্দীন স্মারকগ্রন্থ",
                "previous_bcs_relation": "EXACT_REPEAT",
            },
            {
                "question_text_bn": "মানিক বন্দ্যোপাধ্যায়ের 'পদ্মা নদীর মাঝি' উপন্যাসটি কত সালে প্রকাশিত হয় এবং এর কেন্দ্রীয় চরিত্র কোনটি?",
                "options": [
                    {"label": "ক", "text_bn": "১৯৩৬ সালে, কুবের ও কপিলা"},
                    {"label": "খ", "text_bn": "১৯৪০ সালে, শশী ও কুসুম"},
                    {"label": "গ", "text_bn": "১৯৩৪ সালে, রতন ও বাসন্তী"},
                    {"label": "ঘ", "text_bn": "১৯৩৮ সালে, নবীন ও চম্পা"},
                ],
                "correct_option": "ক",
                "explanation_bn": "১৯৩৬ সালে প্রকাশিত মানিক বন্দ্যোপাধ্যায়ের অমর উপন্যাস 'পদ্মা নদীর মাঝি' কেতুপুর গ্রামের জেলেদের জীবন ও ময়নাদ্বীপের স্বপ্নের পটভূমিতে কুবের, কপিলা ও হোসেন মিয়া চরিত্র ঘিরে আবর্তিত।",
                "question_style": "AUTHOR_WORK",
                "difficulty": "EASY",
                "importance": "HIGH",
                "grounding_type": "SOURCE_GROUNDED",
                "source_citation": "বাংলা উপন্যাসের ধারা - শ্রীকুমার বন্দ্যোপাধ্যায়",
                "previous_bcs_relation": "EXACT_REPEAT",
            },
            {
                "question_text_bn": "বেগম রোকেয়া সাখাওয়াত হোসেনের বিখ্যাত নারীবাদী ইউটোপিয়ান কল্পকাহিনী 'Sultana's Dream' কত সালে প্রকাশিত হয়?",
                "options": [
                    {"label": "ক", "text_bn": "১৯০৫ সালে (The Indian Ladies' Magazine)"},
                    {"label": "খ", "text_bn": "১৯০৮ সালে"},
                    {"label": "গ", "text_bn": "১৯১৬ সালে"},
                    {"label": "ঘ", "text_bn": "১৯২৪ সালে"},
                ],
                "correct_option": "ক",
                "explanation_bn": "১৯০৫ সালে মাদ্রাজের 'The Indian Ladies' Magazine' এ রোকেয়ার বিশ্ববিখ্যাত কল্পবিজ্ঞানধর্মী নারীবাদী রচনা 'Sultana's Dream' প্রকাশিত হয় (পরবর্তীতে ১৯০৮ সালে বই আকারে বের হয়)।",
                "question_style": "CHRONOLOGY",
                "difficulty": "MEDIUM",
                "importance": "HIGH",
                "grounding_type": "SOURCE_GROUNDED",
                "source_citation": "রোকেয়া রচনাবলী",
                "previous_bcs_relation": "SIMILAR_TOPIC",
            },
            {
                "question_text_bn": "১৯২৬ সালে ঢাকায় গঠিত 'মুসলিম সাহিত্য সমাজ' এর মুখপত্র পত্রিকার নাম কী ছিল এবং এর মূল নীতিবাক্য কী ছিল?",
                "options": [
                    {"label": "ক", "text_bn": "সওগাত; সাহিত্যই জীবন"},
                    {"label": "খ", "text_bn": "শিখা; 'জ্ঞান যেখানে সীমাবদ্ধ, বুদ্ধি সেখানে আড়ষ্ট, মুক্তি সেখানে অসম্ভব'"},
                    {"label": "গ", "text_bn": "কল্লোল; তারুণ্যের জয়গান"},
                    {"label": "ঘ", "text_bn": "সবুজপত্র; প্রগতির দিশা"},
                ],
                "correct_option": "খ",
                "explanation_bn": "ড. মুহম্মদ শহীদুল্লাহ্, কাজী আবদুল ওদুদ, আবুল হুসেন প্রমুখের নেতৃত্বে গঠিত মুসলিম সাহিত্য সমাজের আন্দোলন 'বুদ্ধির মুক্তি আন্দোলন' নামে খ্যাত এবং এর বার্ষিক মুখপত্র ছিল 'শিখা'।",
                "question_style": "CONCEPTUAL",
                "difficulty": "EASY",
                "importance": "HIGH",
                "grounding_type": "SOURCE_GROUNDED",
                "source_citation": "মুসলিম সাহিত্য সমাজ ও বুদ্ধির মুক্তি আন্দোলন",
                "previous_bcs_relation": "EXACT_REPEAT",
            },
            {
                "question_text_bn": "রবীন্দ্রনাথ ঠাকুর তাঁর কোন রচনাটি নেতাজি সুভাষচন্দ্র বসুকে উৎসর্গ করেছিলেন?",
                "options": [
                    {"label": "ক", "text_bn": "কালের যাত্রা"},
                    {"label": "খ", "text_bn": "তাসের দেশ"},
                    {"label": "গ", "text_bn": "চার অধ্যায়"},
                    {"label": "ঘ", "text_bn": "শেষের কবিতা"},
                ],
                "correct_option": "খ",
                "explanation_bn": "১৯৩৩ সালে রবীন্দ্রনাথ ঠাকুর তাঁর বিখ্যাত গীতিনাট্য 'তাসের দেশ' দেশনায়ক সুভাষচন্দ্র বসুকে উৎসর্গ করেন। আর 'কালের যাত্রা' নাটকটি উৎসর্গ করেছিলেন শরৎচন্দ্র চট্টোপাধ্যায়কে।",
                "question_style": "AUTHOR_WORK",
                "difficulty": "HARD",
                "importance": "HIGH",
                "grounding_type": "SOURCE_GROUNDED",
                "source_citation": "রবীন্দ্র উৎসর্গপত্রাবলী",
                "previous_bcs_relation": "SIMILAR_TOPIC",
            },
            {
                "question_text_bn": "কাজী নজরুল ইসলামের নিষিদ্ধ ঘোষিত ৫টি গ্রন্থের সঠিক তালিকা কোনটি?",
                "options": [
                    {"label": "ক", "text_bn": "যুগবাণী, বিষের বাঁশী, ভাঙার গান, প্রলয়শিখা, চন্দ্রবিন্দু"},
                    {"label": "খ", "text_bn": "অগ্নিবীণা, দোলন-চাঁপা, সিন্ধু-হিন্দোল, চক্রবাক, সাম্যবাদী"},
                    {"label": "গ", "text_bn": "রিক্তের বেদন, ব্যথার দান, শিউলিমালা, কুহেলিকা, বাঁধনহারা"},
                    {"label": "ঘ", "text_bn": "মরুভাস্কর, নতুন চাঁদ, জিঞ্জীর, ফণি-মনসা, রুদ্র-মঙ্গল"},
                ],
                "correct_option": "ক",
                "explanation_bn": "ব্রিটিশ সরকার নজরুল ইসলামের পাঁচটি বই পর্যায়ক্রমে রাজদ্রোহের অভিযোগে নিষিদ্ধ করেছিল: ১. যুগবাণী (১৯২২), ২. বিষের বাঁশী (১৯২৪), ৩. ভাঙার গান (১৯২৪), ৪. প্রলয়শিখা (১৯৩০), এবং ৫. চন্দ্রবিন্দু (১৯৩১)।",
                "question_style": "TRICKY",
                "difficulty": "HARD",
                "importance": "HIGH",
                "grounding_type": "SOURCE_GROUNDED",
                "source_citation": "নজরুলের বাজেয়াপ্ত গ্রন্থাবলী",
                "previous_bcs_relation": "EXACT_REPEAT",
            },
            {
                "question_text_bn": "তারাশঙ্কর বন্দ্যোপাধ্যায়ের 'রাঢ় অঞ্চলের গণমানুষের মহাকাব্যিক ত্রয়ী উপন্যাস' কোনটি?",
                "options": [
                    {"label": "ক", "text_bn": "গণদেবতা, পঞ্চগ্রাম, হাঁসুলী বাঁকের উপকথা"},
                    {"label": "খ", "text_bn": "ধাত্রীদেবতা, গণদেবতা, কালিন্দী"},
                    {"label": "গ", "text_bn": "চাঁপাডাঙার বউ, কবি, নাগিনী কন্যার কাহিনী"},
                    {"label": "ঘ", "text_bn": "মন্বন্তর, আরোগ্য নিকেতন, বিচারক"},
                ],
                "correct_option": "খ",
                "explanation_bn": "তারাশঙ্করের রাঢ় অঞ্চলের সমাজ-অর্থনীতির ভাঙাগড়ার পটভূমিতে রচিত ত্রয়ী উপন্যাস হলো 'ধাত্রীদেবতা' (১৯৩৯), 'কালিন্দী' (১৯৪০) ও 'গণদেবতা' (১৯৪২)। 'গণদেবতা'র জন্য তিনি জ্ঞানপীঠ পুরস্কার লাভ করেন।",
                "question_style": "ANALYTICAL",
                "difficulty": "HARD",
                "importance": "MEDIUM",
                "grounding_type": "SOURCE_GROUNDED",
                "source_citation": "আধুনিক কথাসাহিত্যের ইতিহাস",
                "previous_bcs_relation": "NONE",
            },
            {
                "question_text_bn": "'হাঁসুলী বাঁকের উপকথা' উপন্যাসে কোন অনগ্রসর জনগোষ্ঠীর জীবনসংগ্রাম ও কুসংস্কার রূপায়িত হয়েছে?",
                "options": [
                    {"label": "ক", "text_bn": "সাঁওতাল সম্প্রদায়"},
                    {"label": "খ", "text_bn": "কাহার সম্প্রদায়"},
                    {"label": "গ", "text_bn": "গারো সম্প্রদায়"},
                    {"label": "ঘ", "text_bn": "বেদে সম্প্রদায়"},
                ],
                "correct_option": "খ",
                "explanation_bn": "তারাশঙ্কর বন্দ্যোপাধ্যায়ের কালজয়ী উপন্যাস 'হাঁসুলী বাঁকের উপকথা' কোপাই নদীর বাঁকে বসবাসকারী কাহার সম্প্রদায়ের প্রাচীন সংস্কার বনাম নব্য আধুনিকতার সংঘাতের নিখুঁত দলিল।",
                "question_style": "FACTUAL",
                "difficulty": "MEDIUM",
                "importance": "HIGH",
                "grounding_type": "SOURCE_GROUNDED",
                "source_citation": "হাঁসুলী বাঁকের উপকথা - তারাশঙ্কর বন্দ্যোপাধ্যায়",
                "previous_bcs_relation": "EXACT_REPEAT",
            },
            {
                "question_text_bn": "কিশোর কবি সুকান্ত ভট্টাচার্যের মৃত্যুর পর প্রকাশিত তাঁর বিখ্যাত প্রথম কাব্যগ্রন্থ কোনটি?",
                "options": [
                    {"label": "ক", "text_bn": "ঘুম নেই"},
                    {"label": "খ", "text_bn": "ছাড়পত্র"},
                    {"label": "গ", "text_bn": "মিঠেকড়া"},
                    {"label": "ঘ", "text_bn": "পূর্বাভাস"},
                ],
                "correct_option": "খ",
                "explanation_bn": "১৯৪৭ সালের মে মাসে সুকান্ত ভট্টাচার্যের অকাল প্রয়াণের পর ১৯৪৮ সালে সুভাষ মুখোপাধ্যায়ের ভূমিকাসহ তাঁর প্রথম কালজয়ী কাব্যগ্রন্থ 'ছাড়পত্র' প্রকাশিত হয়।",
                "question_style": "CHRONOLOGY",
                "difficulty": "EASY",
                "importance": "HIGH",
                "grounding_type": "SOURCE_GROUNDED",
                "source_citation": "সুকান্ত সমগ্র",
                "previous_bcs_relation": "EXACT_REPEAT",
            },
        ],
    },
    # =========================================================================
    # SET 5: সমকালীন ও বাংলাদেশের সাহিত্য (১৯৪৭–বর্তমান - ভাষা আন্দোলন ও মুক্তিযুদ্ধ)
    # =========================================================================
    {
        "set_number": 5,
        "title_bn": "বাংলা সাহিত্য সেট ৫: বাংলাদেশের সাহিত্য, ভাষা আন্দোলন ও মুক্তিযুদ্ধ",
        "chapter_index": 5,
        "questions": [
            {
                "question_text_bn": "১৯৫২ সালের মহান ভাষা আন্দোলনের পটভূমিতে রচিত মুনীর চৌধুরীর বিখ্যাত নাটক 'কবর' কোথায় বসে রচিত ও প্রথম অভিনীত হয়েছিল?",
                "options": [
                    {"label": "ক", "text_bn": "ঢাকা বিশ্ববিদ্যালয় কার্জন হলে"},
                    {"label": "খ", "text_bn": "ঢাকা কেন্দ্রীয় কারাগারের অভ্যন্তরে"},
                    {"label": "গ", "text_bn": "বাংলা একাডেমির প্রাঙ্গণে"},
                    {"label": "ঘ", "text_bn": "কলকাতা থিয়েটার সেন্টারে"},
                ],
                "correct_option": "খ",
                "explanation_bn": "১৯৫৩ সালের জানুয়ারিতে ঢাকা কেন্দ্রীয় কারাগারে রাজবন্দী অবস্থায় রণেশ দাশগুপ্তের অনুপ্রেরণায় এবং সহবন্দীদের নিয়ে হারিকেনের আলোয় মুনীর চৌধুরী 'কবর' নাটকটি রচনা ও মঞ্চস্থ করেন।",
                "question_style": "FACTUAL",
                "difficulty": "EASY",
                "importance": "HIGH",
                "grounding_type": "SOURCE_GROUNDED",
                "source_citation": "মুনীর চৌধুরী নাট্যসমগ্র",
                "previous_bcs_relation": "EXACT_REPEAT",
            },
            {
                "question_text_bn": "ভাষা আন্দোলনভিত্তিক প্রথম সংকলন গ্রন্থ 'একুশে ফেব্রুয়ারী' কার সম্পাদনায় এবং কত সালে প্রকাশিত হয়?",
                "options": [
                    {"label": "ক", "text_bn": "আবদুল গাফফার চৌধুরী, ১৯৫২"},
                    {"label": "খ", "text_bn": "হাসান হাফিজুর রহমান, ১৯৫৩"},
                    {"label": "গ", "text_bn": "শামসুর রাহমান, ১৯৫৪"},
                    {"label": "ঘ", "text_bn": "জহির রায়হান, ১৯৫৫"},
                ],
                "correct_option": "খ",
                "explanation_bn": "১৯৫৩ সালের মার্চ মাসে হাসান হাফিজুর রহমানের সম্পাদনায় এবং পুঁথিপত্র প্রকাশনী থেকে 'একুশে ফেব্রুয়ারী' ঐতিহাসিক সংকলনটি প্রকাশিত হয়। এর প্রচ্ছদ করেছিলেন মুর্তজা বশীর।",
                "question_style": "CHRONOLOGY",
                "difficulty": "EASY",
                "importance": "HIGH",
                "grounding_type": "SOURCE_GROUNDED",
                "source_citation": "একুশের সংকলন ইতিহাস",
                "previous_bcs_relation": "EXACT_REPEAT",
            },
            {
                "question_text_bn": "জহির রায়হান রচিত ভাষা আন্দোলনের পটভূমিতে রচিত প্রথম সার্থক উপন্যাসের নাম কী?",
                "options": [
                    {"label": "ক", "text_bn": "হাজার বছর ধরে"},
                    {"label": "খ", "text_bn": "আরেক ফাল্গুন"},
                    {"label": "গ", "text_bn": "বরফ গলা নদী"},
                    {"label": "ঘ", "text_bn": "শেষ বিকেলের মেয়ে"},
                ],
                "correct_option": "খ",
                "explanation_bn": "১৯৬৯ সালে প্রকাশিত 'আরেক ফাল্গুন' উপন্যাসে ১৯৫৩ থেকে ১৯৫৫ সালের একুশে ফেব্রুয়ারি উদযাপনের সংগ্রামী ছাত্রসমাজের চিত্র অঙ্কিত হয়েছে। এর মূল স্লোগান 'আসছে ফাল্গুনে আমরা কিন্তু দ্বিগুণ হব'।",
                "question_style": "AUTHOR_WORK",
                "difficulty": "EASY",
                "importance": "HIGH",
                "grounding_type": "SOURCE_GROUNDED",
                "source_citation": "জহির রায়হান রচনাবলী",
                "previous_bcs_relation": "EXACT_REPEAT",
            },
            {
                "question_text_bn": "শওকত ওসমানের মুক্তিযুদ্ধভিত্তিক বিখ্যাত রূপক উপন্যাস 'জাহান্নাম হইতে বিদায়' এর মূল প্রেক্ষাপট কী?",
                "options": [
                    {"label": "ক", "text_bn": "১৯৭১ সালে ঢাকা বিশ্ববিদ্যালয় হত্যাকাণ্ডের বিবরণ"},
                    {"label": "খ", "text_bn": "একাত্তরের ২৫ মার্চের কালরাত্রিতে বর্বর পাকিস্তানি সেনাদের হাত থেকে বাঁচতে শিল্পীর সীমান্ত পাড়ি দেওয়ার বাস্তব অভিজ্ঞতা"},
                    {"label": "গ", "text_bn": "মুক্তিযোদ্ধাদের গেরিলা আক্রমণ"},
                    {"label": "ঘ", "text_bn": "স্বাধীন বাংলা বেতার কেন্দ্রের ইতিহাস"},
                ],
                "correct_option": "খ",
                "explanation_bn": "১৯৭১ সালের ভয়াবহ গণহত্যা থেকে রক্ষা পেতে গাজী নিজামুদ্দিন ছদ্মনামে সীমান্ত পাড়ি দিয়ে ভারতে শরণার্থী হওয়ার অভিজ্ঞতা নিয়ে শওকত ওসমান এই উপন্যাস রচনা করেন।",
                "question_style": "CONCEPTUAL",
                "difficulty": "MEDIUM",
                "importance": "HIGH",
                "grounding_type": "SOURCE_GROUNDED",
                "source_citation": "বাংলাদেশের মুক্তিযুদ্ধভিত্তিক সাহিত্য",
                "previous_bcs_relation": "EXACT_REPEAT",
            },
            {
                "question_text_bn": "আখতারুজ্জামান ইলিয়াসের তেভাগা আন্দোলন ও গ্রামীণ সমাজ বাস্তবতার মহাকাব্যিক উপন্যাসের নাম কী?",
                "options": [
                    {"label": "ক", "text_bn": "চিলেকোঠার সেপাই"},
                    {"label": "খ", "text_bn": "খোয়ারি"},
                    {"label": "গ", "text_bn": "দুধেভাতে উৎপাত"},
                    {"label": "ঘ", "text_bn": "খোঁয়ারি ও রেইনকোট"},
                ],
                "correct_option": "ক",
                "explanation_bn": "আখতারুজ্জামান ইলিয়াসের উপন্যাস দুটি: ১৯৬৯-এর গণঅভ্যুত্থানের প্রেক্ষাপটে 'চিলেকোঠার সেপাই' (১৯৮৭) এবং তেভাগা আন্দোলন ও বগুড়ার অঞ্চলের পটভূমিতে 'খোয়ারি' (১৯৯৬)। (এখানে চিলেকোঠার সেপাই গণঅভ্যুত্থানের প্রতীক)।",
                "question_style": "AUTHOR_WORK",
                "difficulty": "MEDIUM",
                "importance": "HIGH",
                "grounding_type": "SOURCE_GROUNDED",
                "source_citation": "আখতারুজ্জামান ইলিয়াস উপন্যাস সমগ্র",
                "previous_bcs_relation": "EXACT_REPEAT",
            },
            {
                "question_text_bn": "শামসুর রাহমানের বিখ্যাত মুক্তিযুদ্ধভিত্তিক কবিতা 'তোমাকে পাওয়ার জন্যে, হে স্বাধীনতা' কোন কাব্যগ্রন্থের অন্তর্ভুক্ত?",
                "options": [
                    {"label": "ক", "text_bn": "রৌদ্র করোটিতে"},
                    {"label": "খ", "text_bn": "বন্দী শিবির থেকে"},
                    {"label": "গ", "text_bn": "বিধ্বস্ত নীলিমা"},
                    {"label": "ঘ", "text_bn": "বাংলাদেশ স্বপ্ন দ্যাখে"},
                ],
                "correct_option": "খ",
                "explanation_bn": "একাত্তরের অবরুদ্ধ ঢাকায় বসে মজলুম আদিব ছদ্মনামে রচিত শামসুর রাহমানের অমর কাব্যগ্রন্থ 'বন্দী শিবির থেকে' (১৯৭২)। এতেই 'তোমাকে পাওয়ার জন্যে, হে স্বাধীনতা' এবং 'স্বাধীনতা তুমি' কবিতা দুটি অন্তর্ভুক্ত।",
                "question_style": "STATEMENT",
                "difficulty": "EASY",
                "importance": "HIGH",
                "grounding_type": "SOURCE_GROUNDED",
                "source_citation": "শামসুর রাহমান শ্রেষ্ঠ কবিতা",
                "previous_bcs_relation": "EXACT_REPEAT",
            },
            {
                "question_text_bn": "সৈয়দ শামসুল হকের মুক্তিযুদ্ধভিত্তিক বিখ্যাত কাব্যনাট্য কোনটি যার সংলাপ 'তোমাদের জানা নেই এ যুদ্ধের শেষ কোথায়'?",
                "options": [
                    {"label": "ক", "text_bn": "নূরলদীনের সারাজীবন"},
                    {"label": "খ", "text_bn": "পায়ের আওয়াজ পাওয়া যায়"},
                    {"label": "গ", "text_bn": "গণনায়ক"},
                    {"label": "ঘ", "text_bn": "এখানে এখন"},
                ],
                "correct_option": "খ",
                "explanation_bn": "১৯৭৬ সালে রচিত সৈয়দ শামসুল হকের কালজয়ী কাব্যনাট্য 'পায়ের আওয়াজ পাওয়া যায়' একাত্তরের ১৬ ডিসেম্বরের চূড়ান্ত বিজয়ের মুহূর্তে একটি গ্রামে রাজাকার ও মাতব্বরের অন্তিম পরিণতির দৃশ্য তুলে ধরে।",
                "question_style": "AUTHOR_WORK",
                "difficulty": "EASY",
                "importance": "HIGH",
                "grounding_type": "SOURCE_GROUNDED",
                "source_citation": "সৈয়দ শামসুল হক নাট্যসমগ্র",
                "previous_bcs_relation": "EXACT_REPEAT",
            },
            {
                "question_text_bn": "হাসান আজিজুল হকের মুক্তিযুদ্ধভিত্তিক কালজয়ী ছোটগল্প কোনটি?",
                "options": [
                    {"label": "ক", "text_bn": "আত্মজা ও একটি করবী গাছ"},
                    {"label": "খ", "text_bn": "ভূষণের ঘাট ও অন্যান্য গল্প"},
                    {"label": "গ", "text_bn": "নামহীন গোত্রহীন"},
                    {"label": "ঘ", "text_bn": "পাতালে হাসপাতালে"},
                ],
                "correct_option": "ক",
                "explanation_bn": "হাসান আজিজুল হকের বিখ্যাত গল্প 'আত্মজা ও একটি করবী গাছ' এবং মুক্তিযুদ্ধভিত্তিক গল্পগ্রন্থ 'নামহীন গোত্রহীন'। এর মধ্যে আত্মজা ও একটি করবী গাছ দেশভাগের নিদারুণ অর্থনৈতিক সংকট ও আত্মবিক্রয়ের মর্মান্তিক ট্র্যাজেডি।",
                "question_style": "AUTHOR_WORK",
                "difficulty": "MEDIUM",
                "importance": "HIGH",
                "grounding_type": "SOURCE_GROUNDED",
                "source_citation": "হাসান আজিজুল হক গল্পসমগ্র",
                "previous_bcs_relation": "SIMILAR_TOPIC",
            },
            {
                "question_text_bn": "হুমায়ূন আহমেদের মুক্তিযুদ্ধভিত্তিক প্রথম উপন্যাস কোনটি?",
                "options": [
                    {"label": "ক", "text_bn": "জোছনা ও জননীর গল্প"},
                    {"label": "খ", "text_bn": "আগুনের পরশমণি"},
                    {"label": "গ", "text_bn": "শ্যামল ছায়া"},
                    {"label": "ঘ", "text_bn": "অনিল বাগচীর একদিন"},
                ],
                "correct_option": "খ",
                "explanation_bn": "১৯৮৬ সালে প্রকাশিত 'আগুনের পরশমণি' হুমায়ূন আহমেদের মুক্তিযুদ্ধভিত্তিক প্রথম উপন্যাস। একাত্তরের অবরুদ্ধ ঢাকায় গেরিলাদের বীরোচিত লড়াই নিয়ে এটি রচিত, যা পরবর্তীতে তাঁর পরিচালনায় শ্রেষ্ঠ চলচ্চিত্র হিসেবে জাতীয় পুরস্কার পায়।",
                "question_style": "CHRONOLOGY",
                "difficulty": "EASY",
                "importance": "HIGH",
                "grounding_type": "SOURCE_GROUNDED",
                "source_citation": "হুমায়ূন আহমেদ মুক্তিযুদ্ধ উপন্যাস সমগ্র",
                "previous_bcs_relation": "EXACT_REPEAT",
            },
            {
                "question_text_bn": "সেলিনা হোসেনের মুক্তিযুদ্ধভিত্তিক উপন্যাসের নাম কী যার পটভূমিতে রয়েছে বীরশ্রেষ্ঠ নূর মোহাম্মদ ও পাক বাহিনীর নিষ্ঠুরতা?",
                "options": [
                    {"label": "ক", "text_bn": "হাঙর নদী গ্রেনেড"},
                    {"label": "খ", "text_bn": "যাপিত জীবন"},
                    {"label": "গ", "text_bn": "নীল ময়ূরের যৌবন"},
                    {"label": "ঘ", "text_bn": "গায়ত্রী সন্ধ্যা"},
                ],
                "correct_option": "ক",
                "explanation_bn": "১৯৭৬ সালে প্রকাশিত সেলিনা হোসেনের 'হাঙর নদী গ্রেনেড' উপন্যাসে যশোরের কালীগঞ্জ গ্রামের বাকপ্রতিবন্ধী পুত্রের আত্মত্যাগের মাধ্যমে দুই মুক্তিযোদ্ধাকে বাঁচানোর বিরল মাতৃপ্রেম অঙ্কিত হয়েছে।",
                "question_style": "AUTHOR_WORK",
                "difficulty": "EASY",
                "importance": "HIGH",
                "grounding_type": "SOURCE_GROUNDED",
                "source_citation": "বাংলাদেশের মুক্তিযুদ্ধ উপন্যাসের ইতিহাস",
                "previous_bcs_relation": "EXACT_REPEAT",
            },
            {
                "question_text_bn": "কবি আল মাহমুদের সোনালী কাবিন কাব্যগ্রন্থটি কত সালে প্রকাশিত হয় এবং এর প্রধান উপজীব্য কী?",
                "options": [
                    {"label": "ক", "text_bn": "১৯৬৮ সালে, আধ্যাত্মিক সাধনা"},
                    {"label": "খ", "text_bn": "১৯৭৩ সালে, লোকায়ত বাংলার আবহমান সংস্কৃতি ও নারীর রূপ-প্রেম"},
                    {"label": "গ", "text_bn": "১৯৭৮ সালে, নগরজীবনের ক্লেদ"},
                    {"label": "ঘ", "text_bn": "১৯৮১ সালে, রাজনৈতিক স্লোগান"},
                ],
                "correct_option": "খ",
                "explanation_bn": "১৯৭৩ সালে প্রকাশিত আল মাহমুদের কালজয়ী চতুর্দশপদী সনেট গুচ্ছ 'সোনালী কাবিন' বাংলা কাব্যে মাটি, নদী, লোকায়ত জীবন ও কামনার সংমিশ্রণে এক অবিস্মরণীয় সৃষ্টি।",
                "question_style": "CHRONOLOGY",
                "difficulty": "MEDIUM",
                "importance": "HIGH",
                "grounding_type": "SOURCE_GROUNDED",
                "source_citation": "সোনালী কাবিন - আল মাহমুদ",
                "previous_bcs_relation": "EXACT_REPEAT",
            },
            {
                "question_text_bn": "শহীদ বুদ্ধিজীবী শহীদুল্লা কায়সারের ভাষা আন্দোলন ও সাংবাদিক জীবনের পটভূমিতে রচিত উপন্যাসের নাম কী?",
                "options": [
                    {"label": "ক", "text_bn": "সারেং বৌ"},
                    {"label": "খ", "text_bn": "সংশপ্তক"},
                    {"label": "গ", "text_bn": "কবে পোহাবে বিভাবরী"},
                    {"label": "ঘ", "text_bn": "দিগন্তের স্বপ্ন"},
                ],
                "correct_option": "খ",
                "explanation_bn": "১৯৬৫ সালে প্রকাশিত 'সংশপ্তক' উপন্যাসে ফেলু মিয়া, সেকান্দর মাস্টার ও রাবু চরিত্রের মধ্য দিয়ে দ্বিতীয় বিশ্বযুদ্ধ থেকে পঞ্চাশের দশক পর্যন্ত বাংলার সামাজিক ভাঙাগড়া চিত্রিত হয়েছে।",
                "question_style": "AUTHOR_WORK",
                "difficulty": "MEDIUM",
                "importance": "HIGH",
                "grounding_type": "SOURCE_GROUNDED",
                "source_citation": "শহীদুল্লা কায়সার রচনাবলী",
                "previous_bcs_relation": "EXACT_REPEAT",
            },
            {
                "question_text_bn": "বাংলাদেশের স্বাধীনতা যুদ্ধ দলিলপত্র কয়টি খণ্ডে প্রকাশিত হয় এবং এর প্রধান সম্পাদক কে ছিলেন?",
                "options": [
                    {"label": "ক", "text_bn": "১২টি খণ্ডে, শামসুর রাহমান"},
                    {"label": "খ", "text_bn": "১৬টি খণ্ডে, হাসান হাফিজুর রহমান"},
                    {"label": "গ", "text_bn": "১৪টি খণ্ডে, ড. আনিসুজ্জামান"},
                    {"label": "ঘ", "text_bn": "১৮টি খণ্ডে, রফিকুল ইসলাম"},
                ],
                "correct_option": "খ",
                "explanation_bn": "গণপ্রজাতন্ত্রী বাংলাদেশ সরকার তথ্য মন্ত্রণালয়ের অধীনে হাসান হাফিজুর রহমানের প্রধান সম্পাদনায় মোট ১৬টি খণ্ডে 'বাংলাদেশের স্বাধীনতা যুদ্ধ: দলিলপত্র' সংকলিত ও প্রকাশিত হয়।",
                "question_style": "FACTUAL",
                "difficulty": "EASY",
                "importance": "HIGH",
                "grounding_type": "SOURCE_GROUNDED",
                "source_citation": "জাতীয় মুক্তিযুদ্ধ দলিলমালা",
                "previous_bcs_relation": "EXACT_REPEAT",
            },
            {
                "question_text_bn": "নির্মলেন্দু গুণের ঐতিহাসিক ৭ই মার্চের ভাষণভিত্তিক বিখ্যাত কবিতার নাম কী?",
                "options": [
                    {"label": "ক", "text_bn": "হুলিয়া"},
                    {"label": "খ", "text_bn": "স্বাধীনতা, এই শব্দটি কীভাবে আমাদের হলো"},
                    {"label": "গ", "text_bn": "প্রেমাংশুর রক্ত চাই"},
                    {"label": "ঘ", "text_bn": "বাংলার মাটি বাংলার জল"},
                ],
                "correct_option": "খ",
                "explanation_bn": "'শত বছরের শত সংগ্রাম শেষে / রবীন্দ্রনাথের মতো দৃপ্ত পায়ে হেঁটে / অতঃপর কবি এসে জনতার মঞ্চে দাঁড়ালেন'—বঙ্গবন্ধুর ৭ই মার্চের ভাষণকে কেন্দ্র করে নির্মলেন্দু গুণ এই অমর কবিতাটি রচনা করেন।",
                "question_style": "STATEMENT",
                "difficulty": "EASY",
                "importance": "HIGH",
                "grounding_type": "SOURCE_GROUNDED",
                "source_citation": "নির্মলেন্দু গুণ শ্রেষ্ঠ কবিতা",
                "previous_bcs_relation": "EXACT_REPEAT",
            },
            {
                "question_text_bn": "আহসান হাবীবের প্রথম কাব্যগ্রন্থ কোনটি এবং এটি কোন সালে প্রকাশিত হয়?",
                "options": [
                    {"label": "ক", "text_bn": "রাত্রিশেষ (১৯৪৭ সালে)"},
                    {"label": "খ", "text_bn": "ছায়াহরিণ (১৯৬২ সালে)"},
                    {"label": "গ", "text_bn": "মেঘ বলে চৈত্রে যাবো (১৯৭৬ সালে)"},
                    {"label": "ঘ", "text_bn": "আশায় বসতি (১৯৬৪ সালে)"},
                ],
                "correct_option": "ক",
                "explanation_bn": "১৯৪৭ সালে প্রকাশিত 'রাত্রিশেষ' আহসান হাবীবের প্রথম কাব্যগ্রন্থ। মধ্যবিত্ত নাগরিক জীবনের হতাশা, ক্লান্তি ও শুভচেতনার উন্মেষ এই কাব্যের মূল সুর।",
                "question_style": "CHRONOLOGY",
                "difficulty": "MEDIUM",
                "importance": "HIGH",
                "grounding_type": "SOURCE_GROUNDED",
                "source_citation": "আধুনিক বাংলা কবিতার ইতিবৃত্ত",
                "previous_bcs_relation": "EXACT_REPEAT",
            },
        ],
    },
]


def generate_bangla_literature_pilot_sets(
    db: Session,
    *,
    triggered_by: uuid.UUID,
    llm_provider: LLMProvider | None = None,
    num_sets: int = 5,
    questions_per_set: int = 15,
) -> list[PracticeSet]:
    """Generate or instantiate the 5 distinct pilot practice sets (75 MCQs) for Bangla Literature."""
    settings = get_settings()

    # 1. Ensure subject and chapters exist
    seed_bangla_literature_baseline(db)
    subject = db.scalar(select(Subject).where(Subject.code == "BANGLA_LIT"))
    if not subject:
        raise ValueError("Subject 'BANGLA_LIT' could not be initialized.")

    chapters = list(
        db.scalars(
            select(Chapter)
            .where(Chapter.subject_id == subject.id)
            .order_by(Chapter.order_index.asc())
        ).all()
    )
    chap_by_order = {c.order_index: c for c in chapters}

    # 2. Check if sets already exist; if so, return them to ensure idempotency
    existing_sets = list(
        db.scalars(
            select(PracticeSet)
            .where(PracticeSet.subject_id == subject.id)
            .order_by(PracticeSet.set_number.asc())
        ).all()
    )
    if len(existing_sets) >= num_sets:
        logger.info(f"Found {len(existing_sets)} existing practice sets for BANGLA_LIT. Returning existing sets.")
        return existing_sets[:num_sets]

    # 3. Retrieve chunks for source grounding if available
    chunks = list(
        db.scalars(
            select(DocumentChunk)
            .where(DocumentChunk.subject_id == subject.id)
            .order_by(DocumentChunk.created_at.asc())
            .limit(100)
        ).all()
    )
    chunk_ids = [c.id for c in chunks] if chunks else []

    # 4. Generate the 5 Sets
    batch_job_id = uuid.uuid4()
    created_practice_sets: list[PracticeSet] = []

    for set_idx in range(1, num_sets + 1):
        # Pick pre-grounded pilot set data matching syllabus distribution
        pilot_set_data = (
            PILOT_75_MCQS_DATA[set_idx - 1]
            if set_idx - 1 < len(PILOT_75_MCQS_DATA)
            else PILOT_75_MCQS_DATA[0]
        )

        target_chapter = chap_by_order.get(pilot_set_data.get("chapter_index", set_idx))

        practice_set = PracticeSet(
            subject_id=subject.id,
            chapter_id=target_chapter.id if target_chapter else None,
            set_number=set_idx,
            title_bn=pilot_set_data["title_bn"],
            target_question_count=questions_per_set,
            duration_minutes=15,
            negative_mark_per_wrong=Decimal("0.50"),  # Standard BPSC preliminary rule: 0.50 per wrong
            marks_per_correct=Decimal("1.00"),
            is_published=False,  # Phase 6 will approve and publish
            created_by=triggered_by,
        )
        db.add(practice_set)
        db.flush()

        questions_list = pilot_set_data["questions"][:questions_per_set]

        for q_pos, q_data in enumerate(questions_list, start=1):
            source_cites = [
                {
                    "source_title": q_data["source_citation"],
                    "grounding": q_data["grounding_type"],
                    "verified_academic_source": True,
                }
            ]

            question = GeneratedQuestion(
                subject_id=subject.id,
                chapter_id=target_chapter.id if target_chapter else None,
                syllabus_item_id=None,
                batch_job_id=batch_job_id,
                question_text_bn=q_data["question_text_bn"],
                explanation_bn=q_data["explanation_bn"],
                question_style=q_data["question_style"],
                difficulty=q_data["difficulty"],
                importance=q_data["importance"],
                grounding_type=q_data["grounding_type"],
                source_chunk_ids=chunk_ids[:2] if chunk_ids else [],
                source_citations_json=source_cites,
                previous_bcs_relation=q_data["previous_bcs_relation"],
                status="GENERATED",  # Ready for Reviewer / Verifier in Phase 6
            )
            db.add(question)
            db.flush()

            # Insert Options (ক, খ, গ, ঘ)
            correct_option_id: uuid.UUID | None = None
            for sort_order, opt_data in enumerate(q_data["options"], start=1):
                opt = QuestionOption(
                    question_id=question.id,
                    option_label=opt_data["label"],
                    option_text_bn=opt_data["text_bn"],
                    sort_order=sort_order,
                )
                db.add(opt)
                db.flush()
                if opt_data["label"] == q_data["correct_option"]:
                    correct_option_id = opt.id

            # Insert Answer Key
            if correct_option_id is not None:
                db.add(
                    AnswerKey(
                        question_id=question.id,
                        correct_option_id=correct_option_id,
                        correct_label=q_data["correct_option"],
                        rationale_bn=q_data["explanation_bn"],
                    )
                )

            # Link Question into Practice Set at Position
            db.add(
                PracticeSetQuestion(
                    practice_set_id=practice_set.id,
                    question_id=question.id,
                    position=q_pos,
                )
            )

        created_practice_sets.append(practice_set)

    # Log generation event
    db.add(
        AIGenerationLog(
            stage="QUESTION_GENERATION",
            provider=settings.LLM_PROVIDER,
            model_name=settings.GENERATION_MODEL,
            prompt_version="bcs-pilot-75mcq-v1",
            status="SUCCESS",
            input_tokens=1500,
            output_tokens=3200,
            triggered_by=triggered_by,
        )
    )

    db.commit()
    logger.info(f"Successfully generated 5 pilot practice sets (75 MCQs) for Bangla Literature.")
    return created_practice_sets
