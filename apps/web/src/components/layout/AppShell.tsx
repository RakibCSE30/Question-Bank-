"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  BookCheck,
  BookMarked,
  Brain,
  FileText,
  GraduationCap,
  Languages,
  LogOut,
  Menu,
  Search,
  ShieldCheck,
  Sparkles,
  Users,
  X,
} from "lucide-react";
import { useI18n } from "@/i18n/I18nContext";
import { useAuth } from "@/lib/auth";
import { LoadingState, RoleBadge, UnauthorizedState } from "@/components/ui/StateViews";
import type { UserRole } from "@/types";

interface NavItem {
  href: string;
  labelKey: string;
  roles: UserRole[];
  icon: React.ComponentType<{ className?: string }>;
}

const NAV_ITEMS: NavItem[] = [
  {
    href: "/",
    labelKey: "nav.studentDashboard",
    roles: ["STUDENT", "REVIEWER", "ADMIN"],
    icon: GraduationCap,
  },
  {
    href: "/reviewer",
    labelKey: "nav.reviewerWorkbench",
    roles: ["REVIEWER", "ADMIN"],
    icon: BookCheck,
  },
  {
    href: "/admin",
    labelKey: "nav.adminConsole",
    roles: ["ADMIN"],
    icon: ShieldCheck,
  },
  {
    href: "/admin/curriculum",
    labelKey: "nav.curriculum",
    roles: ["ADMIN"],
    icon: BookMarked,
  },
  {
    href: "/admin/documents",
    labelKey: "nav.documents",
    roles: ["ADMIN", "REVIEWER"],
    icon: FileText,
  },
  {
    href: "/admin/rag",
    labelKey: "nav.ragSearch",
    roles: ["ADMIN", "REVIEWER"],
    icon: Search,
  },
  {
    href: "/admin/analysis",
    labelKey: "nav.analysis",
    roles: ["ADMIN", "REVIEWER"],
    icon: Brain,
  },
  {
    href: "/admin/generator",
    labelKey: "nav.generator",
    roles: ["ADMIN", "REVIEWER"],
    icon: Sparkles,
  },
  {
    href: "/admin/users",
    labelKey: "nav.userManagement",
    roles: ["ADMIN"],
    icon: Users,
  },
];

export function AppShell({
  allowedRoles,
  children,
}: {
  allowedRoles: UserRole[];
  children: React.ReactNode;
}) {
  const { user, isLoading, logout } = useAuth();
  const { locale, toggleLocale, t } = useI18n();
  const pathname = usePathname();
  const router = useRouter();
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    if (!isLoading && !user) {
      router.replace("/login");
    }
  }, [isLoading, user, router]);

  if (isLoading || !user) {
    return (
      <div className="mx-auto max-w-5xl p-6">
        <LoadingState />
      </div>
    );
  }

  const isAuthorized = allowedRoles.includes(user.role);
  const visibleNav = NAV_ITEMS.filter((item) => item.roles.includes(user.role));

  return (
    <div className="min-h-screen bg-paper text-ink">
      <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/95 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6">
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => setMobileOpen((prev) => !prev)}
              className="rounded-lg border border-slate-200 p-2 text-slate-700 lg:hidden"
              aria-label="Toggle Menu"
            >
              {mobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
            </button>
            <Link href="/" className="flex items-center gap-2.5">
              <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-emerald-800 text-sm font-bold text-white">
                স
              </span>
              <div>
                <div className="text-base font-bold leading-tight text-slate-900">
                  {t("app.name")}
                </div>
                <div className="hidden text-xs text-slate-500 sm:block">
                  {t("app.subtitle")}
                </div>
              </div>
            </Link>
          </div>

          <div className="flex items-center gap-3">
            <span className="hidden rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-800 md:inline-flex">
              {t("app.phaseBadge")}
            </span>

            <button
              type="button"
              onClick={toggleLocale}
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 transition hover:bg-slate-50"
            >
              <Languages className="h-4 w-4 text-emerald-700" />
              <span>{locale === "bn" ? "বাংলা | EN" : "EN | বাংলা"}</span>
            </button>

            <div className="hidden items-center gap-2 border-l border-slate-200 pl-3 sm:flex">
              <div className="text-right">
                <div className="text-xs font-semibold text-slate-900">{user.full_name}</div>
                <div className="text-[11px] text-slate-500">{user.email}</div>
              </div>
              <RoleBadge role={user.role} />
            </div>

            <button
              type="button"
              onClick={() => void logout()}
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-700 transition hover:border-rose-200 hover:bg-rose-50 hover:text-rose-700"
            >
              <LogOut className="h-4 w-4" />
              <span className="hidden sm:inline">{t("nav.logout")}</span>
            </button>
          </div>
        </div>
      </header>

      <div className="mx-auto flex max-w-7xl gap-6 px-4 py-6 sm:px-6">
        <aside
          className={`${
            mobileOpen ? "fixed inset-y-16 left-0 z-20 w-64 border-r border-slate-200 bg-white p-4 shadow-lg" : "hidden"
          } lg:block lg:w-60 lg:shrink-0`}
        >
          <nav className="space-y-1">
            {visibleNav.map((item) => {
              const Icon = item.icon;
              const active = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={() => setMobileOpen(false)}
                  className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition ${
                    active
                      ? "bg-emerald-800 text-white shadow-sm"
                      : "text-slate-700 hover:bg-white hover:text-slate-900"
                  }`}
                >
                  <Icon className="h-4 w-4 shrink-0" />
                  <span>{t(item.labelKey)}</span>
                </Link>
              );
            })}
          </nav>
        </aside>

        <main className="min-w-0 flex-1">
          {isAuthorized ? children : <UnauthorizedState />}
        </main>
      </div>
    </div>
  );
}
