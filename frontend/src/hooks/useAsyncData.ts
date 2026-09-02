"use client";

import { useCallback, useEffect, useRef, useState } from "react";

type AsyncState<T> = {
  data: T | null;
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
  refresh: () => Promise<void>;
};

// Sayfalar arasi gecislerde yasayan, oturum boyunca kalan veri onbellegi.
//
// NEDEN VAR: her sayfa mount'unda `data=null, loading=true` ile basliyorduk;
// dashboard'a besinci gidis de ilki kadar suruyordu ve gecis perdesi
// (PageTransition) `loading` bitene kadar kapali kaliyordu. Onbellek
// "stale-while-revalidate" calisir: anahtar daha once dolduysa ilk render'da
// o veriyle ve loading=false ile baslanir, perde hemen acilir; taze veri
// arka planda cekilip yerine yazilir.
//
// Anahtar VERMEYEN cagrilar eski davranisi birebir korur - onbellek yalnizca
// gecis kapisindaki hook'lara acikca verilir.
//
// Oturum degisince (login/logout) `clearAsyncDataCache` cagrilir: baska
// kullanicinin portfoyu bir an bile ekrana gelmemeli.
const cache = new Map<string, unknown>();

export function clearAsyncDataCache() {
  cache.clear();
}

export function useAsyncData<T>(
  loader: () => Promise<T>,
  deps: unknown[] = [],
  cacheKey?: string,
): AsyncState<T> {
  const cachedInitially = cacheKey !== undefined && cache.has(cacheKey);
  const [data, setData] = useState<T | null>(() =>
    cachedInitially ? (cache.get(cacheKey as string) as T) : null,
  );
  const [loading, setLoading] = useState(!cachedInitially);
  const [error, setError] = useState<string | null>(null);
  const latestRequest = useRef(0);

  const load = useCallback(async (showLoading: boolean) => {
    const requestId = ++latestRequest.current;
    if (showLoading) {
      setLoading(true);
    }
    setError(null);
    try {
      const nextData = await loader();
      if (requestId === latestRequest.current) {
        setData(nextData);
        if (cacheKey !== undefined) {
          cache.set(cacheKey, nextData);
        }
      }
    } catch (exc) {
      if (requestId === latestRequest.current) {
        setError(exc instanceof Error ? exc.message : "Veri alinamadi.");
      }
    } finally {
      if (requestId === latestRequest.current) {
        setLoading(false);
      }
    }
  }, [...deps, cacheKey]);

  // Anahtar doluysa "yukleniyor" gostermeden onbellekten basla, arka planda
  // tazele. Bagimliliklar degistiginde de (ornegin market'te sembol degisince)
  // ayni yol calisir: daha once bakilan sembol aninda acilir.
  const refetch = useCallback(() => {
    if (cacheKey !== undefined && cache.has(cacheKey)) {
      setData(cache.get(cacheKey) as T);
      setLoading(false);
      return load(false);
    }
    return load(true);
  }, [load, cacheKey]);
  const refresh = useCallback(() => load(false), [load]);

  useEffect(() => {
    void refetch();
  }, [refetch]);

  return { data, loading, error, refetch, refresh };
}
