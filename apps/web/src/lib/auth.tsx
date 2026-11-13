"use client";

import React, { createContext, useCallback, useContext, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiFetch, clearTokens, getStoredTokens, storeTokens } from "./api";
import type { Locale, TokenResponse, User } from "@/types";

interface AuthContextValue {
  user: User | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<User>;
  register: (payload: {
    email: string;
    full_name: string;
    password: string;
    preferred_lang: Locale;
  }) => Promise<User>;
  logout: () => Promise<void>;
  refreshProfile: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();

  const refreshProfile = useCallback(async () => {
    const { accessToken } = getStoredTokens();
    if (!accessToken) {
      setUser(null);
      setIsLoading(false);
      return;
    }
    try {
      const me = await apiFetch<User>("/auth/me");
      setUser(me);
    } catch {
      clearTokens();
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void refreshProfile();
  }, [refreshProfile]);

  const login = useCallback(async (email: string, password: string): Promise<User> => {
    const data = await apiFetch<TokenResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    storeTokens(data.access_token, data.refresh_token);
    setUser(data.user);
    return data.user;
  }, []);

  const register = useCallback(
    async (payload: {
      email: string;
      full_name: string;
      password: string;
      preferred_lang: Locale;
    }): Promise<User> => {
      const data = await apiFetch<TokenResponse>("/auth/register", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      storeTokens(data.access_token, data.refresh_token);
      setUser(data.user);
      return data.user;
    },
    []
  );

  const logout = useCallback(async () => {
    try {
      await apiFetch<void>("/auth/logout", { method: "POST" });
    } catch {
      // Clear local session regardless
    } finally {
      clearTokens();
      setUser(null);
      router.push("/login");
    }
  }, [router]);

  return (
    <AuthContext.Provider value={{ user, isLoading, login, register, logout, refreshProfile }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return ctx;
}
