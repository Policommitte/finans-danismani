"use client";

import { useCallback, useEffect, useState } from "react";
import type { ChartInterval, ChartRange, MarketSearchResponse } from "../models/market";
import { getMarketAssets, getMarketCandles, searchMarket } from "../services/marketService";
import { useAsyncData } from "./useAsyncData";

export function useMarket(initialSymbol = "THYAO") {
  const [symbol, setSymbol] = useState(initialSymbol);
  const [chartInterval, setChartInterval] = useState<ChartInterval>("1h");
  const [chartRange, setChartRange] = useState<ChartRange>("1m");
  const [chartRangePresetActive, setChartRangePresetActive] = useState(true);
  const [chartRangePresetRevision, setChartRangePresetRevision] = useState(0);
  const [searchResult, setSearchResult] = useState<MarketSearchResponse | null>(null);
  const [searching, setSearching] = useState(false);

  const loader = useCallback(async () => {
    const [assets, candles] = await Promise.all([
      getMarketAssets(),
      getMarketCandles(symbol, chartInterval, chartRange),
    ]);
    return { assets, candles };
  }, [chartInterval, chartRange, symbol]);

  const state = useAsyncData(
    loader,
    [loader],
    `market:${symbol}:${chartInterval}:${chartRange}`,
  );

  useEffect(() => {
    const timer = window.setInterval(() => void state.refresh(), 60_000);
    return () => window.clearInterval(timer);
  }, [state.refresh]);

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

  function changeChartRange(range: ChartRange) {
    const preferredIntervals: Record<ChartRange, ChartInterval> = {
      "1d": "5m",
      "5d": "15m",
      // 1A/3A gunluk (1d) mumla acilir: hem bu pencerede saatlik/4 saatlik
      // mumlar asiri kalabalik olurdu (540-720 bar) hem de tahmin cizgisi
      // SADECE gunluk grafikte cizilir (bkz. PriceHistoryChart.forecastCizilebilir) -
      // 1Y'de zaten boyleydi, 1A/3A'da da tahminin gorunmesi icin gerekli.
      "1m": "1d",
      "3m": "1d",
      "1y": "1d",
    };
    const shouldResetCurrentView = range === chartRange
      && preferredIntervals[range] === chartInterval;
    setChartRange(range);
    setChartInterval(preferredIntervals[range]);
    setChartRangePresetActive(true);
    if (shouldResetCurrentView) {
      setChartRangePresetRevision((revision) => revision + 1);
    }
  }

  function changeChartInterval(interval: ChartInterval) {
    if (interval !== chartInterval) {
      setChartRangePresetActive(false);
    }
    setChartInterval(interval);
  }

  const clearChartRangePreset = useCallback(() => {
    setChartRangePresetActive(false);
  }, []);

  return {
    ...state,
    symbol,
    setSymbol,
    chartInterval,
    setChartInterval: changeChartInterval,
    chartRange,
    chartRangePresetActive,
    chartRangePresetRevision,
    clearChartRangePreset,
    setChartRange: changeChartRange,
    searchResult,
    searching,
    runSearch,
  };
}
