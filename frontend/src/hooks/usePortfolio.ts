"use client";

import { useCallback, useEffect } from "react";
import {
  getPortfolioSnapshotPerformance,
  getPortfolioTransactions,
} from "../services/portfolioService";
import { useAsyncData } from "./useAsyncData";

export function usePortfolioTransactions(limit = 20) {
  const loader = useCallback(() => getPortfolioTransactions(limit), [limit]);
  return useAsyncData(loader, [loader]);
}

export function usePortfolioPerformance(hours = 24) {
  const loader = useCallback(() => getPortfolioSnapshotPerformance(hours), [hours]);
  const performance = useAsyncData(loader, [loader], `portfolio:performance:${hours}`);

  useEffect(() => {
    const timer = window.setInterval(() => {
      void performance.refresh();
    }, 60_000);

    return () => window.clearInterval(timer);
  }, [performance.refresh]);

  return performance;
}
