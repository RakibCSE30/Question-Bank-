"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  AlertTriangle,
  ArrowLeft,
  CheckCircle2,
  FileText,
  RefreshCw,
} from "lucide-react";
import { AppShell } from "@/components/layout/AppShell";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/StateViews";
import { useI18n } from "@/i18n/I18nContext";
import { apiFetch, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { DocumentDetail } from "@/types";

export default function DocumentInspectorPage() {
  const params = useParams<{ id: string }>();
  const documentId = params.id;
  const { user } = useAuth();
  const { locale, formatNumber } = useI18n();
  const isAdmin = user?.role === "ADMIN";

  const [doc, setDoc] = useState<DocumentDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [pageFilter, setPageFilter] = useState<string>("ALL");

  const loadDetail = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiFetch<DocumentDetail>(`/admin/documents/${documentId}`);
      setDoc(res);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load document detail");
    } finally {
      setLoading(false);
    }
  }, [documentId]);

  useEffect(() => {
    void loadDetail();
  }, [loadDetail]);

  const pageNumbers = useMemo(() => {
    if (!doc) return [];
    return Array.from(new Set(doc.chunks.map((c) => c.page_number))).sort((a, b) => a - b);
  }, [doc]);

  const visibleChunks = useMemo(() => {
    if (!doc) return [];
    if (pageFilter === "ALL") return doc.chunks;
    return doc.chunks.filter((c) => String(c.page_number) === pageFilter);
  }, [doc, pageFilter]);

  async function handleConfirm() {
    if (!doc) return;
    setActionError(null);
    try {
      await apiFetch(`/admin/documents/${doc.id}/confirm`, { method: "POST" });
      await loadDetail();
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Failed to confirm document");
    }
  }

  async function handleReprocessOcr() {
    if (!doc) return;
    setActionError(null);
    try {
      await apiFetch(`/admin/documents/${doc.id}/reprocess-ocr`, { method: "POST" });
      await loadDetail();
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Failed to re-run OCR");
    }
  }

  async function handleIndexVectors() {
    if (!doc) return;
    setActionError(null);
    try {
      await apiFetch(`/admin/documents/${doc.id}/index-vectors`, { method: "POST" });
      await loadDetail();
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Failed to index vectors");
    }
  }

  return (
    <AppShell allowedRoles={["ADMIN", "REVIEWER"]}>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <Link
            href="/admin/documents"
            className="inline-flex items-center gap-1.5 text-sm font-medium text-emerald-800 hover:underline"
          >
            <ArrowLeft className="h-4 w-4" />
            <span>{locale === "bn" ? "সকল নথিতে ফিরে যান" : "Back to Study Materials"}</span>
          </Link>
        </div>

        {loading && <LoadingState />}
        {!loading && error && <ErrorState message={error} onRetry={() => void loadDetail()} />}

        {!loading && !error && doc && (
          <>
            <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2 text-xs font-semibold uppercase text-emerald-800">
                    <FileText className="h-4 w-4" />
                    <span>{doc.source_type}</span>
                  </div>
                  <h1 className="mt-1 text-2xl font-bold text-slate-900">{doc.title}</h1>
                  <p className="mt-0.5 text-xs text-slate-500">{doc.file_name}</p>
                </div>

                {isAdmin && (
                  <div className="flex flex-wrap items-center gap-2">
                    {doc.ingestion_status === "FLAGGED" && !doc.admin_confirmed_low_quality && (
                      <button
                        type="button"
                        onClick={() => void handleConfirm()}
                        className="inline-flex items-center gap-1.5 rounded-lg bg-amber-600 px-3.5 py-2 text-xs font-semibold text-white hover:bg-amber-700"
                      >
                        <CheckCircle2 className="h-4 w-4" />
                        <span>
                          {locale === "bn"
                            ? "নিশ্চিত করুন ও জেনারেশনে অনুমতি দিন"
                            : "Confirm Low-Quality Doc for Generation"}
                        </span>
                      </button>
                    )}
                    <button
                      type="button"
                      onClick={() => void handleIndexVectors()}
                      className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3.5 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50"
                    >
                      <span>{locale === "bn" ? "ভেক্টর ইনডেক্স" : "Index Vectors"}</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => void handleReprocessOcr()}
                      className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3.5 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50"
                    >
                      <RefreshCw className="h-4 w-4" />
                      <span>{locale === "bn" ? "পুনরায় OCR চালান" : "Re-run OCR"}</span>
                    </button>
                  </div>
                )}
              </div>
              {actionError && (
                <div className="mt-4 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-700">
                  {actionError}
                </div>
              )}

              <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-5">
                <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                  <div className="text-[11px] text-slate-500">
                    {locale === "bn" ? "নিষ্কাশন পদ্ধতি" : "Extraction Method"}
                  </div>
                  <div className="mt-1 text-sm font-bold text-slate-900">{doc.extraction_method}</div>
                </div>
                <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                  <div className="text-[11px] text-slate-500">
                    {locale === "bn" ? "মোট পৃষ্ঠা" : "Page Count"}
                  </div>
                  <div className="mt-1 text-sm font-bold tabular-nums text-slate-900">
                    {formatNumber(doc.page_count ?? 0)}
                  </div>
                </div>
                <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                  <div className="text-[11px] text-slate-500">
                    {locale === "bn" ? "মান স্কোর" : "Quality Score"}
                  </div>
                  <div className="mt-1 text-sm font-bold tabular-nums text-slate-900">
                    {doc.extraction_quality_score !== null
                      ? doc.extraction_quality_score.toFixed(3)
                      : "—"}
                  </div>
                </div>
                <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                  <div className="text-[11px] text-slate-500">
                    {locale === "bn" ? "অবস্থা" : "Status"}
                  </div>
                  <div className="mt-1 text-sm font-bold text-slate-900">{doc.ingestion_status}</div>
                </div>
                <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                  <div className="text-[11px] text-slate-500">
                    {locale === "bn" ? "জেনারেশন যোগ্যতা" : "Generation Status"}
                  </div>
                  <div
                    className={`mt-1 text-sm font-bold ${
                      doc.usable_for_generation ? "text-emerald-800" : "text-rose-700"
                    }`}
                  >
                    {doc.usable_for_generation
                      ? locale === "bn"
                        ? "অনুমোদিত"
                        : "Usable"
                      : locale === "bn"
                        ? "ব্লককৃত"
                        : "Blocked"}
                  </div>
                </div>
              </div>

              {doc.ingestion_status === "FLAGGED" && (
                <div className="mt-4 flex items-start gap-2.5 rounded-lg border border-amber-300 bg-amber-50 p-3 text-xs text-amber-950">
                  <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-700" />
                  <div>
                    <span className="font-semibold">FLAGGED: </span>
                    {doc.error_message ||
                      "Quality score is below 0.70. Verify Bangla text below before confirming."}
                  </div>
                </div>
              )}
            </div>

            <div className="flex flex-wrap items-center justify-between gap-3">
              <h2 className="text-base font-bold text-slate-900">
                {locale === "bn"
                  ? `নিষ্কাশিত চাঙ্কসমূহ (${formatNumber(visibleChunks.length)})`
                  : `Extracted Chunks (${visibleChunks.length})`}
              </h2>
              <select
                value={pageFilter}
                onChange={(e) => setPageFilter(e.target.value)}
                className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium"
              >
                <option value="ALL">{locale === "bn" ? "সব পৃষ্ঠা" : "All Pages"}</option>
                {pageNumbers.map((p) => (
                  <option key={p} value={String(p)}>
                    {locale === "bn" ? `পৃষ্ঠা ${formatNumber(p)}` : `Page ${p}`}
                  </option>
                ))}
              </select>
            </div>

            {visibleChunks.length === 0 ? (
              <EmptyState
                title={locale === "bn" ? "কোনো চাঙ্ক পাওয়া যায়নি" : "No chunks available"}
                subtitle={
                  locale === "bn"
                    ? "নথি প্রক্রিয়াকরণ এখনও চলছে অথবা কোনো পাঠ্য পাওয়া যায়নি।"
                    : "Ingestion may still be processing or no text was extracted."
                }
              />
            ) : (
              <div className="space-y-3">
                {visibleChunks.map((chunk) => (
                  <div
                    key={chunk.id}
                    className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-2 text-xs text-slate-600">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="rounded bg-emerald-100 px-2 py-0.5 font-semibold text-emerald-900">
                          {locale === "bn"
                            ? `পৃষ্ঠা ${formatNumber(chunk.page_number)}`
                            : `Page ${chunk.page_number}`}
                        </span>
                        <span className="font-mono text-[11px] text-slate-500">
                          #{chunk.chunk_index}
                        </span>
                        {chunk.heading_path && (
                          <span className="font-semibold text-slate-800">
                            • {chunk.heading_path}
                          </span>
                        )}
                      </div>
                      <div className="tabular-nums text-[11px] text-slate-500">
                        {formatNumber(chunk.token_count)} tokens • conf{" "}
                        {chunk.extraction_confidence?.toFixed(2) ?? "—"}
                      </div>
                    </div>
                    <p className="mt-3 whitespace-pre-wrap text-sm leading-7 text-slate-900">
                      {chunk.content_nfc}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </AppShell>
  );
}
