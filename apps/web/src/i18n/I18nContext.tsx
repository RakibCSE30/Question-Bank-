"use client";

import React, { createContext, useCallback, useContext, useEffect, useState } from "react";
import bn from "./bn.json";
import en from "./en.json";
import type { Locale } from "@/types";

type Dictionary = typeof bn;
const dictionaries: Record<Locale, Dictionary> = { bn, en };

const BENGALI_DIGITS = ["০", "১", "২", "৩", "৪", "৫", "৬", "৭", "৮", "৯"];

export function toBengaliDigits(value: string | number): string {
  return String(value).replace(/\d/g, (digit) => BENGALI_DIGITS[Number(digit)] ?? digit);
}

interface I18nContextValue {
  locale: Locale;
  setLocale: (next: Locale) => void;
  toggleLocale: () => void;
  t: (path: string) => string;
  formatNumber: (value: number | string) => string;
}

const I18nContext = createContext<I18nContextValue | undefined>(undefined);

export function I18nProvider({ children }: { children: React.ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>("bn");

  useEffect(() => {
    const saved = window.localStorage.getItem("sqb_locale");
    if (saved === "bn" || saved === "en") {
      setLocaleState(saved);
    }
  }, []);

  const setLocale = useCallback((next: Locale) => {
    setLocaleState(next);
    window.localStorage.setItem("sqb_locale", next);
    document.documentElement.lang = next;
  }, []);

  const toggleLocale = useCallback(() => {
    setLocale(locale === "bn" ? "en" : "bn");
  }, [locale, setLocale]);

  const t = useCallback(
    (path: string): string => {
      const parts = path.split(".");
      let current: unknown = dictionaries[locale];
      for (const part of parts) {
        if (current && typeof current === "object" && part in (current as Record<string, unknown>)) {
          current = (current as Record<string, unknown>)[part];
        } else {
          return path;
        }
      }
      return typeof current === "string" ? current : path;
    },
    [locale]
  );

  const formatNumber = useCallback(
    (value: number | string): string => {
      return locale === "bn" ? toBengaliDigits(value) : String(value);
    },
    [locale]
  );

  return (
    <I18nContext.Provider value={{ locale, setLocale, toggleLocale, t, formatNumber }}>
      {children}
    </I18nContext.Provider>
  );
}

export function useI18n(): I18nContextValue {
  const ctx = useContext(I18nContext);
  if (!ctx) {
    throw new Error("useI18n must be used within I18nProvider");
  }
  return ctx;
}
