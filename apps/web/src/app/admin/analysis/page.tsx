"use client";

import React, { useEffect, useState } from "react";
import {
  AlertCircle,
  BookOpen,
  Calendar,
  CheckCircle2,
  Database,
  Feather,
  Layers,
  Sparkles,
  TrendingUp,
} from "lucide-react";
import { AppShell } from "@/components/layout/AppShell";
import { LoadingState } from "@/components/ui/StateViews";
import { apiFetch } from "@/lib/api";
import type { BanglaLiteratureAnalysisReport } from "@/types";

export default function LiteratureAnalysisPage() {
  const [report, setReport] = useState<BanglaLiteratureAnalysisReport | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSeeding, setIsSeeding] = useState(false);
  const [seedMessage, setSeedMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"periods" | "topics" | "authors" | "pastExam">("periods");

  const loadReport = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await apiFetch<BanglaLiteratureAnalysisReport>("/analysis/bangla-literature/report");
      setReport(data);
    } catch (err: any) {
      if (err.status === 404) {
        // Not seeded yet, prompt user
        setError("বাংলা সাহিত্য বিষয় এখনও ডাটাবেসে ইনিশিয়ালাইজ করা হয়নি। নিচের বোতাম চেপে বেসলাইন সীড করুন।");
      } else {
        setError(err.message || "বিশ্লেষণ রিপোর্ট লোড করতে সমস্যা হয়েছে।");
      }
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadReport();
  }, []);

  const handleSeedBaseline = async () => {
    setIsSeeding(true);
    setSeedMessage(null);
    setError(null);
    try {
      const res = await apiFetch<{ status: string; message: string }>("/analysis/bangla-literature/seed-baseline", {
        method: "POST",
      });
      setSeedMessage(res.message);
      await loadReport();
    } catch (err: any) {
      setError(err.message || "বেসলাইন সীড করতে ব্যর্থ হয়েছে।");
    } finally {
      setIsSeeding(false);
    }
  };

  return (
    <AppShell allowedRoles={["ADMIN", "REVIEWER"]}>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b pb-5">
          <div>
            <div className="flex items-center gap-2">
              <span className="rounded bg-emerald-100 px-2 py-0.5 text-xs font-semibold text-emerald-800">
                Phase 4: Content Analysis
              </span>
              <h1 className="text-2xl font-bold text-slate-900">
                বাংলা সাহিত্য সিলেবাস ও বিষয়বস্তু বিশ্লেষণ
              </h1>
            </div>
            <p className="mt-1 text-sm text-slate-600">
              চর্যাপদ থেকে সমকালীন সাহিত্য: যুগবিভাগ, সাহিত্যিক, টপিক অগ্রাধিকার ও বিগত বিসিএস ট্রেন্ডস
            </p>
          </div>

          <button
            onClick={handleSeedBaseline}
            disabled={isSeeding}
            className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2.5 text-sm font-medium text-white shadow-sm hover:bg-emerald-700 disabled:opacity-50 transition-colors"
          >
            <Database className="h-4 w-4" />
            {isSeeding ? "সংরক্ষণ করা হচ্ছে..." : "সিলেবাস ও অধ্যায় বেসলাইন সীড করুন"}
          </button>
        </div>

        {/* Notifications */}
        {seedMessage && (
          <div className="flex items-center gap-2 rounded-lg bg-emerald-50 border border-emerald-200 p-4 text-sm text-emerald-800">
            <CheckCircle2 className="h-5 w-5 text-emerald-600 shrink-0" />
            <span>{seedMessage}</span>
          </div>
        )}

        {error && (
          <div className="flex items-start gap-2 rounded-lg bg-amber-50 border border-amber-200 p-4 text-sm text-amber-800">
            <AlertCircle className="h-5 w-5 text-amber-600 shrink-0 mt-0.5" />
            <div className="flex-1">
              <p className="font-medium">{error}</p>
            </div>
          </div>
        )}

        {isLoading ? (
          <LoadingState />
        ) : report ? (
          <div className="space-y-6">
            {/* Navigation Tabs */}
            <div className="flex border-b border-slate-200">
              <button
                onClick={() => setActiveTab("periods")}
                className={`flex items-center gap-2 border-b-2 px-4 py-2.5 text-sm font-medium transition-colors ${
                  activeTab === "periods"
                    ? "border-emerald-600 text-emerald-700"
                    : "border-transparent text-slate-500 hover:text-slate-700"
                }`}
              >
                <Layers className="h-4 w-4" />
                যুগবিভাগ ও কাঠামো ({report.periods.length})
              </button>
              <button
                onClick={() => setActiveTab("topics")}
                className={`flex items-center gap-2 border-b-2 px-4 py-2.5 text-sm font-medium transition-colors ${
                  activeTab === "topics"
                    ? "border-emerald-600 text-emerald-700"
                    : "border-transparent text-slate-500 hover:text-slate-700"
                }`}
              >
                <Sparkles className="h-4 w-4" />
                টপিক অগ্রাধিকার ({report.topic_priorities.length})
              </button>
              <button
                onClick={() => setActiveTab("authors")}
                className={`flex items-center gap-2 border-b-2 px-4 py-2.5 text-sm font-medium transition-colors ${
                  activeTab === "authors"
                    ? "border-emerald-600 text-emerald-700"
                    : "border-transparent text-slate-500 hover:text-slate-700"
                }`}
              >
                <Feather className="h-4 w-4" />
                সাহিত্যিক ও গ্রন্থতালিকা ({report.authors.length})
              </button>
              <button
                onClick={() => setActiveTab("pastExam")}
                className={`flex items-center gap-2 border-b-2 px-4 py-2.5 text-sm font-medium transition-colors ${
                  activeTab === "pastExam"
                    ? "border-emerald-600 text-emerald-700"
                    : "border-transparent text-slate-500 hover:text-slate-700"
                }`}
              >
                <TrendingUp className="h-4 w-4" />
                বিগত বিসিএস প্রশ্ন বিশ্লেষণ
              </button>
            </div>

            {/* Tab 1: Periods */}
            {activeTab === "periods" && (
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
                {report.periods.map((period) => (
                  <div
                    key={period.period_code}
                    className="flex flex-col justify-between rounded-xl border border-slate-200 bg-white p-5 shadow-sm hover:border-emerald-300 transition-colors"
                  >
                    <div>
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-mono font-semibold uppercase text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded">
                          {period.period_code}
                        </span>
                        <span className="text-xs font-semibold text-slate-700 bg-slate-100 px-2 py-0.5 rounded">
                          সম্ভাব্য নম্বর: {period.bcs_mark_weight}
                        </span>
                      </div>
                      <h3 className="mt-3 text-lg font-bold text-slate-900">{period.period_name_bn}</h3>
                      <p className="mt-1 flex items-center gap-1.5 text-xs text-slate-500">
                        <Calendar className="h-3.5 w-3.5 text-slate-400" />
                        {period.span_years}
                      </p>
                      <p className="mt-3 text-xs text-slate-700 leading-relaxed bg-slate-50 p-2.5 rounded-lg border border-slate-100">
                        {period.key_characteristics}
                      </p>
                    </div>

                    <div className="mt-4 border-t border-slate-100 pt-3">
                      <p className="text-xs font-semibold text-slate-600 mb-2">মূল টপিকসমূহ:</p>
                      <ul className="space-y-1 text-xs text-slate-600 list-disc list-inside">
                        {period.core_topics.map((t, idx) => (
                          <li key={idx} className="line-clamp-1">
                            {t}
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Tab 2: Topics Priority */}
            {activeTab === "topics" && (
              <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
                <div className="p-4 border-b border-slate-100 flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-slate-900">
                    বিসিএস সিলেবাসের টপিক অগ্রাধিকার ও ওয়েট বণ্টন
                  </h3>
                  <span className="text-xs text-slate-500">
                    মোট টপিক: {report.topic_priorities.length}টি
                  </span>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm text-slate-700">
                    <thead className="bg-slate-50 text-xs font-semibold text-slate-600 border-b border-slate-200">
                      <tr>
                        <th className="px-4 py-3">টপিক</th>
                        <th className="px-4 py-3">অধ্যায়</th>
                        <th className="px-4 py-3">অগ্রাধিকার</th>
                        <th className="px-4 py-3">ওয়েট (%)</th>
                        <th className="px-4 py-3">বিগত প্রশ্ন সংখ্যা</th>
                        <th className="px-4 py-3">অগ্রাধিকার কারণ</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 text-xs">
                      {report.topic_priorities.map((item, idx) => (
                        <tr key={idx} className="hover:bg-slate-50/80">
                          <td className="px-4 py-3 font-medium text-slate-900">{item.topic_bn}</td>
                          <td className="px-4 py-3 text-slate-600">{item.chapter_name_bn}</td>
                          <td className="px-4 py-3">
                            <span
                              className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                                item.priority === "HIGH"
                                  ? "bg-rose-50 text-rose-700 border border-rose-200"
                                  : item.priority === "MEDIUM"
                                  ? "bg-amber-50 text-amber-700 border border-amber-200"
                                  : "bg-slate-100 text-slate-700"
                              }`}
                            >
                              {item.priority}
                            </span>
                          </td>
                          <td className="px-4 py-3 font-mono">{item.weight_percentage}%</td>
                          <td className="px-4 py-3 font-mono font-semibold text-emerald-700">
                            {item.previous_bcs_frequency}
                          </td>
                          <td className="px-4 py-3 text-slate-500 max-w-xs truncate">{item.priority_reason}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Tab 3: Authors & Works */}
            {activeTab === "authors" && (
              <div className="space-y-6">
                <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
                  {report.authors.map((auth, idx) => (
                    <div key={idx} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                      <div className="flex items-start justify-between">
                        <div>
                          <h4 className="text-base font-bold text-slate-900">{auth.name_bn}</h4>
                          {auth.pen_name_or_title && (
                            <span className="inline-block mt-1 text-xs text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded font-medium">
                              {auth.pen_name_or_title}
                            </span>
                          )}
                        </div>
                        <span className="text-xs text-slate-500 font-medium bg-slate-100 px-2 py-0.5 rounded">
                          {auth.era_or_period}
                        </span>
                      </div>
                      <p className="mt-3 text-xs text-slate-600 leading-relaxed">{auth.significance}</p>
                      <div className="mt-3 border-t border-slate-100 pt-3">
                        <p className="text-xs font-semibold text-slate-700 mb-1.5">প্রধান রচনাসমূহ:</p>
                        <div className="flex flex-wrap gap-1.5">
                          {auth.notable_works.map((w, wIdx) => (
                            <span
                              key={wIdx}
                              className="text-xs bg-slate-50 text-slate-700 border border-slate-200 px-2 py-0.5 rounded"
                            >
                              {w}
                            </span>
                          ))}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>

                <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                  <h3 className="text-base font-bold text-slate-900 mb-4 flex items-center gap-2">
                    <BookOpen className="h-5 w-5 text-emerald-600" />
                    প্রধান সাহিত্যকর্ম ও চরিত্র বিশ্লেষণ
                  </h3>
                  <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                    {report.literary_works.map((work, idx) => (
                      <div key={idx} className="rounded-lg border border-slate-100 bg-slate-50/50 p-4">
                        <div className="flex items-center justify-between">
                          <h4 className="font-bold text-slate-900">{work.title_bn}</h4>
                          <span className="text-xs font-medium text-emerald-700 bg-emerald-100/60 px-2 py-0.5 rounded">
                            {work.genre}
                          </span>
                        </div>
                        <p className="text-xs text-slate-600 mt-1">রচয়িতা: {work.author_name_bn}</p>
                        {work.publication_year_or_era && (
                          <p className="text-xs text-slate-500 mt-0.5">সাল/কাল: {work.publication_year_or_era}</p>
                        )}
                        {work.major_characters.length > 0 && (
                          <div className="mt-2 text-xs text-slate-600">
                            <span className="font-medium text-slate-700">প্রধান চরিত্র: </span>
                            {work.major_characters.join(", ")}
                          </div>
                        )}
                        {work.themes.length > 0 && (
                          <div className="mt-1 text-xs text-slate-600">
                            <span className="font-medium text-slate-700">উপজীব্য: </span>
                            {work.themes.join(", ")}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* Tab 4: Past Exam Analysis */}
            {activeTab === "pastExam" && (
              <div className="space-y-6">
                <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
                  <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm text-center">
                    <p className="text-xs font-semibold text-slate-500 uppercase">মোট বিগত প্রশ্ন</p>
                    <p className="mt-1 text-2xl font-bold text-slate-900">
                      {report.previous_trends.total_previous_questions}
                    </p>
                  </div>
                  <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm text-center">
                    <p className="text-xs font-semibold text-slate-500 uppercase">তথ্যভিত্তিক (Factual)</p>
                    <p className="mt-1 text-2xl font-bold text-blue-600">
                      {report.previous_trends.factual_percentage}%
                    </p>
                  </div>
                  <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm text-center">
                    <p className="text-xs font-semibold text-slate-500 uppercase">রচয়িতা-গ্রন্থ</p>
                    <p className="mt-1 text-2xl font-bold text-emerald-600">
                      {report.previous_trends.author_work_percentage}%
                    </p>
                  </div>
                  <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm text-center">
                    <p className="text-xs font-semibold text-slate-500 uppercase">ধারণাগত ও উক্তি</p>
                    <p className="mt-1 text-2xl font-bold text-purple-600">
                      {report.previous_trends.conceptual_percentage}%
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
                  <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                    <h4 className="text-sm font-bold text-slate-900 mb-3">
                      বিগত বিসিএসে ঘনঘন পরীক্ষিত টপিকসমূহ
                    </h4>
                    <ul className="space-y-2 text-xs text-slate-700">
                      {report.previous_trends.frequently_tested_topics.map((t, idx) => (
                        <li key={idx} className="flex items-center gap-2">
                          <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0" />
                          <span>{t}</span>
                        </li>
                      ))}
                    </ul>
                  </div>

                  <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                    <h4 className="text-sm font-bold text-slate-900 mb-3">
                      সিলেবাসের কম মূল্যায়িত / আন্ডাররিপ্রেজেন্টেড ক্ষেত্র
                    </h4>
                    <ul className="space-y-2 text-xs text-slate-700">
                      {report.previous_trends.underrepresented_topics.map((t, idx) => (
                        <li key={idx} className="flex items-center gap-2">
                          <AlertCircle className="h-4 w-4 text-amber-500 shrink-0" />
                          <span>{t}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>

                {/* Important Disclaimer */}
                <div className="rounded-xl bg-amber-50/70 border border-amber-200 p-4 text-xs text-amber-900 flex items-start gap-3">
                  <AlertCircle className="h-5 w-5 text-amber-600 shrink-0 mt-0.5" />
                  <div>
                    <span className="font-bold">নীতিমালা ও শিক্ষাগত সততা: </span>
                    {report.previous_trends.disclaimer} সিলেবাসের সমস্ত বিষয় সমভাবে গুরুত্ব দিয়ে
                    অনুশীলন করার জন্য এআই প্রতিটি সেটকে সুষমভাবে তৈরি করে।
                  </div>
                </div>
              </div>
            )}
          </div>
        ) : null}
      </div>
    </AppShell>
  );
}
