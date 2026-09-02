"use client";

import { createContext, ReactNode, useContext, useEffect, useMemo, useState } from "react";
import type { RegisterRequest, User } from "../models/auth";
import { getAccessToken } from "../services/apiClient";
import {
  getMe,
  login as loginRequest,
  logout as logoutRequest,
  register as registerRequest,
} from "../services/authService";
import { clearAsyncDataCache } from "./useAsyncData";

type AuthContextValue = {
  user: User | null;
  loading: boolean;
  error: string | null;
  hasToken: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (payload: RegisterRequest) => Promise<void>;
  logout: () => void;
  refresh: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [hasToken, setHasToken] = useState(false);

  async function refresh() {
    const token = getAccessToken();
    setHasToken(Boolean(token));

    if (!token) {
      setUser(null);
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      setUser(await getMe());
      setError(null);
    } catch (exc) {
      setUser(null);
      logoutRequest();
      clearAsyncDataCache();
      setHasToken(false);
      setError(exc instanceof Error ? exc.message : "Oturum dogrulanamadi.");
    } finally {
      setLoading(false);
    }
  }

  async function login(email: string, password: string) {
    setLoading(true);
    try {
      await loginRequest({ email, password });
      // Onceki oturumun sayfa verisi (portfoy, oneriler) yeni kullaniciya
      // bir an bile gorunmemeli.
      clearAsyncDataCache();
      setHasToken(true);
      await refresh();
    } finally {
      setLoading(false);
    }
  }

  async function register(payload: RegisterRequest) {
    setLoading(true);
    try {
      await registerRequest(payload);
      clearAsyncDataCache();
      setHasToken(true);
      await refresh();
    } finally {
      setLoading(false);
    }
  }

  function logout() {
    logoutRequest();
    clearAsyncDataCache();
    setUser(null);
    setHasToken(false);
  }

  useEffect(() => {
    void refresh();
  }, []);

  const value = useMemo(
    () => ({ user, loading, error, hasToken, login, register, logout, refresh }),
    [user, loading, error, hasToken],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const auth = useContext(AuthContext);

  if (!auth) {
    throw new Error("useAuth must be used inside AuthProvider.");
  }

  return auth;
}
