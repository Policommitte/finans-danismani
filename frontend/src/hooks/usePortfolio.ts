"use client";

import { useCallback, useEffect } from "react";
import type { PerformanceRange } from "../models/portfolio";
import { getPortfolioPerformance, getPortfolioTransactions } from "../services/portfolioService";
import { useAsyncData } from "./useAsyncData";

export function usePortfolioTransactions(limit = 20) {
  const loader = useCallback(() => getPortfolioTransactions(limit), [limit]);
  return useAsyncData(loader, [loader]);
}

export function usePortfolioPerformance(range: PerformanceRange = "1G") {
  const loader = useCallback(() => getPortfolioPerformance(range), [range]);
  const performance = useAsyncData(loader, [loader]);

  useEffect(() => {
    const timer = window.setInterval(() => {
      void performance.refresh();
    }, 60_000);

    return () => window.clearInterval(timer);
  }, [performance.refresh]);

  return performance;
}
