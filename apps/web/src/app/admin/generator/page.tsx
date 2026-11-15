"use client";

import React, { useEffect, useState } from "react";
import {
  AlertCircle,
  BookCheck,
  Check,
  CheckCircle2,
  Clock,
  ExternalLink,
  Eye,
  FileQuestion,
  HelpCircle,
  Layers,
  Send,
  Sparkles,
  Tag,
} from "lucide-react";
import { AppShell } from "@/components/layout/AppShell";
import { LoadingState } from "@/components/ui/StateViews";
import { apiFetch } from "@/lib/api";
import type { PracticeSetDetail, PracticeSetItem } from "@/types";

export default function MCQGeneratorPage() {
  const [sets, setSets] = useState<PracticeSetItem[]>([]);
  const [selectedSetId, setSelectedSetId] = useState<string | null>(null);
  const [activeSetDetail, setActiveSetDetail] = useState<PracticeSetDetail | null>(null);
  const [isLoadingSets, setIsLoadingSets] = useState(true);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isPublishing, setIsPublishing] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadPracticeSets = async () => {
    setIsLoadingSets(true);
    setError(null);
    try {
      const data = await apiFetch<PracticeSetItem[]>("/questions/practice-sets");
      setSets(data);
      if (data.length > 0 && !selectedSetId) {
        setSelectedSetId(data[0].id);
      }
    } catch (err: any) {
      setError(err.message || "প্র্যাকটিস সেটের তালিকা লোড করতে সমস্যা হয়েছে।");
    } finally {
      setIsLoadingSets(false);
    }
  };

  const loadSetDetail = async (setId: string) => {
    setIsLoadingDetail(true);
    try {
      const detail = await apiFetch<PracticeSetDetail>(`/questions/practice-sets/${setId}`);
      setActiveSetDetail(detail);
    } catch (err: any) {
      setError(err.message || "সেটের বিস্তারিত লোড করতে সমস্যা হয়েছে।");
    } finally {
      setIsLoadingDetail(false);
    }
  };

  useEffect(() => {
    loadPracticeSets();
  }, []);

  useEffect(() => {
    if (selectedSetId) {
      loadSetDetail(selectedSetId);
    }
  }, [selectedSetId]);

  const handleGeneratePilot = async () => {
    setIsGenerating(true);
    setMessage(null);
    setError(null);
    try {
      const created = await apiFetch<PracticeSetItem[]>("/questions/generate-pilot-sets", {
        method: "POST",
        body: JSON.stringify({
          subject_code: "BANGLA_LIT",
          num_sets: 5,
          questions_per_set: 15,
        }),
      });
      setSets(created);
      if (created.length > 0) {
        setSelectedSetId(created[0].id);
      }
      setMessage("বাংলা সাহিত্যের ৫টি প্র্যাকটিস সেট (৭৫টি প্রমিত MCQ) সফলভাবে ডাটাবেসে জেনারেট হয়েছে!");
    } catch (err: any) {
      setError(err.message || "প্রশ্ন সেট জেনারেট করতে সমস্যা হয়েছে।");
    } finally {
      setIsGenerating(false);
    }
  };

  const handleTogglePublish = async () => {
    if (!activeSetDetail) return;
    setIsPublishing(true);
    try {
      const nextStatus = !activeSetDetail.is_published;
      const updated = await apiFetch<PracticeSetItem>(
        `/questions/practice-sets/${activeSetDetail.id}/publish`,
        {
          method: "PATCH",
          body: JSON.stringify({
            is_published: nextStatus,
            negative_mark_per_wrong: 0.5,
            duration_minutes: 15,
          }),
        }
      );
      setActiveSetDetail((prev) => (prev ? { ...prev, is_published: updated.is_published } : null));
      setSets((prev) =>
        prev.map((s) => (s.id === updated.id ? { ...s, is_published: updated.is_published } : s))
      );
      setMessage(
        nextStatus
          ? "প্র্যাকটিস সেটটি সফলভাবে প্রকাশিত হয়েছে। শিক্ষার্থীরা এখন মক টেস্ট দিতে পারবে।"
          : "প্র্যাকটিস সেটটি অপ্রকাশিত করা হয়েছে।"
      );
    } catch (err: any) {
      setError(err.message || "স্ট্যাটাস পরিবর্তন করতে ব্যর্থ হয়েছে।");
    } finally {
      setIsPublishing(false);
    }
  };

  const handleQuickApprove = async (questionId: string) => {
    try {
      await apiFetch(`/questions/${questionId}/review`, {
        method: "PATCH",
        body: JSON.stringify({ status: "APPROVED" }),
      });
      if (activeSetDetail) {
        setActiveSetDetail({
          ...activeSetDetail,
          items: activeSetDetail.items.map((it) =>
            it.question.id === questionId
              ? { ...it, question: { ...it.question, status: "APPROVED" } }
              : it
          ),
        });
      }
    } catch (err: any) {
      setError(err.message || "প্রশ্ন অনুমোদন করতে ব্যর্থ হয়েছে।");
    }
  };

  return (
    <AppShell allowedRoles={["ADMIN", "REVIEWER"]}>
      <div className="space-y-6">
        {/* Page Header */}
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b pb-5">
          <div>
            <div className="flex items-center gap-2">
              <span className="rounded bg-indigo-100 px-2 py-0.5 text-xs font-semibold text-indigo-800">
                Phase 5: Question Generation
              </span>
              <h1 className="text-2xl font-bold text-slate-900">
                পাইলট প্রশ্ন জেনারেটর ও প্রশ্ন ব্যাংক
              </h1>
            </div>
            <p className="mt-1 text-sm text-slate-600">
              বাংলা সাহিত্য পাইলট: ৫টি বৈচিত্র্যপূর্ণ সেট x ১৫টি করে প্রশ্ন = মোট ৭৫টি প্রমিত বিসিএস MCQ
            </p>
          </div>

          <button
            onClick={handleGeneratePilot}
            disabled={isGenerating}
            className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-medium text-white shadow-sm hover:bg-indigo-700 disabled:opacity-50 transition-colors"
          >
            <Sparkles className="h-4 w-4" />
            {isGenerating ? "তৈরি হচ্ছে (৭৫টি প্রশ্ন)..." : "৫টি সেট তৈরি করুন (Generate 5 Sets)"}
          </button>
        </div>

        {/* Notifications */}
        {message && (
          <div className="flex items-center gap-2 rounded-lg bg-emerald-50 border border-emerald-200 p-4 text-sm text-emerald-800">
            <CheckCircle2 className="h-5 w-5 text-emerald-600 shrink-0" />
            <span>{message}</span>
          </div>
        )}

        {error && (
          <div className="flex items-start gap-2 rounded-lg bg-rose-50 border border-rose-200 p-4 text-sm text-rose-800">
            <AlertCircle className="h-5 w-5 text-rose-600 shrink-0 mt-0.5" />
            <p className="font-medium">{error}</p>
          </div>
        )}

        {/* Sets Selection Tabs */}
        {isLoadingSets ? (
          <LoadingState />
        ) : sets.length === 0 ? (
          <div className="rounded-xl border border-dashed border-slate-300 p-12 text-center bg-slate-50">
            <FileQuestion className="mx-auto h-12 w-12 text-slate-400" />
            <h3 className="mt-3 text-base font-bold text-slate-900">এখনও কোনো প্রশ্ন সেট তৈরি করা হয়নি</h3>
            <p className="mt-1 text-sm text-slate-500 max-w-md mx-auto">
              উপরে থাকা "৫টি সেট তৈরি করুন" বোতামটি চেপে বাংলা সাহিত্যের ৫টি অধ্যায়ভিত্তিক প্র্যাকটিস সেট (৭৫টি MCQ)
              ডাটাবেসে তৈরি করুন।
            </p>
            <button
              onClick={handleGeneratePilot}
              disabled={isGenerating}
              className="mt-5 inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow hover:bg-indigo-700"
            >
              <Sparkles className="h-4 w-4" />
              এখনই পাইলট প্রশ্ন সেট তৈরি করুন
            </button>
          </div>
        ) : (
          <div className="space-y-6">
            {/* Set Tabs */}
            <div className="flex flex-wrap gap-2 border-b border-slate-200 pb-3">
              {sets.map((s) => {
                const isSelected = selectedSetId === s.id;
                return (
                  <button
                    key={s.id}
                    onClick={() => setSelectedSetId(s.id)}
                    className={`flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold transition-all ${
                      isSelected
                        ? "bg-indigo-600 text-white shadow-sm"
                        : "bg-white border border-slate-200 text-slate-700 hover:bg-slate-50"
                    }`}
                  >
                    <span>সেট {s.set_number}</span>
                    <span
                      className={`text-xs px-1.5 py-0.2 rounded font-mono ${
                        isSelected ? "bg-indigo-700 text-white" : "bg-slate-100 text-slate-600"
                      }`}
                    >
                      {s.question_count || 15}টি MCQ
                    </span>
                    {s.is_published && (
                      <span className="h-2 w-2 rounded-full bg-emerald-400 inline-block" />
                    )}
                  </button>
                );
              })}
            </div>

            {/* Active Set Content */}
            {isLoadingDetail ? (
              <LoadingState />
            ) : activeSetDetail ? (
              <div className="space-y-6">
                {/* Active Set Meta Card */}
                <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                  <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="rounded bg-slate-100 px-2.5 py-0.5 text-xs font-bold text-slate-800">
                          সেট নং {activeSetDetail.set_number}
                        </span>
                        <span
                          className={`rounded px-2.5 py-0.5 text-xs font-semibold ${
                            activeSetDetail.is_published
                              ? "bg-emerald-100 text-emerald-800"
                              : "bg-amber-100 text-amber-800"
                          }`}
                        >
                          {activeSetDetail.is_published ? "প্রকাশিত (Live for Students)" : "অপ্রকাশিত (Draft)"}
                        </span>
                      </div>
                      <h2 className="mt-2 text-xl font-bold text-slate-900">
                        {activeSetDetail.title_bn}
                      </h2>
                    </div>

                    <div className="flex flex-wrap items-center gap-3">
                      <div className="flex items-center gap-1.5 text-xs text-slate-600 bg-slate-50 px-3 py-1.5 rounded-lg border border-slate-200">
                        <Clock className="h-4 w-4 text-slate-400" />
                        <span>সময়: {activeSetDetail.duration_minutes} মিনিট</span>
                      </div>
                      <div className="flex items-center gap-1.5 text-xs text-slate-600 bg-slate-50 px-3 py-1.5 rounded-lg border border-slate-200">
                        <span>নেগেটিভ মার্কিং: -{activeSetDetail.negative_mark_per_wrong}</span>
                      </div>
                      <button
                        onClick={handleTogglePublish}
                        disabled={isPublishing}
                        className={`inline-flex items-center gap-1.5 rounded-lg px-3.5 py-1.5 text-xs font-medium text-white shadow-sm transition-colors ${
                          activeSetDetail.is_published
                            ? "bg-amber-600 hover:bg-amber-700"
                            : "bg-emerald-600 hover:bg-emerald-700"
                        }`}
                      >
                        <Send className="h-3.5 w-3.5" />
                        {activeSetDetail.is_published ? "অপ্রকাশিত করুন" : "শিক্ষার্থীদের জন্য প্রকাশ করুন"}
                      </button>
                    </div>
                  </div>
                </div>

                {/* 15 Questions List */}
                <div className="space-y-4">
                  <div className="flex items-center justify-between px-1">
                    <h3 className="text-sm font-bold text-slate-900">
                      প্রশ্নের তালিকা ({activeSetDetail.items.length}টি MCQ)
                    </h3>
                    <span className="text-xs text-slate-500">
                      চারটি অপশন (ক, খ, গ, ঘ) • সোর্স-গ্রাউন্ডেড ব্যাখ্যা সহ
                    </span>
                  </div>

                  {activeSetDetail.items.map((item, idx) => {
                    const q = item.question;
                    const correctLabel = q.answer_key?.correct_label;

                    return (
                      <div
                        key={q.id}
                        className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm transition-all hover:border-slate-300"
                      >
                        {/* Question Top Tags */}
                        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-3">
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="flex h-6 w-6 items-center justify-center rounded-full bg-slate-100 text-xs font-bold text-slate-700">
                              {item.position}
                            </span>
                            <span className="rounded bg-indigo-50 px-2 py-0.5 text-xs font-semibold text-indigo-700">
                              {q.question_style}
                            </span>
                            <span
                              className={`rounded px-2 py-0.5 text-xs font-medium ${
                                q.difficulty === "HARD"
                                  ? "bg-rose-50 text-rose-700 border border-rose-200"
                                  : q.difficulty === "MEDIUM"
                                  ? "bg-amber-50 text-amber-700 border border-amber-200"
                                  : "bg-emerald-50 text-emerald-700 border border-emerald-200"
                              }`}
                            >
                              {q.difficulty}
                            </span>
                            <span className="rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-600">
                              {q.grounding_type}
                            </span>
                          </div>

                          <div className="flex items-center gap-2">
                            <span
                              className={`text-xs font-medium px-2 py-0.5 rounded ${
                                q.status === "APPROVED"
                                  ? "bg-emerald-100 text-emerald-800"
                                  : "bg-slate-100 text-slate-600"
                              }`}
                            >
                              {q.status}
                            </span>
                            {q.status !== "APPROVED" && (
                              <button
                                onClick={() => handleQuickApprove(q.id)}
                                className="inline-flex items-center gap-1 rounded bg-emerald-50 px-2 py-1 text-xs font-semibold text-emerald-700 border border-emerald-200 hover:bg-emerald-100"
                              >
                                <Check className="h-3 w-3" />
                                অনুমোদন
                              </button>
                            )}
                          </div>
                        </div>

                        {/* Question Text */}
                        <p className="mt-4 text-base font-semibold text-slate-900 leading-relaxed">
                          {q.question_text_bn}
                        </p>

                        {/* 4 Options (ক, খ, গ, ঘ) */}
                        <div className="mt-4 grid grid-cols-1 gap-2.5 sm:grid-cols-2">
                          {q.options.map((opt) => {
                            const isCorrect = opt.option_label === correctLabel;
                            return (
                              <div
                                key={opt.id}
                                className={`flex items-start gap-3 rounded-lg border p-3 text-sm transition-colors ${
                                  isCorrect
                                    ? "border-emerald-500 bg-emerald-50/70 text-emerald-950 font-medium ring-1 ring-emerald-400"
                                    : "border-slate-200 bg-white text-slate-700"
                                }`}
                              >
                                <span
                                  className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-bold ${
                                    isCorrect
                                      ? "bg-emerald-600 text-white"
                                      : "bg-slate-100 text-slate-700"
                                  }`}
                                >
                                  {opt.option_label}
                                </span>
                                <span className="flex-1 mt-0.5">{opt.option_text_bn}</span>
                                {isCorrect && (
                                  <Check className="h-4 w-4 text-emerald-600 shrink-0 mt-0.5" />
                                )}
                              </div>
                            );
                          })}
                        </div>

                        {/* Explanation & Source Citation Card */}
                        <div className="mt-4 rounded-lg bg-slate-50 border border-slate-200/80 p-3.5 text-xs text-slate-700 space-y-2">
                          <div className="flex items-start gap-2">
                            <span className="font-bold text-slate-900 shrink-0">ব্যাখ্যা:</span>
                            <span className="leading-relaxed">{q.explanation_bn}</span>
                          </div>
                          {q.source_citations_json && (
                            <div className="flex items-center gap-1.5 text-slate-500 pt-1 border-t border-slate-200/60">
                              <Tag className="h-3 w-3 text-slate-400" />
                              <span className="font-medium text-slate-600">রেফারেন্স সোর্স:</span>
                              <span>
                                {Array.isArray(q.source_citations_json)
                                  ? q.source_citations_json[0]?.source_title || "বিপিএসসি সিলেবাস"
                                  : "বিপিএসসি সিলেবাস"}
                              </span>
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            ) : null}
          </div>
        )}
      </div>
    </AppShell>
  );
}
