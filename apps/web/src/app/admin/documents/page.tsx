"use client";

import React, { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  AlertTriangle,
  CheckCircle2,
  Database,
  Eye,
  FileUp,
  Loader2,
  RefreshCw,
  Trash2,
} from "lucide-react";
import { AppShell } from "@/components/layout/AppShell";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/StateViews";
import { useI18n } from "@/i18n/I18nContext";
import { apiFetch, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type {
  Chapter,
  DocumentItem,
  DocumentListResponse,
  SourceType,
  Subject,
} from "@/types";

export default function AdminDocumentsPage() {
  const { user } = useAuth();
  const { locale, formatNumber } = useI18n();
  const isAdmin = user?.role === "ADMIN";

  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [chapters, setChapters] = useState<Chapter[]>([]);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Upload form
  const [subjectId, setSubjectId] = useState("");
  const [chapterId, setChapterId] = useState("");
  const [sourceType, setSourceType] = useState<SourceType>("TEXTBOOK");
  const [title, setTitle] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    try {
      const [subjList, docRes] = await Promise.all([
        apiFetch<Subject[]>("/subjects"),
        apiFetch<DocumentListResponse>("/admin/documents"),
      ]);
      setSubjects(subjList);
      setDocuments(docRes.items);
      if (subjList.length > 0 && !subjectId) {
        setSubjectId(subjList[0].id);
      }
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load documents");
    } finally {
      setLoading(false);
    }
  }, [subjectId]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  useEffect(() => {
    if (!subjectId) {
      setChapters([]);
      return;
    }
    void apiFetch<Chapter[]>(`/subjects/${subjectId}/chapters`)
      .then(setChapters)
      .catch(() => setChapters([]));
  }, [subjectId]);

  // Auto-poll while any document is PENDING or PROCESSING
  useEffect(() => {
    const hasActive = documents.some(
      (d) => d.ingestion_status === "PENDING" || d.ingestion_status === "PROCESSING"
    );
    if (!hasActive) return;
    const timer = window.setInterval(() => {
      void loadData();
    }, 3000);
    return () => window.clearInterval(timer);
  }, [documents, loadData]);

  async function handleUpload(e: React.FormEvent) {
    e.preventDefault();
    if (!file || !subjectId) return;
    setUploadError(null);
    setUploading(true);
    try {
      const form = new FormData();
      form.append("subject_id", subjectId);
      if (chapterId) form.append("chapter_id", chapterId);
      form.append("title", title);
      form.append("source_type", sourceType);
      form.append("file", file);

      await apiFetch<DocumentItem>("/admin/documents/upload", {
        method: "POST",
        body: form,
      });
      setTitle("");
      setFile(null);
      await loadData();
    } catch (err) {
      setUploadError(err instanceof ApiError ? err.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  }

  async function handleConfirm(docId: string) {
    setUploadError(null);
    try {
      await apiFetch<DocumentItem>(`/admin/documents/${docId}/confirm`, { method: "POST" });
      await loadData();
    } catch (err) {
      setUploadError(err instanceof ApiError ? err.message : "Failed to confirm document");
    }
  }

  async function handleReprocessOcr(docId: string) {
    setUploadError(null);
    try {
      await apiFetch<DocumentItem>(`/admin/documents/${docId}/reprocess-ocr`, { method: "POST" });
      await loadData();
    } catch (err) {
      setUploadError(err instanceof ApiError ? err.message : "Failed to re-run OCR");
    }
  }

  async function handleIndexVectors(docId: string) {
    setUploadError(null);
    try {
      await apiFetch(`/admin/documents/${docId}/index-vectors`, { method: "POST" });
      await loadData();
    } catch (err) {
      setUploadError(err instanceof ApiError ? err.message : "Failed to index vectors");
    }
  }

  async function handleDelete(docId: string) {
    setUploadError(null);
    try {
      await apiFetch<void>(`/admin/documents/${docId}`, { method: "DELETE" });
      await loadData();
    } catch (err) {
      setUploadError(err instanceof ApiError ? err.message : "Failed to delete document");
    }
  }

  return (
    <AppShell allowedRoles={["ADMIN", "REVIEWER"]}>
      <div className="space-y-6">
        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <h1 className="text-2xl font-bold text-slate-900">
            {locale === "bn" ? "পাঠ্যবই ও নথি ব্যবস্থাপনা" : "Study Material & OCR Processing"}
          </h1>
          <p className="mt-1 text-sm text-slate-600">
            {locale === "bn"
              ? "PDF, DOCX, TXT বা ছবি আপলোড করুন। বিজয়/অস্পষ্ট বাংলা ফন্ট স্বয়ংক্রিয়ভাবে শনাক্ত হয়ে Tesseract OCR (ben+eng) দিয়ে প্রক্রিয়াজাত হয়।"
              : "Upload PDF, DOCX, TXT, or images. Legacy Bijoy/scanned pages automatically trigger Tesseract ben+eng OCR."}
          </p>

          {isAdmin && (
            <form onSubmit={handleUpload} className="mt-5 grid grid-cols-1 gap-3 md:grid-cols-6">
              <select
                required
                value={subjectId}
                onChange={(e) => setSubjectId(e.target.value)}
                className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm md:col-span-2"
              >
                {subjects.length === 0 && (
                  <option value="">
                    {locale === "bn" ? "প্রথমে বিষয় তৈরি করুন" : "Create a subject first"}
                  </option>
                )}
                {subjects.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name_bn} ({s.name_en})
                  </option>
                ))}
              </select>

              <select
                value={chapterId}
                onChange={(e) => setChapterId(e.target.value)}
                className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
              >
                <option value="">{locale === "bn" ? "সব অধ্যায় (ঐচ্ছিক)" : "All Chapters (Optional)"}</option>
                {chapters.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.order_index}. {c.title_bn}
                  </option>
                ))}
              </select>

              <select
                value={sourceType}
                onChange={(e) => setSourceType(e.target.value as SourceType)}
                className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
              >
                <option value="TEXTBOOK">TEXTBOOK</option>
                <option value="SYLLABUS">SYLLABUS</option>
                <option value="PREVIOUS_BCS">PREVIOUS_BCS</option>
                <option value="NOTES">NOTES</option>
              </select>

              <input
                required
                minLength={2}
                placeholder={locale === "bn" ? "নথির শিরোনাম" : "Document Title"}
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="rounded-lg border border-slate-300 px-3 py-2 text-sm md:col-span-2"
              />

              <input
                required
                type="file"
                accept=".pdf,.docx,.txt,.png,.jpg,.jpeg,.webp"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                className="rounded-lg border border-slate-300 bg-slate-50 px-3 py-1.5 text-xs md:col-span-4"
              />

              <button
                type="submit"
                disabled={uploading || !subjectId || !file}
                className="inline-flex items-center justify-center gap-2 rounded-lg bg-emerald-800 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-900 disabled:opacity-60 md:col-span-2"
              >
                {uploading ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileUp className="h-4 w-4" />}
                <span>{locale === "bn" ? "আপলোড ও প্রক্রিয়াকরণ" : "Upload & Process"}</span>
              </button>
            </form>
          )}

          {uploadError && (
            <div className="mt-3 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
              {uploadError}
            </div>
          )}
        </div>

        {loading && <LoadingState />}
        {!loading && error && <ErrorState message={error} onRetry={() => void loadData()} />}

        {!loading && !error && documents.length === 0 && (
          <EmptyState
            title={locale === "bn" ? "এখনও কোনো নথি আপলোড করা হয়নি" : "No documents uploaded yet"}
            subtitle={
              locale === "bn"
                ? "প্রথমে সিলেবাস বা বাংলা সাহিত্য পিডিএফ আপলোড করুন।"
                : "Upload a syllabus or Bangla Literature study material above to start extraction."
            }
          />
        )}

        {!loading && !error && documents.length > 0 && (
          <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
            <table className="min-w-full divide-y divide-slate-200 text-sm">
              <thead className="bg-slate-50 text-left text-xs font-semibold uppercase text-slate-600">
                <tr>
                  <th className="px-4 py-3">{locale === "bn" ? "নথি" : "Document"}</th>
                  <th className="px-4 py-3">{locale === "bn" ? "পদ্ধতি" : "Method"}</th>
                  <th className="px-4 py-3">{locale === "bn" ? "পৃষ্ঠা / চাঙ্ক" : "Pages / Chunks"}</th>
                  <th className="px-4 py-3">{locale === "bn" ? "মান স্কোর" : "Quality"}</th>
                  <th className="px-4 py-3">{locale === "bn" ? "অবস্থা" : "Status"}</th>
                  <th className="px-4 py-3 text-right">{locale === "bn" ? "কার্যক্রম" : "Actions"}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {documents.map((doc) => (
                  <tr key={doc.id}>
                    <td className="px-4 py-3">
                      <div className="font-semibold text-slate-900">{doc.title}</div>
                      <div className="text-xs text-slate-500">
                        {doc.source_type} • {doc.file_name}
                      </div>
                      {doc.error_message && (
                        <div className="mt-1 text-xs text-amber-800">{doc.error_message}</div>
                      )}
                    </td>
                    <td className="px-4 py-3 text-xs font-medium text-slate-700">
                      <div>{doc.extraction_method}</div>
                      {doc.legacy_encoding_detected && (
                        <span className="mt-1 inline-block rounded bg-amber-100 px-1.5 py-0.5 text-[10px] font-semibold text-amber-900">
                          Bijoy/Legacy Detected
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-xs tabular-nums text-slate-700">
                      {formatNumber(doc.page_count ?? 0)}p / {formatNumber(doc.chunk_count)} chunks
                    </td>
                    <td className="px-4 py-3 text-xs font-bold tabular-nums">
                      {doc.extraction_quality_score !== null ? (
                        <span
                          className={`rounded-full px-2.5 py-0.5 ${
                            doc.extraction_quality_score >= 0.7
                              ? "bg-emerald-100 text-emerald-800"
                              : "bg-rose-100 text-rose-800"
                          }`}
                        >
                          {doc.extraction_quality_score.toFixed(2)}
                        </span>
                      ) : (
                        "—"
                      )}
                    </td>
                    <td className="px-4 py-3 text-xs">
                      <div className="flex flex-col gap-1">
                        <span
                          className={`inline-flex w-fit items-center gap-1 rounded-full px-2.5 py-0.5 font-semibold ${
                            doc.ingestion_status === "COMPLETED"
                              ? "bg-emerald-100 text-emerald-900"
                              : doc.ingestion_status === "FLAGGED"
                                ? "bg-amber-100 text-amber-900"
                                : doc.ingestion_status === "FAILED"
                                  ? "bg-rose-100 text-rose-900"
                                  : "bg-slate-100 text-slate-700"
                          }`}
                        >
                          {doc.ingestion_status === "FLAGGED" && <AlertTriangle className="h-3 w-3" />}
                          {doc.ingestion_status}
                        </span>
                        <span className="text-[11px] text-slate-500">
                          {doc.usable_for_generation
                            ? locale === "bn"
                              ? "জেনারেশনের জন্য প্রস্তুত"
                              : "Usable for generation"
                            : locale === "bn"
                              ? "জেনারেশনে ব্লককৃত"
                              : "Blocked from generation"}
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="inline-flex flex-wrap items-center justify-end gap-1.5">
                        <Link
                          href={`/admin/documents/${doc.id}`}
                          className="inline-flex items-center gap-1 rounded-md border border-slate-300 px-2.5 py-1 text-xs font-semibold text-slate-700 hover:bg-slate-50"
                        >
                          <Eye className="h-3.5 w-3.5" />
                          <span>{locale === "bn" ? "পরিদর্শন" : "Inspect"}</span>
                        </Link>
                        {isAdmin && doc.ingestion_status === "FLAGGED" && !doc.admin_confirmed_low_quality && (
                          <button
                            type="button"
                            onClick={() => void handleConfirm(doc.id)}
                            className="inline-flex items-center gap-1 rounded-md bg-amber-600 px-2.5 py-1 text-xs font-semibold text-white hover:bg-amber-700"
                          >
                            <CheckCircle2 className="h-3.5 w-3.5" />
                            <span>{locale === "bn" ? "অনুমোদন" : "Confirm"}</span>
                          </button>
                        )}
                        {isAdmin && (
                          <>
                            <button
                              type="button"
                              onClick={() => void handleIndexVectors(doc.id)}
                              className="inline-flex items-center gap-1 rounded-md border border-slate-300 px-2.5 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50"
                              title="Embed & Index in Qdrant"
                            >
                              <Database className="h-3.5 w-3.5" />
                              <span>Index</span>
                            </button>
                            <button
                              type="button"
                              onClick={() => void handleReprocessOcr(doc.id)}
                              className="inline-flex items-center gap-1 rounded-md border border-slate-300 px-2.5 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50"
                              title="Re-run Tesseract OCR"
                            >
                              <RefreshCw className="h-3.5 w-3.5" />
                              <span>OCR</span>
                            </button>
                            <button
                              type="button"
                              onClick={() => void handleDelete(doc.id)}
                              className="inline-flex items-center gap-1 rounded-md border border-rose-200 px-2 py-1 text-xs font-medium text-rose-700 hover:bg-rose-50"
                              title="Delete Document"
                            >
                              <Trash2 className="h-3.5 w-3.5" />
                            </button>
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </AppShell>
  );
}
