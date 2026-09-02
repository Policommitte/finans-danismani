"use client";

import { useEffect, useMemo, useState } from "react";
import {
  Area,
  AreaChart,
  Bar,
  CartesianGrid,
  Cell,
  ComposedChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useLanguage } from "../../contexts/LanguageContext";
import type { Holding, PortfolioValueSnapshotPoint } from "../../models/portfolio";
import Card from "../ui/Card";

export type PortfolioViewMode = "line" | "candlestick" | "pie";
export type DisplayCurrency = "TRY" | "USD" | "EUR";
export type PortfolioFxRates = { USD: number | null; EUR: number | null };

type CandlePoint = {
  ts: string;
  open: number;
  high: number;
  low: number;
  close: number;
  range: [number, number];
};

type CandlestickShapeProps = {
  x?: number;
  y?: number;
  width?: number;
  height?: number;
  payload?: CandlePoint;
};

const colors = [
  "var(--color-primary)",
  "var(--color-success)",
  "var(--color-chart-yellow)",
  "var(--color-danger)",
  "var(--color-chart-purple)",
  "var(--color-chart-cyan)",
];

function formatTime(value: string, language: "tr" | "en"): string {
  return new Intl.DateTimeFormat(language === "tr" ? "tr-TR" : "en-US", {
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

export function buildCompletedHalfHourlyCandles(
  points: PortfolioValueSnapshotPoint[],
): CandlePoint[] {
  const fiveMinutes = 5 * 60 * 1_000;
  const halfHour = 30 * 60 * 1_000;
  const buckets = new Map<number, Map<number, number>>();

  points.forEach((point) => {
    const timestamp = new Date(point.ts).getTime();
    if (!Number.isFinite(timestamp) || timestamp % fiveMinutes !== 0) {
      return;
    }

    const bucketTimestamp = Math.floor(timestamp / halfHour) * halfHour;
    const bucket = buckets.get(bucketTimestamp) ?? new Map<number, number>();
    bucket.set(timestamp, point.total_value_try);
    buckets.set(bucketTimestamp, bucket);
  });

  return [...buckets.entries()]
    .sort(([left], [right]) => left - right)
    .flatMap(([bucketTimestamp, values]) => {
      const expectedValues = Array.from({ length: 6 }, (_, index) =>
        values.get(bucketTimestamp + index * fiveMinutes),
      );
      if (expectedValues.some((value) => value == null)) {
        return [];
      }

      const completedValues = expectedValues as number[];
      const open = completedValues[0];
      const close = completedValues.at(-1) ?? open;
      const high = Math.max(...completedValues);
      const low = Math.min(...completedValues);
      return [{
        ts: new Date(bucketTimestamp).toISOString(),
        open,
        high,
        low,
        close,
        range: [low, high] as [number, number],
      }];
    });
}

function paddedDomain(minimum: number, maximum: number): [number, number] {
  const spread = maximum - minimum;
  const padding = Math.max(spread * 0.12, Math.abs(maximum) * 0.0005, 1);
  return [minimum - padding, maximum + padding];
}

function CandlestickShape({ x = 0, y = 0, width = 0, height = 0, payload }: CandlestickShapeProps) {
  if (!payload) {
    return null;
  }

  const rising = payload.close >= payload.open;
  const color = rising ? "var(--color-success)" : "var(--color-danger)";
  const priceRange = payload.high - payload.low;
  const centerX = x + width / 2;
  const wickTop = priceRange > 0 ? y : y - 7;
  const wickBottom = priceRange > 0 ? y + height : y + 7;
  const openY = priceRange > 0 ? y + ((payload.high - payload.open) / priceRange) * height : y;
  const closeY = priceRange > 0 ? y + ((payload.high - payload.close) / priceRange) * height : y;
  const bodyTop = Math.min(openY, closeY);
  const bodyHeight = Math.max(Math.abs(closeY - openY), 4);
  const bodyWidth = Math.max(5, Math.min(width * 0.58, 18));

  return (
    <g>
      <line x1={centerX} x2={centerX} y1={wickTop} y2={wickBottom} stroke={color} strokeWidth={2} />
      <rect
        x={centerX - bodyWidth / 2}
        y={bodyTop - (bodyHeight === 4 ? 2 : 0)}
        width={bodyWidth}
        height={bodyHeight}
        rx={1.5}
        fill={color}
      />
    </g>
  );
}

function ChartModeIcon({ mode }: { mode: PortfolioViewMode }) {
  if (mode === "line") {
    return (
      <svg aria-hidden="true" viewBox="0 0 24 24" className="h-5 w-5" fill="none">
        <path d="M3 17 8 12l4 3 8-9" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M17 6h3v3" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    );
  }

  if (mode === "candlestick") {
    return (
      <svg aria-hidden="true" viewBox="0 0 24 24" className="h-5 w-5" fill="none">
        <path d="M7 3v4m0 7v7M4.5 7h5v7h-5V7Zm12-4v6m0 7v5M14 9h5v7h-5V9Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    );
  }

  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" className="h-5 w-5" fill="none">
      <path d="M11 3a9 9 0 1 0 9 9h-9V3Z" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" />
      <path d="M14 3.5A7 7 0 0 1 20.5 10H14V3.5Z" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" />
    </svg>
  );
}

function ViewToggle({
  mode,
  onChange,
  language,
}: {
  mode: PortfolioViewMode;
  onChange: (mode: PortfolioViewMode) => void;
  language: "tr" | "en";
}) {
  return (
    <div
      className="flex shrink-0 rounded-md border app-border app-card-muted p-1"
      role="group"
      aria-label={language === "tr" ? "Grafik görünümü" : "Chart view"}
    >
      <button
        type="button"
        aria-pressed={mode === "line"}
        aria-label={language === "tr" ? "Çizgi grafik" : "Line chart"}
        title={language === "tr" ? "Çizgi grafik" : "Line chart"}
        onClick={() => onChange("line")}
        className={`flex h-9 w-10 items-center justify-center rounded-md transition ${
          mode === "line"
            ? "bg-[var(--color-panel-dark)] text-white shadow-sm"
            : "app-muted hover:text-[var(--color-heading)]"
        }`}
      >
        <ChartModeIcon mode="line" />
      </button>
      <button
        type="button"
        aria-pressed={mode === "candlestick"}
        aria-label={language === "tr" ? "Mum grafik" : "Candlestick chart"}
        title={language === "tr" ? "Mum grafik" : "Candlestick chart"}
        onClick={() => onChange("candlestick")}
        className={`flex h-9 w-10 items-center justify-center rounded-md transition ${
          mode === "candlestick"
            ? "bg-[var(--color-panel-dark)] text-white shadow-sm"
            : "app-muted hover:text-[var(--color-heading)]"
        }`}
      >
        <ChartModeIcon mode="candlestick" />
      </button>
      <button
        type="button"
        aria-pressed={mode === "pie"}
        aria-label={language === "tr" ? "Pasta grafik" : "Pie chart"}
        title={language === "tr" ? "Pasta grafik" : "Pie chart"}
        onClick={() => onChange("pie")}
        className={`flex h-9 w-10 items-center justify-center rounded-md transition ${
          mode === "pie"
            ? "bg-[var(--color-panel-dark)] text-white shadow-sm"
            : "app-muted hover:text-[var(--color-heading)]"
        }`}
      >
        <ChartModeIcon mode="pie" />
      </button>
    </div>
  );
}

function CurrencyToggle({
  currency,
  onChange,
  ratesReady,
  language,
}: {
  currency: DisplayCurrency;
  onChange: (currency: DisplayCurrency) => void;
  ratesReady: boolean;
  language: "tr" | "en";
}) {
  const options: Array<{ code: DisplayCurrency; symbol: string; tr: string; en: string }> = [
    { code: "TRY", symbol: "₺", tr: "Türk lirası", en: "Turkish lira" },
    { code: "USD", symbol: "$", tr: "Amerikan doları", en: "US dollar" },
    { code: "EUR", symbol: "€", tr: "Euro", en: "Euro" },
  ];

  return (
    <div
      className="flex shrink-0 rounded-md border app-border app-card-muted p-1"
      role="group"
      aria-label={language === "tr" ? "Gösterim para birimi" : "Display currency"}
    >
      {options.map((option) => {
        const disabled = option.code !== "TRY" && !ratesReady;
        return (
          <button
            key={option.code}
            type="button"
            disabled={disabled}
            aria-pressed={currency === option.code}
            aria-label={option[language]}
            title={option[language]}
            onClick={() => onChange(option.code)}
            className={`flex h-9 w-10 items-center justify-center rounded-md text-base font-semibold transition ${
              currency === option.code
                ? "bg-[var(--color-panel-dark)] text-white shadow-sm"
                : "app-muted hover:text-[var(--color-heading)] disabled:cursor-not-allowed disabled:opacity-35"
            }`}
          >
            {option.symbol}
          </button>
        );
      })}
    </div>
  );
}

export function PortfolioVisualization({
  holdings,
  cashTotalTry = 0,
  performancePoints,
  performanceLoading = false,
  performanceError = null,
  mode,
  onModeChange,
  displayCurrency,
  onDisplayCurrencyChange,
  fxRates,
}: {
  holdings: Holding[];
  cashTotalTry?: number;
  performancePoints: PortfolioValueSnapshotPoint[];
  performanceLoading?: boolean;
  performanceError?: string | null;
  mode: PortfolioViewMode;
  onModeChange: (mode: PortfolioViewMode) => void;
  displayCurrency: DisplayCurrency;
  onDisplayCurrencyChange: (currency: DisplayCurrency) => void;
  fxRates: PortfolioFxRates;
}) {
  const { language } = useLanguage();
  const [chartAnimationKey, setChartAnimationKey] = useState(0);
  const [pieAnimationKey, setPieAnimationKey] = useState(0);
  const [pieReady, setPieReady] = useState(false);
  const locale = language === "tr" ? "tr-TR" : "en-US";
  const displayCurrencyLabel = displayCurrency === "TRY"
    ? language === "tr" ? "TL" : "TRY"
    : displayCurrency;
  const ratesReady = fxRates.USD != null && fxRates.EUR != null;
  const conversionDivisor = displayCurrency === "TRY" ? 1 : (fxRates[displayCurrency] ?? 1);
  const currency = new Intl.NumberFormat(locale, {
    style: "currency",
    currency: displayCurrency,
    maximumFractionDigits: 0,
  });
  const compactCurrency = new Intl.NumberFormat(locale, {
    style: "currency",
    currency: displayCurrency,
    notation: "compact",
    maximumFractionDigits: 1,
  });
  const millionCurrency = new Intl.NumberFormat(locale, {
    style: "currency",
    currency: displayCurrency,
    minimumFractionDigits: 3,
    maximumFractionDigits: 3,
  });
  const formatYAxisValue = (value: number) =>
    Math.abs(value) >= 1_000_000
      ? `${millionCurrency.format(value / 1_000_000)} Mn`
      : compactCurrency.format(value);
  const quantityFormatter = new Intl.NumberFormat(locale, { maximumFractionDigits: 4 });
  const chartPoints = useMemo(
    () => performancePoints
      .filter((point) => !Number.isNaN(new Date(point.ts).getTime()))
      .map((point) => ({
        ...point,
        holdings_value_try: point.holdings_value_try / conversionDivisor,
        cash_value_try: point.cash_value_try / conversionDivisor,
        total_value_try: point.total_value_try / conversionDivisor,
      })),
    [conversionDivisor, performancePoints],
  );
  const totalValueTry = holdings.reduce((sum, item) => sum + item.market_value_try, 0) + cashTotalTry;
  const totalValue = totalValueTry / conversionDivisor;
  const pieData = [
    ...holdings,
    ...(cashTotalTry > 0 ? [{
      symbol: language === "tr" ? "NAKİT" : "CASH",
      asset_name: language === "tr" ? "Likit para" : "Liquid cash",
      asset_class: "CASH",
      currency: "TRY",
      quantity: 1,
      average_buy_price: cashTotalTry,
      current_price: cashTotalTry,
      daily_change_pct: 0,
      daily_change_try: 0,
      daily_change_pct_try: 0,
      market_value_try: cashTotalTry,
      cost_basis_try: cashTotalTry,
      pnl_try: 0,
      pnl_pct: 0,
    }] : []),
  ]
    .filter((item) => item.market_value_try > 0)
    .map((item) => ({
      ...item,
      value: item.market_value_try / conversionDivisor,
      percent: totalValueTry > 0 ? (item.market_value_try / totalValueTry) * 100 : 0,
    }));

  const first = chartPoints[0]?.total_value_try ?? 0;
  const current = chartPoints.at(-1)?.total_value_try ?? totalValue;
  const change = current - first;
  const changePct = first > 0 ? (change / first) * 100 : 0;
  const positive = change >= 0;
  const performanceValues = chartPoints.map((point) => point.total_value_try);
  const minimum = performanceValues.length > 0 ? Math.min(...performanceValues) : current;
  const maximum = performanceValues.length > 0 ? Math.max(...performanceValues) : current;
  const lineDomain = paddedDomain(minimum, maximum);
  const trendStops = useMemo(() => {
    const success = "var(--color-success)";
    const danger = "var(--color-danger)";

    if (chartPoints.length < 2) {
      return [
        { offset: 0, color: success },
        { offset: 100, color: success },
      ];
    }

    const segmentColors = chartPoints.slice(1).map((point, index) =>
      point.total_value_try >= chartPoints[index].total_value_try ? success : danger,
    );
    const stops = [{ offset: 0, color: segmentColors[0] }];

    for (let index = 1; index < chartPoints.length - 1; index += 1) {
      const offset = (index / (chartPoints.length - 1)) * 100;
      stops.push({ offset, color: segmentColors[index - 1] });
      stops.push({ offset, color: segmentColors[index] });
    }

    stops.push({ offset: 100, color: segmentColors.at(-1) ?? success });
    return stops;
  }, [chartPoints]);
  const candlePoints = useMemo(
    () => buildCompletedHalfHourlyCandles(chartPoints),
    [chartPoints],
  );
  const candleMinimum = candlePoints.length > 0 ? Math.min(...candlePoints.map((point) => point.low)) : current;
  const candleMaximum = candlePoints.length > 0 ? Math.max(...candlePoints.map((point) => point.high)) : current;
  const candleDomain = paddedDomain(candleMinimum, candleMaximum);

  useEffect(() => {
    if (mode !== "pie") {
      setPieReady(false);
      return;
    }

    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const timer = window.setTimeout(() => setPieReady(true), reduceMotion ? 0 : 240);
    return () => window.clearTimeout(timer);
  }, [mode, pieAnimationKey]);

  function formatCurrentPrice(item: Holding): string {
    const unitPriceTry = item.quantity > 0 ? item.market_value_try / item.quantity : 0;
    return new Intl.NumberFormat(locale, {
      style: "currency",
      currency: displayCurrency,
      maximumFractionDigits: unitPriceTry / conversionDivisor < 10 ? 4 : 2,
    }).format(unitPriceTry / conversionDivisor);
  }

  function handleModeChange(nextMode: PortfolioViewMode) {
    if (nextMode === mode) {
      return;
    }

    setChartAnimationKey((currentKey) => currentKey + 1);

    if (nextMode === "pie" && mode !== "pie") {
      setPieAnimationKey((currentKey) => currentKey + 1);
    }

    onModeChange(nextMode);
  }

  return (
    <Card className={mode === "pie" ? "min-h-[560px]" : "h-full"}>
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-base font-semibold app-heading">
            {mode === "line"
              ? language === "tr" ? "Portföy performansı" : "Portfolio performance"
              : mode === "candlestick"
                ? language === "tr" ? "Portföy mum grafiği" : "Portfolio candlestick chart"
              : language === "tr" ? "Hisse ve varlık dağılımı" : "Holdings and asset allocation"}
          </h2>
          <p className="mt-1 text-xs app-muted">
            {mode === "line"
              ? language === "tr" ? `Son 24 saat · ${displayCurrencyLabel} bazlı` : `Last 24 hours · ${displayCurrencyLabel} based`
              : mode === "candlestick"
                ? language === "tr" ? `30 dakikalık · ${displayCurrencyLabel} bazlı` : `30-minute · ${displayCurrencyLabel} based`
              : language === "tr" ? "Portföydeki varlık oranları ve değerleri" : "Portfolio asset weights and values"}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <CurrencyToggle
            currency={displayCurrency}
            onChange={onDisplayCurrencyChange}
            ratesReady={ratesReady}
            language={language}
          />
          <ViewToggle mode={mode} onChange={handleModeChange} language={language} />
        </div>
      </div>

      <div
        key={mode}
        data-mode={mode}
        className={`portfolio-chart-content ${mode === "pie" ? "mt-5 min-h-[460px]" : "mt-3 h-[420px] overflow-y-auto pr-1"}`}
      >
        {mode === "pie" ? (
          <div className="grid min-h-[450px] items-center gap-8 lg:grid-cols-[minmax(280px,.78fr)_minmax(0,1.35fr)]">
            <div className="relative mx-auto aspect-square w-full max-w-[360px]">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  {pieReady ? (
                    <Pie
                      key={`portfolio-pie-${pieAnimationKey}`}
                      animationId={pieAnimationKey}
                      data={pieData}
                      dataKey="percent"
                      nameKey="symbol"
                      innerRadius="57%"
                      outerRadius="82%"
                      cornerRadius={11}
                      paddingAngle={3}
                      stroke="none"
                      isAnimationActive
                      animationBegin={0}
                      animationDuration={1000}
                      animationEasing="ease-out"
                    >
                      {pieData.map((item, index) => (
                        <Cell key={item.symbol} fill={colors[index % colors.length]} />
                      ))}
                    </Pie>
                  ) : null}
                  <Tooltip
                    formatter={(value, name) => [`%${Number(value).toFixed(2)}`, String(name)]}
                    contentStyle={{
                      background: "var(--color-surface)",
                      borderColor: "var(--color-border)",
                      borderRadius: "6px",
                      color: "var(--color-text)",
                      boxShadow: "0 10px 30px rgb(0 0 0 / 0.12)",
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
              <div className={`pointer-events-none absolute inset-0 flex flex-col items-center justify-center text-center transition-opacity duration-300 ${pieReady ? "opacity-100" : "opacity-0"}`}>
                <span className="text-[11px] font-semibold uppercase app-muted">
                  {language === "tr" ? "Portföy değeri" : "Portfolio value"}
                </span>
                <strong className="mt-1 text-xl font-bold app-heading">{currency.format(totalValue)}</strong>
              </div>
            </div>

            <div className="min-w-0">
              <h3 className="mb-2 text-sm font-semibold app-heading">
                {language === "tr" ? "Varlıklar" : "Assets"}
              </h3>
              <div className="divide-y rounded-md border app-border app-border-soft">
                {pieData.map((item, index) => (
                  <div
                    key={item.symbol}
                    className="grid min-h-[82px] grid-cols-[minmax(0,1fr)_auto] items-center gap-4 px-4 py-3"
                  >
                    <div className="flex min-w-0 items-center gap-3">
                      <span
                        className="h-3 w-3 shrink-0 rounded-full"
                        style={{ backgroundColor: colors[index % colors.length] }}
                      />
                      <div className="min-w-0">
                        <div className="truncate text-sm font-semibold app-heading">
                          {item.symbol}
                          {item.asset_name && item.asset_name !== item.symbol ? (
                            <span className="font-normal app-muted"> · {item.asset_name}</span>
                          ) : null}
                        </div>
                        <div className="mt-1 text-xs app-muted">
                          {item.asset_class === "CASH"
                            ? language === "tr" ? "Kullanılabilir ve bloke bakiye" : "Available and reserved balance"
                            : `${quantityFormatter.format(item.quantity)} ${language === "tr" ? "adet" : "units"} · ${formatCurrentPrice(item)}`}
                        </div>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-sm font-semibold app-heading">
                        {currency.format(item.market_value_try / conversionDivisor)}
                      </div>
                      <div className="mt-1 text-xs font-semibold app-success">%{item.percent.toFixed(2)}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        ) : performanceLoading ? (
          <div className="grid min-h-[356px] place-items-center text-sm app-muted">
            {language === "tr" ? "Performans verisi yükleniyor..." : "Loading performance data..."}
          </div>
        ) : performanceError ? (
          <div className="grid min-h-[356px] place-items-center px-6 text-center text-sm app-danger">
            {language === "tr" ? "Performans verisi şu anda alınamıyor." : "Performance data is currently unavailable."}
          </div>
        ) : chartPoints.length === 0 ? (
          <div className="grid min-h-[356px] place-items-center text-center text-sm app-muted">
            {language === "tr" ? "Henüz portföy snapshot verisi oluşmadı." : "No portfolio snapshot data is available yet."}
          </div>
        ) : mode === "candlestick" && candlePoints.length === 0 ? (
          <div className="grid min-h-[356px] place-items-center px-6 text-center text-sm app-muted">
            {language === "tr"
              ? "Tamamlanmış bir 30 dakikalık mum için henüz altı adet 5 dakikalık değer oluşmadı."
              : "Six 5-minute values have not yet formed a completed 30-minute candle."}
          </div>
        ) : mode === "candlestick" ? (
          <>
            <div className="flex items-end justify-between gap-4">
              <div className="text-2xl font-semibold app-heading">{currency.format(current)}</div>
              <span className={`text-sm font-semibold ${positive ? "app-success" : "app-danger"}`}>
                {positive ? "▲" : "▼"} %{Math.abs(changePct).toFixed(2)}
              </span>
            </div>
            <div className="mt-3 h-72">
              <ResponsiveContainer>
                <ComposedChart data={candlePoints} margin={{ top: 10, right: 12, left: 4, bottom: 0 }}>
                  <CartesianGrid vertical={false} stroke="var(--color-chart-grid)" strokeDasharray="3 3" />
                  <XAxis
                    dataKey="ts"
                    tickFormatter={(value) => formatTime(value, language)}
                    axisLine={false}
                    tickLine={false}
                    minTickGap={36}
                    tick={{ fill: "var(--color-muted)", fontSize: 12 }}
                  />
                  <YAxis
                    width={94}
                    domain={candleDomain}
                    tickFormatter={(value) => formatYAxisValue(Number(value))}
                    axisLine={false}
                    tickLine={false}
                    tick={{ fill: "var(--color-muted)", fontSize: 12 }}
                  />
                  <Tooltip
                    cursor={{ fill: "var(--color-overlay-soft)" }}
                    content={({ active, payload, label }) => {
                      const candle = payload?.[0]?.payload as CandlePoint | undefined;
                      if (!active || !candle) {
                        return null;
                      }

                      const labels = language === "tr"
                        ? ["Açılış", "En yüksek", "En düşük", "Kapanış"]
                        : ["Open", "High", "Low", "Close"];
                      const values = [candle.open, candle.high, candle.low, candle.close];

                      return (
                        <div className="rounded-md border app-border bg-[var(--color-panel-dark)] p-3 text-xs text-[var(--color-market-text)] shadow-xl">
                          <div className="mb-2 font-semibold text-[var(--color-on-primary-muted)]">
                            {formatTime(String(label), language)}
                          </div>
                          <div className="grid grid-cols-[auto_auto] gap-x-4 gap-y-1">
                            {labels.map((item, index) => (
                              <div key={item} className="contents">
                                <span className="text-[var(--color-on-primary-muted)]">{item}</span>
                                <strong className="text-right">{currency.format(values[index])}</strong>
                              </div>
                            ))}
                          </div>
                        </div>
                      );
                    }}
                  />
                  <Bar
                    key={`portfolio-candles-${chartAnimationKey}`}
                    animationId={chartAnimationKey}
                    className="portfolio-cartesian-series portfolio-candlestick-series"
                    dataKey="range"
                    shape={(props: CandlestickShapeProps) => <CandlestickShape {...props} />}
                    isAnimationActive={false}
                  />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
            <div className="grid grid-cols-2 gap-4 border-t app-border pt-4 text-sm sm:grid-cols-4">
              {[
                [language === "tr" ? "AÇILIŞ" : "OPEN", candlePoints[0]?.open ?? current],
                [language === "tr" ? "EN YÜKSEK" : "HIGHEST", candleMaximum],
                [language === "tr" ? "EN DÜŞÜK" : "LOWEST", candleMinimum],
                [language === "tr" ? "KAPANIŞ" : "CLOSE", candlePoints.at(-1)?.close ?? current],
              ].map(([label, value]) => (
                <div key={String(label)}>
                  <div className="text-xs font-semibold app-muted">{label}</div>
                  <div className="mt-1 font-semibold app-heading">{currency.format(Number(value))}</div>
                </div>
              ))}
            </div>
          </>
        ) : (
          <>
            <div className="flex items-end justify-between gap-4">
              <div className="text-2xl font-semibold app-heading">{currency.format(current)}</div>
              <div className="flex items-center gap-4">
                <span className={`text-sm font-semibold ${positive ? "app-success" : "app-danger"}`}>
                  {positive ? "▲" : "▼"} %{Math.abs(changePct).toFixed(2)}
                </span>
              </div>
            </div>
            <div className="mt-3 h-72">
              <ResponsiveContainer>
                <AreaChart data={chartPoints} margin={{ top: 10, right: 12, left: 4, bottom: 0 }}>
                  <defs>
                    <linearGradient id="portfolio-trend-gradient" x1="0" y1="0" x2="1" y2="0">
                      {trendStops.map((stop, index) => (
                        <stop
                          key={`${stop.offset}-${index}`}
                          offset={`${stop.offset}%`}
                          stopColor={stop.color}
                        />
                      ))}
                    </linearGradient>
                  </defs>
                  <CartesianGrid vertical={false} stroke="var(--color-chart-grid)" strokeDasharray="3 3" />
                  <XAxis
                    dataKey="ts"
                    tickFormatter={(value) => formatTime(value, language)}
                    axisLine={false}
                    tickLine={false}
                    minTickGap={36}
                    tick={{ fill: "var(--color-muted)", fontSize: 12 }}
                  />
                  <YAxis
                    width={94}
                    domain={lineDomain}
                    tickFormatter={(value) => formatYAxisValue(Number(value))}
                    axisLine={false}
                    tickLine={false}
                    tick={{ fill: "var(--color-muted)", fontSize: 12 }}
                  />
                  <Tooltip
                    labelFormatter={(label) => formatTime(String(label), language)}
                    formatter={(value) => [
                      currency.format(Number(value)),
                      language === "tr" ? "Portföy" : "Portfolio",
                    ]}
                    contentStyle={{
                      background: "var(--color-panel-dark)",
                      border: "1px solid var(--color-border)",
                      borderRadius: "6px",
                      color: "var(--color-market-text)",
                      boxShadow: "0 12px 30px rgb(0 0 0 / 0.18)",
                    }}
                    itemStyle={{ color: "var(--color-market-text)" }}
                    labelStyle={{ color: "var(--color-on-primary-muted)" }}
                  />
                  <Area
                    key={`portfolio-area-${chartAnimationKey}`}
                    animationId={chartAnimationKey}
                    className="portfolio-cartesian-series"
                    type="monotone"
                    dataKey="total_value_try"
                    stroke="url(#portfolio-trend-gradient)"
                    strokeWidth={3}
                    fill="url(#portfolio-trend-gradient)"
                    fillOpacity={0.1}
                    activeDot={{ r: 5, strokeWidth: 2, fill: "var(--color-surface)" }}
                    isAnimationActive={false}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
            <div className="grid grid-cols-2 gap-4 border-t app-border pt-4 text-sm">
              <div>
                <div className="text-xs font-semibold app-muted">{language === "tr" ? "EN YÜKSEK" : "HIGHEST"}</div>
                <div className="mt-1 font-semibold app-heading">{currency.format(maximum)}</div>
              </div>
              <div>
                <div className="text-xs font-semibold app-muted">{language === "tr" ? "EN DÜŞÜK" : "LOWEST"}</div>
                <div className="mt-1 font-semibold app-heading">{currency.format(minimum)}</div>
              </div>
            </div>
          </>
        )}
      </div>
    </Card>
  );
}
