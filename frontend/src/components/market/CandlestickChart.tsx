"use client";

import { useEffect, useRef } from "react";
import type { IChartApi, UTCTimestamp } from "lightweight-charts";
import type { OhlcCandle } from "../../models/market";

function resolveColor(varName: string, fallback: string): string {
  if (typeof window === "undefined") {
    return fallback;
  }
  const value = getComputedStyle(document.documentElement).getPropertyValue(varName).trim();
  return value || fallback;
}

function toUnixSeconds(ts: string): UTCTimestamp {
  return Math.floor(new Date(ts).getTime() / 1000) as UTCTimestamp;
}

//: Sadece mumlar gorunur - EMA/SMA gibi cizgi overlay'leri BILINCLI olarak
//: yok (kullanici talebi: mum modunda hicbir cizgi olmasin).
export function CandlestickChart({ candles }: { candles: OhlcCandle[] }) {
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container || candles.length === 0) {
      return;
    }

    let disposed = false;
    let chart: IChartApi | null = null;
    let candleSeries: ReturnType<IChartApi["addSeries"]> | null = null;
    let resizeObserver: ResizeObserver | null = null;
    let themeObserver: MutationObserver | null = null;

    function applyThemeColors() {
      if (!chart) return;
      const textColor = resolveColor("--color-muted", "#64748b");
      const gridColor = resolveColor("--color-chart-grid", "#e2e8f0");
      const upColor = resolveColor("--color-success", "#16a34a");
      const downColor = resolveColor("--color-danger", "#dc2626");
      chart.applyOptions({
        layout: { textColor },
        grid: { vertLines: { color: gridColor }, horzLines: { color: gridColor } },
        rightPriceScale: { borderColor: gridColor },
        timeScale: { borderColor: gridColor },
      });
      candleSeries?.applyOptions({
        upColor,
        downColor,
        borderUpColor: upColor,
        borderDownColor: downColor,
        wickUpColor: upColor,
        wickDownColor: downColor,
      });
    }

    void (async () => {
      const { createChart, CandlestickSeries, ColorType } = await import("lightweight-charts");
      if (disposed || !containerRef.current) return;

      chart = createChart(containerRef.current, {
        layout: {
          background: { type: ColorType.Solid, color: "transparent" },
          fontSize: 10,
          // Kucuk grafiklerde varsayilan "TradingView" filigranini kapatir.
          // NOT: kutuphanenin lisansi (Apache-2.0) bu logoyu, atif gereksinimini
          // (NOTICE dosyasi + tradingview.com linki) karsilamanin bir yolu
          // olarak sunuyor; kapatilinca atif baska bir yerde (repo NOTICE/README)
          // saglanmali - bu proje kapsaminda bu ayri bir is.
          attributionLogo: false,
        },
        crosshair: { mode: 0 },
        timeScale: { timeVisible: true, secondsVisible: false },
        height: containerRef.current.clientHeight,
        width: containerRef.current.clientWidth,
      });

      candleSeries = chart.addSeries(CandlestickSeries, {});
      applyThemeColors();
      candleSeries.setData(
        candles.map((c) => ({
          time: toUnixSeconds(c.ts),
          open: c.open,
          high: c.high,
          low: c.low,
          close: c.close,
        }))
      );

      chart.timeScale().fitContent();

      resizeObserver = new ResizeObserver((entries) => {
        const entry = entries[0];
        if (!chart || !entry) return;
        chart.applyOptions({ width: entry.contentRect.width, height: entry.contentRect.height });
      });
      resizeObserver.observe(containerRef.current);

      themeObserver = new MutationObserver(applyThemeColors);
      themeObserver.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
    })();

    return () => {
      disposed = true;
      resizeObserver?.disconnect();
      themeObserver?.disconnect();
      chart?.remove();
    };
  }, [candles]);

  return <div ref={containerRef} className="h-full w-full" />;
}
