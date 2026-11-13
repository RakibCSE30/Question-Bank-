"""Initial normalized schema for all 21 tables and system roles.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-11-13
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. roles
    op.create_table(
        "roles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=32), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("name IN ('ADMIN', 'REVIEWER', 'STUDENT')", name="ck_roles_valid_name"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    # 2. users
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("preferred_lang", sa.String(length=8), nullable=False, server_default="bn"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("refresh_token_hash", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("preferred_lang IN ('bn', 'en')", name="ck_users_preferred_lang"),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_role_id", "users", ["role_id"])

    # 3. subjects
    op.create_table(
        "subjects",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name_bn", sa.String(length=255), nullable=False),
        sa.Column("name_en", sa.String(length=255), nullable=False),
        sa.Column("bcs_total_marks", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )

    # 4. chapters
    op.create_table(
        "chapters",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("subject_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("title_bn", sa.String(length=255), nullable=False),
        sa.Column("title_en", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("subject_id", "order_index", name="uq_chapters_subject_order"),
    )
    op.create_index("ix_chapters_subject_id", "chapters", ["subject_id"])

    # 5. syllabus_items
    op.create_table(
        "syllabus_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("subject_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chapter_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("topic_bn", sa.String(length=500), nullable=False),
        sa.Column("topic_en", sa.String(length=500), nullable=True),
        sa.Column("weight_percentage", sa.Numeric(precision=5, scale=2), nullable=False, server_default="0.00"),
        sa.Column("priority", sa.String(length=16), nullable=False, server_default="MEDIUM"),
        sa.Column("priority_reason", sa.Text(), nullable=True),
        sa.Column("source_reference", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("priority IN ('HIGH', 'MEDIUM', 'LOW')", name="ck_syllabus_priority"),
        sa.CheckConstraint("weight_percentage >= 0 AND weight_percentage <= 100", name="ck_syllabus_weight"),
        sa.ForeignKeyConstraint(["chapter_id"], ["chapters.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_syllabus_subject_chapter_priority", "syllabus_items", ["subject_id", "chapter_id", "priority"])

    # 6. documents
    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("uploaded_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("subject_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chapter_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=128), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256_hash", sa.String(length=64), nullable=False),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("extraction_method", sa.String(length=32), nullable=False, server_default="PYMUPDF"),
        sa.Column("legacy_encoding_detected", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("extraction_quality_score", sa.Numeric(precision=4, scale=3), nullable=True),
        sa.Column("admin_confirmed_low_quality", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("ingestion_status", sa.String(length=24), nullable=False, server_default="PENDING"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "source_type IN ('SYLLABUS', 'PREVIOUS_BCS', 'TEXTBOOK', 'NOTES')",
            name="ck_documents_source_type",
        ),
        sa.CheckConstraint(
            "extraction_method IN ('PYMUPDF', 'DOCX', 'OCR_TESSERACT', 'TXT', 'IMAGE_OCR')",
            name="ck_documents_extraction_method",
        ),
        sa.CheckConstraint(
            "ingestion_status IN ('PENDING', 'PROCESSING', 'COMPLETED', 'FLAGGED', 'FAILED')",
            name="ck_documents_ingestion_status",
        ),
        sa.ForeignKeyConstraint(["chapter_id"], ["chapters.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["uploaded_by"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sha256_hash"),
    )
    op.create_index("ix_documents_subject_chapter_status", "documents", ["subject_id", "chapter_id", "ingestion_status"])

    # 7. document_chunks
    op.create_table(
        "document_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("subject_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chapter_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("heading_path", sa.Text(), nullable=True),
        sa.Column("content_nfc", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("vector_point_id", sa.String(length=128), nullable=True),
        sa.Column("extraction_confidence", sa.Numeric(precision=4, scale=3), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["chapter_id"], ["chapters.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_id", "chunk_index", name="uq_doc_chunks_doc_index"),
    )
    op.create_index("ix_doc_chunks_subject_chapter_page", "document_chunks", ["subject_id", "chapter_id", "page_number"])

    # 8. previous_questions
    op.create_table(
        "previous_questions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("subject_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chapter_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("syllabus_item_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("bcs_batch", sa.String(length=64), nullable=False),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("question_text_bn", sa.Text(), nullable=False),
        sa.Column("options_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("correct_option", sa.String(length=8), nullable=False),
        sa.Column("question_type", sa.String(length=32), nullable=False, server_default="FACTUAL"),
        sa.Column("difficulty", sa.String(length=16), nullable=False, server_default="MEDIUM"),
        sa.Column("extracted_authors_works", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("source_document_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("vector_point_id", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("difficulty IN ('EASY', 'MEDIUM', 'HARD')", name="ck_prev_q_difficulty"),
        sa.ForeignKeyConstraint(["chapter_id"], ["chapters.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_document_id"], ["documents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["syllabus_item_id"], ["syllabus_items.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_prev_questions_subject_batch", "previous_questions", ["subject_id", "bcs_batch"])

    # 9. generated_questions
    op.create_table(
        "generated_questions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("subject_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chapter_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("syllabus_item_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("batch_job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("question_text_bn", sa.Text(), nullable=False),
        sa.Column("explanation_bn", sa.Text(), nullable=False),
        sa.Column("question_style", sa.String(length=24), nullable=False),
        sa.Column("difficulty", sa.String(length=16), nullable=False),
        sa.Column("importance", sa.String(length=16), nullable=False),
        sa.Column("grounding_type", sa.String(length=24), nullable=False),
        sa.Column("source_chunk_ids", postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=False),
        sa.Column("source_citations_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("verified_previous_bcs_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("previous_bcs_relation", sa.String(length=24), nullable=False, server_default="NONE"),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="GENERATED"),
        sa.Column("reviewed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("vector_point_id", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "question_style IN ('FACTUAL', 'AUTHOR_WORK', 'CHRONOLOGY', 'CONCEPTUAL', "
            "'STATEMENT', 'COMPARATIVE', 'ANALYTICAL', 'TRICKY')",
            name="ck_gen_q_style",
        ),
        sa.CheckConstraint("difficulty IN ('EASY', 'MEDIUM', 'HARD')", name="ck_gen_q_difficulty"),
        sa.CheckConstraint("importance IN ('HIGH', 'MEDIUM', 'LOW')", name="ck_gen_q_importance"),
        sa.CheckConstraint("grounding_type IN ('SOURCE_GROUNDED', 'AI_INFERENCE')", name="ck_gen_q_grounding"),
        sa.CheckConstraint(
            "previous_bcs_relation IN ('EXACT_REPEAT', 'SIMILAR_TOPIC', 'NONE')",
            name="ck_gen_q_prev_bcs_rel",
        ),
        sa.CheckConstraint(
            "status IN ('GENERATED', 'VERIFIED', 'NEEDS_REVIEW', 'REJECTED', 'APPROVED')",
            name="ck_gen_q_status",
        ),
        sa.ForeignKeyConstraint(["chapter_id"], ["chapters.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reviewed_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["syllabus_item_id"], ["syllabus_items.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["verified_previous_bcs_id"], ["previous_questions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_gen_questions_status_subj_chap", "generated_questions", ["status", "subject_id", "chapter_id"])
    op.create_index("ix_gen_questions_batch_job", "generated_questions", ["batch_job_id"])

    # 10. question_options
    op.create_table(
        "question_options",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("question_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("option_label", sa.String(length=8), nullable=False),
        sa.Column("option_text_bn", sa.Text(), nullable=False),
        sa.Column("sort_order", sa.SmallInteger(), nullable=False),
        sa.CheckConstraint("option_label IN ('ক', 'খ', 'গ', 'ঘ')", name="ck_option_label_bengali"),
        sa.CheckConstraint("sort_order >= 1 AND sort_order <= 4", name="ck_option_sort_order"),
        sa.ForeignKeyConstraint(["question_id"], ["generated_questions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("question_id", "option_label", name="uq_question_options_label"),
    )

    # 11. answer_keys
    op.create_table(
        "answer_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("question_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("correct_option_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("correct_label", sa.String(length=8), nullable=False),
        sa.Column("rationale_bn", sa.Text(), nullable=True),
        sa.CheckConstraint("correct_label IN ('ক', 'খ', 'গ', 'ঘ')", name="ck_answer_key_label"),
        sa.ForeignKeyConstraint(["correct_option_id"], ["question_options.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["question_id"], ["generated_questions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("question_id"),
    )

    # 12. question_verifications
    op.create_table(
        "question_verifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("question_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("verdict", sa.String(length=24), nullable=False),
        sa.Column("source_support_score", sa.Numeric(precision=4, scale=3), nullable=False),
        sa.Column("answer_correctness_ok", sa.Boolean(), nullable=False),
        sa.Column("ambiguity_detected", sa.Boolean(), nullable=False),
        sa.Column("unsupported_claims", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("semantic_duplicate_of_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("max_similarity_score", sa.Numeric(precision=4, scale=3), nullable=True),
        sa.Column("option_quality_ok", sa.Boolean(), nullable=False),
        sa.Column("source_conflict_detected", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("reasons_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("verifier_model", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("verdict IN ('VERIFIED', 'NEEDS_REVIEW', 'REJECTED')", name="ck_q_verification_verdict"),
        sa.ForeignKeyConstraint(["question_id"], ["generated_questions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["semantic_duplicate_of_id"], ["generated_questions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_question_verifications_q_verdict", "question_verifications", ["question_id", "verdict"])

    # 13. practice_sets
    op.create_table(
        "practice_sets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("subject_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chapter_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("set_number", sa.Integer(), nullable=False),
        sa.Column("title_bn", sa.String(length=255), nullable=False),
        sa.Column("target_question_count", sa.Integer(), nullable=False, server_default="15"),
        sa.Column("duration_minutes", sa.Integer(), nullable=False, server_default="15"),
        sa.Column("negative_mark_per_wrong", sa.Numeric(precision=4, scale=2), nullable=False, server_default="0.00"),
        sa.Column("marks_per_correct", sa.Numeric(precision=4, scale=2), nullable=False, server_default="1.00"),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("negative_mark_per_wrong >= 0", name="ck_practice_sets_nonneg_penalty"),
        sa.CheckConstraint("marks_per_correct > 0", name="ck_practice_sets_pos_marks"),
        sa.CheckConstraint("duration_minutes > 0", name="ck_practice_sets_pos_duration"),
        sa.ForeignKeyConstraint(["chapter_id"], ["chapters.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_practice_sets_subject_published", "practice_sets", ["subject_id", "is_published"])

    # 14. practice_set_questions
    op.create_table(
        "practice_set_questions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("practice_set_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("question_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["practice_set_id"], ["practice_sets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["question_id"], ["generated_questions.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("practice_set_id", "position", name="uq_practice_set_q_pos"),
        sa.UniqueConstraint("practice_set_id", "question_id", name="uq_practice_set_q_unique"),
    )

    # 15. test_attempts
    op.create_table(
        "test_attempts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("practice_set_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="IN_PROGRESS"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_questions", sa.Integer(), nullable=False),
        sa.Column("correct_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("incorrect_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unanswered_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("raw_score", sa.Numeric(precision=6, scale=2), nullable=False, server_default="0.00"),
        sa.Column("negative_deduction", sa.Numeric(precision=6, scale=2), nullable=False, server_default="0.00"),
        sa.Column("final_score", sa.Numeric(precision=6, scale=2), nullable=False, server_default="0.00"),
        sa.Column("time_spent_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.CheckConstraint("status IN ('IN_PROGRESS', 'SUBMITTED', 'TIMED_OUT')", name="ck_test_attempts_status"),
        sa.ForeignKeyConstraint(["practice_set_id"], ["practice_sets.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["student_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_test_attempts_student_started", "test_attempts", ["student_id", "started_at"])
    op.create_index("ix_test_attempts_practice_set", "test_attempts", ["practice_set_id"])

    # 16. student_responses
    op.create_table(
        "student_responses",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("attempt_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("question_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("selected_option_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_marked_for_review", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_correct", sa.Boolean(), nullable=True),
        sa.Column("time_spent_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("answered_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["attempt_id"], ["test_attempts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["question_id"], ["generated_questions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["selected_option_id"], ["question_options.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("attempt_id", "question_id", name="uq_student_resp_attempt_q"),
    )

    # 17. performance_reports
    op.create_table(
        "performance_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("attempt_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("accuracy_pct", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("topic_breakdown_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("difficulty_breakdown_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("weak_topics_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("revision_recommendations_bn", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["attempt_id"], ["test_attempts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["student_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("attempt_id"),
    )
    op.create_index("ix_perf_reports_student_created", "performance_reports", ["student_id", "created_at"])

    # 18. written_questions
    op.create_table(
        "written_questions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("subject_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chapter_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("syllabus_item_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("prompt_bn", sa.Text(), nullable=False),
        sa.Column("max_marks", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("model_answer_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("rubric_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("source_chunk_ids", postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=False),
        sa.Column("grounding_type", sa.String(length=24), nullable=False, server_default="SOURCE_GROUNDED"),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="GENERATED"),
        sa.Column("reviewed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("max_marks > 0", name="ck_written_q_pos_marks"),
        sa.CheckConstraint("grounding_type IN ('SOURCE_GROUNDED', 'AI_INFERENCE')", name="ck_written_q_grounding"),
        sa.CheckConstraint(
            "status IN ('GENERATED', 'VERIFIED', 'NEEDS_REVIEW', 'REJECTED', 'APPROVED')",
            name="ck_written_q_status",
        ),
        sa.ForeignKeyConstraint(["chapter_id"], ["chapters.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reviewed_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["syllabus_item_id"], ["syllabus_items.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_written_questions_subj_status", "written_questions", ["subject_id", "status"])

    # 19. ai_generation_logs
    op.create_table(
        "ai_generation_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("stage", sa.String(length=32), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("model_name", sa.String(length=128), nullable=False),
        sa.Column("prompt_version", sa.String(length=64), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("estimated_cost_usd", sa.Numeric(precision=10, scale=6), nullable=False, server_default="0.000000"),
        sa.Column("latency_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("triggered_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "stage IN ('INGEST_EXTRACT', 'CONTENT_ANALYSIS', 'MCQ_GEN', 'VERIFICATION', 'WRITTEN_GEN', 'WRITTEN_EVAL')",
            name="ck_ai_logs_stage",
        ),
        sa.CheckConstraint("status IN ('SUCCESS', 'VALIDATION_ERROR', 'PROVIDER_ERROR')", name="ck_ai_logs_status"),
        sa.ForeignKeyConstraint(["triggered_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_logs_stage_created", "ai_generation_logs", ["stage", "created_at"])

    # 20. written_answers
    op.create_table(
        "written_answers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("written_question_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("answer_text_bn", sa.Text(), nullable=False),
        sa.Column("estimated_score", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("rubric_scores_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("feedback_bn", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "disclaimer_label",
            sa.String(length=255),
            nullable=False,
            server_default="Educational estimate, not an official examiner score",
        ),
        sa.Column("ai_log_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["ai_log_id"], ["ai_generation_logs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["student_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["written_question_id"], ["written_questions.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_written_answers_student_created", "written_answers", ["student_id", "created_at"])

    # 21. audit_logs
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("actor_role", sa.String(length=32), nullable=True),
        sa.Column("action", sa.String(length=128), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("before_state", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("after_state", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_logs_entity", "audit_logs", ["entity_type", "entity_id"])
    op.create_index("ix_audit_logs_created", "audit_logs", ["created_at"])

    # Seed immutable system roles
    op.execute(
        """
        INSERT INTO roles (name, description, created_at) VALUES
        ('ADMIN', 'System administrator: users, curriculum, documents, generation, marking rules, reports', NOW()),
        ('REVIEWER', 'Human quality reviewer: inspect citations, edit, approve or reject questions', NOW()),
        ('STUDENT', 'Learner: take approved mock tests, view analytics and written practice', NOW())
        ON CONFLICT (name) DO NOTHING;
        """
    )


def downgrade() -> None:
    op.drop_index("ix_audit_logs_created", table_name="audit_logs")
    op.drop_index("ix_audit_logs_entity", table_name="audit_logs")
    op.drop_table("audit_logs")
    op.drop_index("ix_written_answers_student_created", table_name="written_answers")
    op.drop_table("written_answers")
    op.drop_index("ix_ai_logs_stage_created", table_name="ai_generation_logs")
    op.drop_table("ai_generation_logs")
    op.drop_index("ix_written_questions_subj_status", table_name="written_questions")
    op.drop_table("written_questions")
    op.drop_index("ix_perf_reports_student_created", table_name="performance_reports")
    op.drop_table("performance_reports")
    op.drop_table("student_responses")
    op.drop_index("ix_test_attempts_practice_set", table_name="test_attempts")
    op.drop_index("ix_test_attempts_student_started", table_name="test_attempts")
    op.drop_table("test_attempts")
    op.drop_table("practice_set_questions")
    op.drop_index("ix_practice_sets_subject_published", table_name="practice_sets")
    op.drop_table("practice_sets")
    op.drop_index("ix_question_verifications_q_verdict", table_name="question_verifications")
    op.drop_table("question_verifications")
    op.drop_table("answer_keys")
    op.drop_table("question_options")
    op.drop_index("ix_gen_questions_batch_job", table_name="generated_questions")
    op.drop_index("ix_gen_questions_status_subj_chap", table_name="generated_questions")
    op.drop_table("generated_questions")
    op.drop_index("ix_prev_questions_subject_batch", table_name="previous_questions")
    op.drop_table("previous_questions")
    op.drop_index("ix_doc_chunks_subject_chapter_page", table_name="document_chunks")
    op.drop_table("document_chunks")
    op.drop_index("ix_documents_subject_chapter_status", table_name="documents")
    op.drop_table("documents")
    op.drop_index("ix_syllabus_subject_chapter_priority", table_name="syllabus_items")
    op.drop_table("syllabus_items")
    op.drop_index("ix_chapters_subject_id", table_name="chapters")
    op.drop_table("chapters")
    op.drop_table("subjects")
    op.drop_index("ix_users_role_id", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
    op.drop_table("roles")
