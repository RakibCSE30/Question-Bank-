"use client";

import React, { useCallback, useEffect, useState } from "react";
import { Cpu, Loader2, Search, Sparkles } from "lucide-react";
import { AppShell } from "@/components/layout/AppShell";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/StateViews";
import { useI18n } from "@/i18n/I18nContext";
import { apiFetch, ApiError } from "@/lib/api";
import type { Subject } from "@/types";

interface AIStatus {
  llm_provider: string;
  generation_model: string;
  verification_model: string;
  verification_temperature: number;
  embedding_provider: string;
  embedding_model: string;
  bge_m3_model: string;
  openai_api_key_configured: boolean;
  bge_m3_installed: boolean;
  llm_ready: boolean;
  embedding_ready: boolean;
}

interface RetrievedChunk {
  chunk_id: string;
  document_id: string;
  document_title: string;
  source_type: string;
  page_number: number;
  heading_path: string | null;
  content_nfc: string;
  score: number;
  usable_for_generation: boolean;
}

export default function AdminRagPage() {
  const { locale, formatNumber } = useI18n();
  const [aiStatus, setAiStatus] = useState<AIStatus | null>(null);
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [subjectId, setSubjectId] = useState("");
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<RetrievedChunk[]>([]);
  const [hasSearched, setHasSearched] = useState(false);

  const [loadingInit, setLoadingInit] = useState(true);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchError, setSearchError] = useState<string | null>(null);

  const loadInit = useCallback(async () => {
    setLoadingInit(true);
    setError(null);
    try {
      const [statusRes, subjList] = await Promise.all([
        apiFetch<AIStatus>("/ai/status"),
        apiFetch<Subject[]>("/subjects"),
      ]);
      setAiStatus(statusRes);
      setSubjects(subjList);
      if (subjList.length > 0 && !subjectId) {
        setSubjectId(subjList[0].id);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load AI configuration status");
    } finally {
      setLoadingInit(false);
    }
  }, [subjectId]);

  useEffect(() => {
    void loadInit();
  }, [loadInit]);

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    if (!subjectId || !query.trim()) return;
    setSearchError(null);
    setSearching(true);
    setHasSearched(true);
    try {
      const res = await apiFetch<{ items: RetrievedChunk[] }>("/rag/retrieve", {
        method: "POST",
        body: JSON.stringify({
          query: query.trim(),
          subject_id: subjectId,
          top_k: 5,
          usable_only: true,
        }),
      });
      setResults(res.items);
    } catch (err) {
      setSearchError(err instanceof ApiError ? err.message : "Retrieval failed");
      setResults([]);
    } finally {
      setSearching(false);
    }
  }

  return (
    <AppShell allowedRoles={["ADMIN", "REVIEWER"]}>
      <div className="space-y-6">
        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <h1 className="flex items-center gap-2 text-2xl font-bold text-slate-900">
            <Sparkles className="h-5 w-5 text-emerald-700" />
            <span>
              {locale === "bn" ? "RAG ভেক্টর অনুসন্ধান ও AI প্রস্তুতি" : "RAG Retrieval & AI Provider Status"}
            </span>
          </h1>
          <p className="mt-1 text-sm text-slate-600">
            {locale === "bn"
              ? "Qdrant ভেক্টর ডাটাবেসে ইনডেক্সকৃত উৎস-চাঙ্ক থেকে বাংলা/ইংরেজি সিমান্টিক অনুসন্ধান পরীক্ষা করুন।"
              : "Inspect non-secret AI provider configuration and test semantic Bengali/English chunk retrieval against Qdrant."}
          </p>
        </div>

        {loadingInit && <LoadingState />}
        {!loadingInit && error && <ErrorState message={error} onRetry={() => void loadInit()} />}

        {!loadingInit && !error && aiStatus && (
          <>
            <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
              <h2 className="flex items-center gap-2 text-sm font-bold text-slate-900">
                <Cpu className="h-4 w-4 text-emerald-700" />
                <span>{locale === "bn" ? "প্রোভাইডার কনফিগারেশন অবস্থা" : "Provider Readiness"}</span>
              </h2>
              <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
                <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs">
                  <div className="text-slate-500">LLM Provider / Model</div>
                  <div className="mt-1 font-bold text-slate-900">
                    {aiStatus.llm_provider} • {aiStatus.generation_model}
                  </div>
                </div>
                <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs">
                  <div className="text-slate-500">Embedding Provider</div>
                  <div className="mt-1 font-bold text-slate-900">
                    {aiStatus.embedding_provider} ({aiStatus.embedding_model})
                  </div>
                </div>
                <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs">
                  <div className="text-slate-500">OPENAI_API_KEY</div>
                  <div
                    className={`mt-1 font-bold ${
                      aiStatus.openai_api_key_configured ? "text-emerald-800" : "text-amber-800"
                    }`}
                  >
                    {aiStatus.openai_api_key_configured ? "Configured" : "Missing in .env"}
                  </div>
                </div>
                <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs">
                  <div className="text-slate-500">BGE-M3 Local Adapter</div>
                  <div className="mt-1 font-bold text-slate-900">
                    {aiStatus.bge_m3_installed ? "Installed" : "Optional extra (.[bge])"}
                  </div>
                </div>
              </div>
            </div>

            <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
              <form onSubmit={handleSearch} className="grid grid-cols-1 gap-3 md:grid-cols-6">
                <select
                  required
                  value={subjectId}
                  onChange={(e) => setSubjectId(e.target.value)}
                  className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm md:col-span-2"
                >
                  {subjects.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name_bn} ({s.name_en})
                    </option>
                  ))}
                </select>
                <input
                  required
                  minLength={2}
                  placeholder={
                    locale === "bn"
                      ? "উদাহরণ: চর্যাপদের প্রাচীন কবি কে?"
                      : "Enter Bengali or English RAG query..."
                  }
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  className="rounded-lg border border-slate-300 px-3 py-2 text-sm md:col-span-3"
                />
                <button
                  type="submit"
                  disabled={searching || !subjectId}
                  className="inline-flex items-center justify-center gap-2 rounded-lg bg-emerald-800 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-900 disabled:opacity-60"
                >
                  {searching ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
                  <span>{locale === "bn" ? "খুঁজুন" : "Retrieve"}</span>
                </button>
              </form>

              {searchError && (
                <div className="mt-4 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
                  {searchError}
                </div>
              )}

              {!searching && hasSearched && !searchError && results.length === 0 && (
                <div className="mt-4">
                  <EmptyState
                    title={locale === "bn" ? "কোনো প্রাসঙ্গিক চাঙ্ক পাওয়া যায়নি" : "No matching chunks found"}
                    subtitle={
                      locale === "bn"
                        ? "প্রথমে একটি নথি আপলোড করে 'Index' বাটনে ক্লিক করুন।"
                        : "Ensure usable documents are indexed into Qdrant first."
                    }
                  />
                </div>
              )}

              {results.length > 0 && (
                <div className="mt-4 space-y-3">
                  {results.map((item) => (
                    <div
                      key={item.chunk_id}
                      className="rounded-lg border border-slate-200 bg-slate-50/70 p-4"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-slate-600">
                        <div className="font-semibold text-slate-900">
                          {item.document_title} •{" "}
                          {locale === "bn"
                            ? `পৃষ্ঠা ${formatNumber(item.page_number)}`
                            : `Page ${item.page_number}`}
                          {item.heading_path ? ` • ${item.heading_path}` : ""}
                        </div>
                        <span className="rounded-full bg-emerald-100 px-2.5 py-0.5 font-mono text-[11px] font-semibold text-emerald-900">
                          score {item.score.toFixed(4)}
                        </span>
                      </div>
                      <p className="mt-2 text-sm leading-relaxed text-slate-800">
                        {item.content_nfc}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </AppShell>
  );
}
