"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Languages, Loader2 } from "lucide-react";
import { useI18n } from "@/i18n/I18nContext";
import { useAuth } from "@/lib/auth";
import { ApiError } from "@/lib/api";

export default function LoginPage() {
  const { login } = useAuth();
  const { locale, toggleLocale, t } = useI18n();
  const router = useRouter();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const user = await login(email, password);
      if (user.role === "ADMIN") router.push("/admin");
      else if (user.role === "REVIEWER") router.push("/reviewer");
      else router.push("/");
    } catch (err) {
      if (err instanceof ApiError) setError(err.message);
      else setError(t("auth.authError"));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-paper px-4 py-12">
      <div className="mb-6 flex w-full max-w-md items-center justify-between">
        <div className="flex items-center gap-2.5">
          <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-emerald-800 text-sm font-bold text-white">
            স
          </span>
          <span className="text-lg font-bold text-slate-900">{t("app.name")}</span>
        </div>
        <button
          type="button"
          onClick={toggleLocale}
          className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50"
        >
          <Languages className="h-4 w-4 text-emerald-700" />
          <span>{locale === "bn" ? "বাংলা | EN" : "EN | বাংলা"}</span>
        </button>
      </div>

      <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <h1 className="text-xl font-bold text-slate-900">{t("auth.loginTitle")}</h1>
        <p className="mt-1 text-sm text-slate-600">{t("auth.loginSubtitle")}</p>

        {error && (
          <div className="mt-4 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="mt-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700">{t("auth.email")}</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-emerald-700 focus:outline-none focus:ring-1 focus:ring-emerald-700"
              placeholder="name@example.com"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700">{t("auth.password")}</label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-emerald-700 focus:outline-none focus:ring-1 focus:ring-emerald-700"
            />
          </div>

          <button
            type="submit"
            disabled={submitting}
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-emerald-800 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-emerald-900 disabled:opacity-60"
          >
            {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
            <span>{t("auth.loginButton")}</span>
          </button>
        </form>

        <div className="mt-5 text-center text-sm">
          <Link href="/register" className="font-medium text-emerald-800 hover:underline">
            {t("auth.noAccount")}
          </Link>
        </div>
      </div>
    </div>
  );
}
