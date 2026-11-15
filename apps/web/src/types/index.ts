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
