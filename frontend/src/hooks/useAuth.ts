"use client";

import { useEffect, useState } from "react";
import type { User } from "../models/auth";
import { getAccessToken } from "../services/apiClient";
import { getMe, login as loginRequest, logout as logoutRequest } from "../services/authService";

export function useAuth() {
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
      setHasToken(true);
      await refresh();
    } finally {
      setLoading(false);
    }
  }

  function logout() {
    logoutRequest();
    setUser(null);
    setHasToken(false);
  }

  useEffect(() => {
    void refresh();
  }, []);

  return { user, loading, error, hasToken, login, logout, refresh };
}
