"use client";

import React, { useCallback, useEffect, useState } from "react";
import { Loader2, UserPlus } from "lucide-react";
import { AppShell } from "@/components/layout/AppShell";
import { ErrorState, LoadingState, RoleBadge } from "@/components/ui/StateViews";
import { useI18n } from "@/i18n/I18nContext";
import { apiFetch, ApiError } from "@/lib/api";
import type { User, UserListResponse, UserRole } from "@/types";

export default function AdminUsersPage() {
  const { t } = useI18n();
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<UserRole>("REVIEWER");
  const [creating, setCreating] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const loadUsers = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiFetch<UserListResponse>("/admin/users");
      setUsers(res.items);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("states.errorTitle"));
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    void loadUsers();
  }, [loadUsers]);

  async function handleCreateUser(e: React.FormEvent) {
    e.preventDefault();
    setFormError(null);
    setCreating(true);
    try {
      await apiFetch<User>("/admin/users", {
        method: "POST",
        body: JSON.stringify({
          email,
          full_name: fullName,
          password,
          role,
          preferred_lang: "bn",
        }),
      });
      setEmail("");
      setFullName("");
      setPassword("");
      await loadUsers();
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : t("states.errorTitle"));
    } finally {
      setCreating(false);
    }
  }

  async function toggleActive(target: User) {
    try {
      await apiFetch<User>(`/admin/users/${target.id}`, {
        method: "PATCH",
        body: JSON.stringify({ is_active: !target.is_active }),
      });
      await loadUsers();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("states.errorTitle"));
    }
  }

  return (
    <AppShell allowedRoles={["ADMIN"]}>
      <div className="space-y-6">
        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <h1 className="text-xl font-bold text-slate-900">{t("admin.usersHeading")}</h1>

          <form onSubmit={handleCreateUser} className="mt-5 grid grid-cols-1 gap-3 md:grid-cols-5">
            <input
              type="text"
              required
              minLength={2}
              placeholder={t("auth.fullName")}
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
            />
            <input
              type="email"
              required
              placeholder={t("auth.email")}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
            />
            <input
              type="password"
              required
              minLength={8}
              placeholder={t("auth.password")}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
            />
            <select
              value={role}
              onChange={(e) => setRole(e.target.value as UserRole)}
              className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
            >
              <option value="REVIEWER">{t("roles.REVIEWER")}</option>
              <option value="STUDENT">{t("roles.STUDENT")}</option>
              <option value="ADMIN">{t("roles.ADMIN")}</option>
            </select>
            <button
              type="submit"
              disabled={creating}
              className="inline-flex items-center justify-center gap-2 rounded-lg bg-emerald-800 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-900 disabled:opacity-60"
            >
              {creating ? <Loader2 className="h-4 w-4 animate-spin" /> : <UserPlus className="h-4 w-4" />}
              <span>{t("admin.createButton")}</span>
            </button>
          </form>

          {formError && (
            <p className="mt-3 text-sm text-rose-700">{formError}</p>
          )}
        </div>

        {loading && <LoadingState />}
        {!loading && error && <ErrorState message={error} onRetry={() => void loadUsers()} />}

        {!loading && !error && (
          <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
            <table className="min-w-full divide-y divide-slate-200 text-sm">
              <thead className="bg-slate-50 text-left text-xs font-semibold uppercase text-slate-600">
                <tr>
                  <th className="px-4 py-3">{t("auth.fullName")}</th>
                  <th className="px-4 py-3">{t("auth.email")}</th>
                  <th className="px-4 py-3">{t("admin.role")}</th>
                  <th className="px-4 py-3">{t("admin.status")}</th>
                  <th className="px-4 py-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {users.map((u) => (
                  <tr key={u.id}>
                    <td className="px-4 py-3 font-medium text-slate-900">{u.full_name}</td>
                    <td className="px-4 py-3 text-slate-600">{u.email}</td>
                    <td className="px-4 py-3">
                      <RoleBadge role={u.role} />
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${
                          u.is_active ? "bg-emerald-100 text-emerald-800" : "bg-slate-100 text-slate-600"
                        }`}
                      >
                        {u.is_active ? t("admin.active") : t("admin.inactive")}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button
                        type="button"
                        onClick={() => void toggleActive(u)}
                        className="rounded-md border border-slate-300 px-2.5 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50"
                      >
                        {u.is_active ? t("admin.deactivate") : t("admin.activate")}
                      </button>
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
