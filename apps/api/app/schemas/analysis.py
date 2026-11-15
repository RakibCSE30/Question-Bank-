from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, Field


class AuthorEntity(BaseModel):
    name_bn: str = Field(description="সাহিত্যিকের নাম (বাংলায়)")
    pen_name_or_title: str | None = Field(default=None, description="ছদ্মনাম বা উপাধি (যেমন: ভানুসিংহ ঠাকুর, বিশ্বকবি)")
    era_or_period: str = Field(description="সাহিত্যের যুগ (প্রাচীন, মধ্য, আধুনিক)")
    notable_works: list[str] = Field(default_factory=list, description="প্রধান সাহিত্যকর্ম")
    significance: str = Field(description="বিসিএস সিলেবাসের গুরুত্ব ও তাৎপর্য")


class LiteraryWorkEntity(BaseModel):
    title_bn: str = Field(description="গ্রন্থের নাম")
    author_name_bn: str = Field(description="রচয়িতার নাম")
    genre: str = Field(description="ধারা/শ্রেণি (কাব্য, নাটক, উপন্যাস, প্রবন্ধ, ছোটগল্প, সাময়িকপত্র)")
    publication_year_or_era: str | None = Field(default=None, description="প্রকাশকাল বা রচনাকাল")
    major_characters: list[str] = Field(default_factory=list, description="প্রধান চরিত্রসমূহ")
    themes: list[str] = Field(default_factory=list, description="মূল বিষয়বস্তু ও উপজীব্য")


class LiteraryPeriodSummary(BaseModel):
    period_code: str
    period_name_bn: str
    span_years: str
    key_characteristics: str
    core_topics: list[str]
    bcs_mark_weight: int = Field(description="বিসিএস প্রিলিমিনারিতে সম্ভাব্য নম্বর বণ্টন")


class TopicPriorityItem(BaseModel):
    topic_bn: str
    chapter_name_bn: str
    priority: Literal["HIGH", "MEDIUM", "LOW"]
    priority_reason: str
    weight_percentage: float
    previous_bcs_frequency: int = Field(default=0, description="বিগত বিসিএস পরীক্ষায় এই টপিক থেকে আসা প্রশ্নের সংখ্যা")


class PreviousQuestionsTrendAnalysis(BaseModel):
    total_previous_questions: int
    subject_code: str
    factual_percentage: float
    author_work_percentage: float
    chronology_percentage: float
    conceptual_percentage: float
    most_tested_authors: list[dict[str, str | int]]
    frequently_tested_topics: list[str]
    underrepresented_topics: list[str]
    disclaimer: str = Field(
        default="অতীতের ফ্রিকোয়েন্সি কোনোভাবেই ভবিষ্যৎ পরীক্ষায় প্রশ্ন আসার নিশ্চয়তা প্রদান করে না।"
    )


class BanglaLiteratureAnalysisReport(BaseModel):
    subject_code: str
    subject_name_bn: str
    authors: list[AuthorEntity]
    literary_works: list[LiteraryWorkEntity]
    periods: list[LiteraryPeriodSummary]
    topic_priorities: list[TopicPriorityItem]
    previous_trends: PreviousQuestionsTrendAnalysis
