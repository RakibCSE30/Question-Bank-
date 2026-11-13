"use client";

import React, { useCallback, useEffect, useState } from "react";
import { ShieldCheck } from "lucide-react";
import { AppShell } from "@/components/layout/AppShell";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/StateViews";
import { useI18n } from "@/i18n/I18nContext";
import { apiFetch, ApiError } from "@/lib/api";
import type { DashboardSummaryResponse } from "@/types";

export default function StudentDashboardPage() {
  const { t, formatNumber } = useI18n();
  const [data, setData] = useState<DashboardSummaryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiFetch<DashboardSummaryResponse>("/dashboard/student");
      setData(res);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("states.errorTitle"));
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <AppShell allowedRoles={["STUDENT", "REVIEWER", "ADMIN"]}>
      <div className="space-y-6">
        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <h1 className="text-2xl font-bold text-slate-900">{t("student.heading")}</h1>
          <p className="mt-1 text-sm text-slate-600">{t("student.description")}</p>
          <div className="mt-4 flex items-start gap-2.5 rounded-lg border border-emerald-200 bg-emerald-50/80 p-3 text-xs leading-relaxed text-emerald-950">
            <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-emerald-700" />
            <span>{t("student.integrityNote")}</span>
          </div>
        </div>

        {loading && <LoadingState />}
        {!loading && error && <ErrorState message={error} onRetry={() => void load()} />}

        {!loading && !error && data && (
          <>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {data.metrics.map((metric) => (
                <div
                  key={metric.key}
                  className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm"
                >
                  <div className="text-xs font-medium text-slate-500">
                    {t(`metrics.${metric.key}`)}
                  </div>
                  <div className="mt-2 text-2xl font-bold tabular-nums text-slate-900">
                    {formatNumber(metric.value)}
                  </div>
                </div>
              ))}
            </div>

            <EmptyState />
          </>
        )}
      </div>
    </AppShell>
  );
}
