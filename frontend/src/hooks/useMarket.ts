"use client";

import { useCallback, useState } from "react";
import type { MarketSearchResponse } from "../models/market";
import { getMarketAssets, getMarketHistory, searchMarket } from "../services/marketService";
import { useAsyncData } from "./useAsyncData";

export function useMarket(initialSymbol = "THYAO") {
  const [symbol, setSymbol] = useState(initialSymbol);
  const [searchResult, setSearchResult] = useState<MarketSearchResponse | null>(null);
  const [searching, setSearching] = useState(false);

  const loader = useCallback(async () => {
    const [assets, history] = await Promise.all([
      getMarketAssets(),
      getMarketHistory(symbol, 30),
    ]);
    return { assets, history };
  }, [symbol]);

  const state = useAsyncData(loader, [loader]);

  async function runSearch(query: string) {
    if (!query.trim()) {
      return;
    }
    setSearching(true);
    try {
      setSearchResult(await searchMarket({ query, top_k: 5 }));
    } finally {
      setSearching(false);
    }
  }

  return { ...state, symbol, setSymbol, searchResult, searching, runSearch };
}
