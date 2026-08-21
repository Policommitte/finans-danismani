"use client";

import { useCallback, useEffect } from "react";
import { getPortfolioPerformance, getPortfolioTransactions } from "../services/portfolioService";
import { useAsyncData } from "./useAsyncData";

export function usePortfolioTransactions(limit = 20) {
  const loader = useCallback(() => getPortfolioTransactions(limit), [limit]);
  return useAsyncData(loader, [loader]);
}

export function usePortfolioPerformance(hours = 24) {
  const loader = useCallback(() => getPortfolioPerformance(hours), [hours]);
  const performance = useAsyncData(loader, [loader]);

  useEffect(() => {
    const timer = window.setInterval(() => {
      void performance.refresh();
    }, 60_000);

    return () => window.clearInterval(timer);
  }, [performance.refresh]);

  return performance;
}
