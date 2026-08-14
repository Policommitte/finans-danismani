"use client";

import { useCallback } from "react";
import {
  getPortfolioAllocation,
  getPortfolioHoldings,
  getPortfolioSummary,
  getPortfolioTransactions,
} from "../services/portfolioService";
import { useAsyncData } from "./useAsyncData";

export function usePortfolio() {
  const loader = useCallback(async () => {
    const [summary, holdings, allocation, transactions] = await Promise.all([
      getPortfolioSummary(),
      getPortfolioHoldings(),
      getPortfolioAllocation(),
      getPortfolioTransactions(20),
    ]);

    return { summary, holdings, allocation, transactions };
  }, []);

  return useAsyncData(loader, [loader]);
}
