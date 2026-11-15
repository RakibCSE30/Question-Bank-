export type UserRole = "ADMIN" | "REVIEWER" | "STUDENT";
export type Locale = "bn" | "en";

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  preferred_lang: Locale;
  is_active: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface DashboardMetricCard {
  key: string;
  value: number | string;
}

export interface DashboardSummaryResponse {
  role: UserRole;
  phase: string;
  metrics: DashboardMetricCard[];
  notices: string[];
}

export interface UserListResponse {
  items: User[];
  total: number;
}

export interface Subject {
  id: string;
  code: string;
  name_bn: string;
  name_en: string;
  bcs_total_marks: number;
  is_active: boolean;
  created_at: string;
}

export interface Chapter {
  id: string;
  subject_id: string;
  order_index: number;
  title_bn: string;
  title_en: string | null;
  created_at: string;
}

export type SourceType = "SYLLABUS" | "PREVIOUS_BCS" | "TEXTBOOK" | "NOTES";

export interface DocumentItem {
  id: string;
  uploaded_by: string;
  subject_id: string;
  chapter_id: string | null;
  title: string;
  source_type: SourceType;
  file_name: string;
  mime_type: string;
  file_size_bytes: number;
  sha256_hash: string;
  extraction_method: string;
  legacy_encoding_detected: boolean;
  extraction_quality_score: number | null;
  admin_confirmed_low_quality: boolean;
  usable_for_generation: boolean;
  page_count: number | null;
  ingestion_status: "PENDING" | "PROCESSING" | "COMPLETED" | "FLAGGED" | "FAILED";
  error_message: string | null;
  chunk_count: number;
  created_at: string;
}

export interface DocumentChunkItem {
  id: string;
  chunk_index: number;
  page_number: number;
  heading_path: string | null;
  content_nfc: string;
  token_count: number;
  extraction_confidence: number | null;
  created_at: string;
}

export interface DocumentDetail extends DocumentItem {
  chunks: DocumentChunkItem[];
}

export interface DocumentListResponse {
  items: DocumentItem[];
  total: number;
}

// Phase 4: Literature Analysis Types
export interface AuthorEntity {
  name_bn: string;
  pen_name_or_title: string | null;
  era_or_period: string;
  notable_works: string[];
  significance: string;
}

export interface LiteraryWorkEntity {
  title_bn: string;
  author_name_bn: string;
  genre: string;
  publication_year_or_era: string | null;
  major_characters: string[];
  themes: string[];
}

export interface LiteraryPeriodSummary {
  period_code: string;
  period_name_bn: string;
  span_years: string;
  key_characteristics: string;
  core_topics: string[];
  bcs_mark_weight: number;
}

export interface TopicPriorityItem {
  topic_bn: string;
  chapter_name_bn: string;
  priority: "HIGH" | "MEDIUM" | "LOW";
  priority_reason: string;
  weight_percentage: number;
  previous_bcs_frequency: number;
}

export interface PreviousQuestionsTrendAnalysis {
  total_previous_questions: number;
  subject_code: string;
  factual_percentage: number;
  author_work_percentage: number;
  chronology_percentage: number;
  conceptual_percentage: number;
  most_tested_authors: Array<{ author: string; question_count: number }>;
  frequently_tested_topics: string[];
  underrepresented_topics: string[];
  disclaimer: string;
}

export interface BanglaLiteratureAnalysisReport {
  subject_code: string;
  subject_name_bn: string;
  authors: AuthorEntity[];
  literary_works: LiteraryWorkEntity[];
  periods: LiteraryPeriodSummary[];
  topic_priorities: TopicPriorityItem[];
  previous_trends: PreviousQuestionsTrendAnalysis;
}

// Phase 5: Question Generation & Practice Sets
export interface QuestionOptionItem {
  id: string;
  option_label: "ক" | "খ" | "গ" | "ঘ";
  option_text_bn: string;
  sort_order: number;
}

export interface AnswerKeyItem {
  id: string;
  correct_option_id: string;
  correct_label: "ক" | "খ" | "গ" | "ঘ";
  rationale_bn: string | null;
}

export interface GeneratedQuestionItem {
  id: string;
  subject_id: string;
  chapter_id: string | null;
  batch_job_id: string;
  question_text_bn: string;
  explanation_bn: string;
  question_style: string;
  difficulty: "EASY" | "MEDIUM" | "HARD";
  importance: "HIGH" | "MEDIUM" | "LOW";
  grounding_type: "SOURCE_GROUNDED" | "AI_INFERENCE";
  source_citations_json: Array<{ source_title?: string; grounding?: string }>;
  previous_bcs_relation: "EXACT_REPEAT" | "SIMILAR_TOPIC" | "NONE";
  status: "GENERATED" | "VERIFIED" | "NEEDS_REVIEW" | "REJECTED" | "APPROVED";
  options: QuestionOptionItem[];
  answer_key?: AnswerKeyItem;
  created_at: string;
}

export interface PracticeSetQuestionItem {
  id: string;
  position: number;
  question: GeneratedQuestionItem;
}

export interface PracticeSetItem {
  id: string;
  subject_id: string;
  chapter_id: string | null;
  set_number: number;
  title_bn: string;
  target_question_count: number;
  duration_minutes: number;
  negative_mark_per_wrong: number;
  marks_per_correct: number;
  is_published: boolean;
  question_count: number;
  created_at: string;
}

export interface PracticeSetDetail extends PracticeSetItem {
  items: PracticeSetQuestionItem[];
}
