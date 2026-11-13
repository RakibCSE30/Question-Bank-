"use client";

import React from "react";
import { AlertTriangle, BookOpen, Loader2, ShieldAlert } from "lucide-react";
import { useI18n } from "@/i18n/I18nContext";
import type { UserRole } from "@/types";

export function LoadingState({ message }: { message?: string }) {
  const { t } = useI18n();
  return (
    <div
      className="flex min-h-[240px] flex-col items-center justify-center rounded-xl border border-slate-200 bg-white p-8 text-center shadow-sm"
      role="status"
      aria-live="polite"
    >
      <Loader2 className="h-8 w-8 animate-spin text-emerald-700" />
      <p className="mt-3 text-sm font-medium text-slate-600">{message ?? t("states.loading")}</p>
    </div>
  );
}

export function EmptyState({
  title,
  subtitle,
}: {
  title?: string;
  subtitle?: string;
}) {
  const { t } = useI18n();
  return (
    <div className="flex min-h-[240px] flex-col items-center justify-center rounded-xl border border-dashed border-slate-300 bg-white p-8 text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-emerald-50 text-emerald-700">
        <BookOpen className="h-6 w-6" />
      </div>
      <h3 className="mt-4 text-base font-semibold text-slate-900">
        {title ?? t("states.emptyTitle")}
      </h3>
      <p className="mt-2 max-w-md text-sm leading-relaxed text-slate-600">
        {subtitle ?? t("states.emptySubtitle")}
      </p>
    </div>
  );
}

export function ErrorState({
  message,
  onRetry,
}: {
  message?: string;
  onRetry?: () => void;
}) {
  const { t } = useI18n();
  return (
    <div
      className="flex min-h-[220px] flex-col items-center justify-center rounded-xl border border-rose-200 bg-rose-50/60 p-8 text-center"
      role="alert"
    >
      <AlertTriangle className="h-8 w-8 text-rose-600" />
      <h3 className="mt-3 text-base font-semibold text-rose-900">{t("states.errorTitle")}</h3>
      {message && <p className="mt-1 max-w-md text-sm text-rose-700">{message}</p>}
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-4 rounded-lg bg-rose-700 px-4 py-2 text-sm font-medium text-white transition hover:bg-rose-800"
        >
          {t("states.retry")}
        </button>
      )}
    </div>
  );
}

export function UnauthorizedState() {
  const { t } = useI18n();
  return (
    <div className="flex min-h-[260px] flex-col items-center justify-center rounded-xl border border-amber-200 bg-amber-50/70 p-8 text-center">
      <ShieldAlert className="h-9 w-9 text-amber-700" />
      <h3 className="mt-3 text-base font-semibold text-amber-950">{t("states.unauthorizedTitle")}</h3>
      <p className="mt-1 max-w-md text-sm text-amber-800">{t("states.unauthorizedSubtitle")}</p>
    </div>
  );
}

export function RoleBadge({ role }: { role: UserRole }) {
  const { t } = useI18n();
  const styles: Record<UserRole, string> = {
    ADMIN: "bg-slate-900 text-white",
    REVIEWER: "bg-amber-100 text-amber-900 border border-amber-300",
    STUDENT: "bg-emerald-100 text-emerald-900 border border-emerald-300",
  };
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${styles[role]}`}>
      {t(`roles.${role}`)}
    </span>
  );
}
