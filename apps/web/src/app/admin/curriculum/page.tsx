"use client";

import React, { useCallback, useEffect, useState } from "react";
import { BookMarked, Loader2, Plus, Sparkles, Trash2 } from "lucide-react";
import { AppShell } from "@/components/layout/AppShell";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/StateViews";
import { useI18n } from "@/i18n/I18nContext";
import { apiFetch, ApiError } from "@/lib/api";
import type { Chapter, Subject } from "@/types";

export default function AdminCurriculumPage() {
  const { locale, formatNumber } = useI18n();
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [selectedSubjectId, setSelectedSubjectId] = useState<string | null>(null);
  const [chapters, setChapters] = useState<Chapter[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Subject form
  const [code, setCode] = useState("");
  const [nameBn, setNameBn] = useState("");
  const [nameEn, setNameEn] = useState("");
  const [marks, setMarks] = useState(20);
  const [savingSubject, setSavingSubject] = useState(false);

  // Chapter form
  const [orderIndex, setOrderIndex] = useState(1);
  const [chapBn, setChapBn] = useState("");
  const [chapEn, setChapEn] = useState("");
  const [savingChapter, setSavingChapter] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const loadSubjects = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const list = await apiFetch<Subject[]>("/subjects");
      setSubjects(list);
      if (list.length > 0 && !selectedSubjectId) {
        setSelectedSubjectId(list[0].id);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load subjects");
    } finally {
      setLoading(false);
    }
  }, [selectedSubjectId]);

  const loadChapters = useCallback(async (subjectId: string) => {
    try {
      const list = await apiFetch<Chapter[]>(`/subjects/${subjectId}/chapters`);
      setChapters(list);
      setOrderIndex(list.length + 1);
    } catch {
      setChapters([]);
    }
  }, []);

  useEffect(() => {
    void loadSubjects();
  }, [loadSubjects]);

  useEffect(() => {
    if (selectedSubjectId) {
      void loadChapters(selectedSubjectId);
    } else {
      setChapters([]);
    }
  }, [selectedSubjectId, loadChapters]);

  async function handleSeedPilot() {
    setActionError(null);
    setSavingSubject(true);
    try {
      const seeded = await apiFetch<Subject>("/admin/subjects/seed-pilot", { method: "POST" });
      setSelectedSubjectId(seeded.id);
      await loadSubjects();
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Failed to seed pilot subject");
    } finally {
      setSavingSubject(false);
    }
  }

  async function handleCreateSubject(e: React.FormEvent) {
    e.preventDefault();
    setActionError(null);
    setSavingSubject(true);
    try {
      const created = await apiFetch<Subject>("/admin/subjects", {
        method: "POST",
        body: JSON.stringify({
          code,
          name_bn: nameBn,
          name_en: nameEn,
          bcs_total_marks: Number(marks),
        }),
      });
      setCode("");
      setNameBn("");
      setNameEn("");
      setSelectedSubjectId(created.id);
      await loadSubjects();
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Failed to create subject");
    } finally {
      setSavingSubject(false);
    }
  }

  async function handleCreateChapter(e: React.FormEvent) {
    e.preventDefault();
    if (!selectedSubjectId) return;
    setActionError(null);
    setSavingChapter(true);
    try {
      await apiFetch<Chapter>(`/admin/subjects/${selectedSubjectId}/chapters`, {
        method: "POST",
        body: JSON.stringify({
          order_index: Number(orderIndex),
          title_bn: chapBn,
          title_en: chapEn || null,
        }),
      });
      setChapBn("");
      setChapEn("");
      await loadChapters(selectedSubjectId);
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Failed to create chapter");
    } finally {
      setSavingChapter(false);
    }
  }

  async function handleDeleteChapter(chapterId: string) {
    if (!selectedSubjectId) return;
    setActionError(null);
    try {
      await apiFetch<void>(`/admin/chapters/${chapterId}`, { method: "DELETE" });
      await loadChapters(selectedSubjectId);
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Failed to delete chapter");
    }
  }

  return (
    <AppShell allowedRoles={["ADMIN"]}>
      <div className="space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">
              {locale === "bn" ? "বিষয় ও অধ্যায় ব্যবস্থাপনা" : "Subjects & Chapters"}
            </h1>
            <p className="mt-1 text-sm text-slate-600">
              {locale === "bn"
                ? "বিসিএস সিলেবাস অনুযায়ী বিষয় ও অধ্যায় তৈরি করুন। কোনো ভুয়া কনটেন্ট স্বয়ংক্রিয়ভাবে যোগ হয় না।"
                : "Manage BCS subjects and chapters. No placeholder content is seeded."}
            </p>
          </div>
          <button
            type="button"
            onClick={() => void handleSeedPilot()}
            disabled={savingSubject}
            className="inline-flex items-center gap-2 rounded-lg bg-emerald-800 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-900 disabled:opacity-60"
          >
            <Sparkles className="h-4 w-4" />
            <span>
              {locale === "bn"
                ? "পাইলট বিষয় যোগ করুন (বাংলা সাহিত্য)"
                : "Seed Pilot Subject (Bangla Literature)"}
            </span>
          </button>
        </div>

        {actionError && (
          <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">
            {actionError}
          </div>
        )}

        {loading && <LoadingState />}
        {!loading && error && <ErrorState message={error} onRetry={() => void loadSubjects()} />}

        {!loading && !error && (
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            {/* Subjects column */}
            <div className="space-y-4 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
              <h2 className="flex items-center gap-2 text-base font-bold text-slate-900">
                <BookMarked className="h-4 w-4 text-emerald-700" />
                <span>{locale === "bn" ? "বিষয়সমূহ" : "Subjects"}</span>
              </h2>

              <form onSubmit={handleCreateSubject} className="grid grid-cols-2 gap-2">
                <input
                  required
                  placeholder="Code (e.g. BANGLA_LIT)"
                  value={code}
                  onChange={(e) => setCode(e.target.value)}
                  className="rounded-lg border border-slate-300 px-3 py-2 text-xs"
                />
                <input
                  type="number"
                  min={0}
                  max={200}
                  value={marks}
                  onChange={(e) => setMarks(Number(e.target.value))}
                  placeholder="BCS Marks"
                  className="rounded-lg border border-slate-300 px-3 py-2 text-xs"
                />
                <input
                  required
                  placeholder={locale === "bn" ? "বাংলা নাম" : "Bangla Name"}
                  value={nameBn}
                  onChange={(e) => setNameBn(e.target.value)}
                  className="rounded-lg border border-slate-300 px-3 py-2 text-xs"
                />
                <input
                  required
                  placeholder="English Name"
                  value={nameEn}
                  onChange={(e) => setNameEn(e.target.value)}
                  className="rounded-lg border border-slate-300 px-3 py-2 text-xs"
                />
                <button
                  type="submit"
                  disabled={savingSubject}
                  className="col-span-2 inline-flex items-center justify-center gap-1.5 rounded-lg bg-slate-900 px-3 py-2 text-xs font-semibold text-white hover:bg-slate-800"
                >
                  {savingSubject ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Plus className="h-3.5 w-3.5" />}
                  <span>{locale === "bn" ? "বিষয় যোগ করুন" : "Add Subject"}</span>
                </button>
              </form>

              {subjects.length === 0 ? (
                <EmptyState
                  title={locale === "bn" ? "কোনো বিষয় নেই" : "No subjects yet"}
                  subtitle={
                    locale === "bn"
                      ? "উপরের বাটনে ক্লিক করে 'বাংলা সাহিত্য' পাইলট বিষয় যোগ করুন।"
                      : "Click the button above to seed Bangla Literature or create a subject."
                  }
                />
              ) : (
                <div className="divide-y divide-slate-100 rounded-lg border border-slate-200">
                  {subjects.map((subj) => (
                    <button
                      key={subj.id}
                      type="button"
                      onClick={() => setSelectedSubjectId(subj.id)}
                      className={`flex w-full items-center justify-between px-4 py-3 text-left transition ${
                        selectedSubjectId === subj.id ? "bg-emerald-50" : "hover:bg-slate-50"
                      }`}
                    >
                      <div>
                        <div className="text-sm font-semibold text-slate-900">{subj.name_bn}</div>
                        <div className="text-xs text-slate-500">
                          {subj.name_en} ({subj.code})
                        </div>
                      </div>
                      <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-semibold text-slate-700">
                        {formatNumber(subj.bcs_total_marks)} {locale === "bn" ? "নম্বর" : "marks"}
                      </span>
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Chapters column */}
            <div className="space-y-4 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
              <h2 className="text-base font-bold text-slate-900">
                {locale === "bn" ? "অধ্যায়সমূহ" : "Chapters"}
              </h2>

              {selectedSubjectId ? (
                <>
                  <form onSubmit={handleCreateChapter} className="grid grid-cols-4 gap-2">
                    <input
                      type="number"
                      min={1}
                      required
                      value={orderIndex}
                      onChange={(e) => setOrderIndex(Number(e.target.value))}
                      className="rounded-lg border border-slate-300 px-3 py-2 text-xs"
                    />
                    <input
                      required
                      placeholder={locale === "bn" ? "অধ্যায়ের নাম (বাংলা)" : "Chapter Title (BN)"}
                      value={chapBn}
                      onChange={(e) => setChapBn(e.target.value)}
                      className="col-span-3 rounded-lg border border-slate-300 px-3 py-2 text-xs"
                    />
                    <input
                      placeholder="Chapter Title (EN, optional)"
                      value={chapEn}
                      onChange={(e) => setChapEn(e.target.value)}
                      className="col-span-3 rounded-lg border border-slate-300 px-3 py-2 text-xs"
                    />
                    <button
                      type="submit"
                      disabled={savingChapter}
                      className="inline-flex items-center justify-center gap-1 rounded-lg bg-emerald-800 px-3 py-2 text-xs font-semibold text-white hover:bg-emerald-900"
                    >
                      <Plus className="h-3.5 w-3.5" />
                      <span>{locale === "bn" ? "যোগ" : "Add"}</span>
                    </button>
                  </form>

                  {chapters.length === 0 ? (
                    <EmptyState
                      title={locale === "bn" ? "এই বিষয়ে কোনো অধ্যায় নেই" : "No chapters yet"}
                      subtitle={
                        locale === "bn"
                          ? "বই বা সিলেবাস অনুযায়ী অধ্যায় যোগ করুন (ঐচ্ছিক)।"
                          : "Add chapters for this subject if needed."
                      }
                    />
                  ) : (
                    <div className="divide-y divide-slate-100 rounded-lg border border-slate-200">
                      {chapters.map((c) => (
                        <div key={c.id} className="flex items-center justify-between px-4 py-2.5 text-sm">
                          <div>
                            <span className="mr-2 font-semibold text-emerald-800">
                              {formatNumber(c.order_index)}.
                            </span>
                            <span className="font-medium text-slate-900">{c.title_bn}</span>
                            {c.title_en && (
                              <span className="ml-2 text-xs text-slate-500">({c.title_en})</span>
                            )}
                          </div>
                          <button
                            type="button"
                            onClick={() => void handleDeleteChapter(c.id)}
                            className="rounded p-1 text-slate-400 hover:bg-rose-50 hover:text-rose-700"
                            aria-label="Delete chapter"
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </>
              ) : (
                <EmptyState
                  title={locale === "bn" ? "প্রথমে একটি বিষয় নির্বাচন করুন" : "Select a subject first"}
                  subtitle=""
                />
              )}
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}
