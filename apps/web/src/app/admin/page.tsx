"use client";

import React, { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Users } from "lucide-react";
import { AppShell } from "@/components/layout/AppShell";
import { ErrorState, LoadingState } from "@/components/ui/StateViews";
import { useI18n } from "@/i18n/I18nContext";
import { apiFetch, ApiError } from "@/lib/api";
import type { DashboardSummaryResponse } from "@/types";

export default function AdminDashboardPage() {
  const { t, formatNumber } = useI18n();
  const [data, setData] = useState<DashboardSummaryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiFetch<DashboardSummaryResponse>("/dashboard/admin");
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
    <AppShell allowedRoles={["ADMIN"]}>
      <div className="space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">{t("admin.heading")}</h1>
            <p className="mt-1 text-sm text-slate-600">{t("admin.description")}</p>
          </div>
          <Link
            href="/admin/users"
            className="inline-flex items-center gap-2 rounded-lg bg-emerald-800 px-4 py-2 text-sm font-semibold text-white transition hover:bg-emerald-900"
          >
            <Users className="h-4 w-4" />
            <span>{t("nav.userManagement")}</span>
          </Link>
        </div>

        {loading && <LoadingState />}
        {!loading && error && <ErrorState message={error} onRetry={() => void load()} />}

        {!loading && !error && data && (
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
        )}
      </div>
    </AppShell>
  );
}
