"use client";

import { useCallback, useEffect, useState } from "react";

type AsyncState<T> = {
  data: T | null;
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
  refresh: () => Promise<void>;
};

export function useAsyncData<T>(loader: () => Promise<T>, deps: unknown[] = []): AsyncState<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (showLoading: boolean) => {
    if (showLoading) {
      setLoading(true);
    }
    setError(null);
    try {
      setData(await loader());
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Veri alinamadi.");
    } finally {
      if (showLoading) {
        setLoading(false);
      }
    }
  }, deps);

  const refetch = useCallback(() => load(true), [load]);
  const refresh = useCallback(() => load(false), [load]);

  useEffect(() => {
    void refetch();
  }, [refetch]);

  return { data, loading, error, refetch, refresh };
}
