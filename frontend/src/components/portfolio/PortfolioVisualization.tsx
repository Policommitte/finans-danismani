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
import type {
  Holding,
  PerformanceRange,
  PortfolioValueSnapshotPoint,
} from "../../models/portfolio";
import Card from "../ui/Card";

//: Grafik altbasligi secilen donemi soyler - "Bugün" yazip yillik seri
//: cizmek kullaniciyi yaniltirdi.
const RANGE_SUBTITLES: Record<PerformanceRange, { tr: string; en: string }> = {
  "1G": { tr: "Bugün", en: "Today" },
  "1H": { tr: "Son 1 hafta", en: "Last week" },
  "1A": { tr: "Son 1 ay", en: "Last month" },
  "1Y": { tr: "Son 1 yıl", en: "Last year" },
};

//: Mum grafiginin kova boyu secilen doneme gore degisir.
const CANDLE_SUBTITLES: Record<PerformanceRange, { tr: string; en: string }> = {
  "1G": { tr: "30 dakikalık", en: "30-minute" },
  "1H": { tr: "Günlük", en: "Daily" },
  "1A": { tr: "Günlük", en: "Daily" },
  "1Y": { tr: "Haftalık", en: "Weekly" },
};

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

/**
 * X ekseni ve ipucu etiketi. Bicim SECILEN DONEME baglidir: tek gunluk
 * grafikte saat anlamlidir, aylik/yillik grafikte her nokta ayri bir gun
 * oldugu icin saat gostermek tum etiketleri ayni ("00:00") yapardi.
 */
const TIME_FORMATS: Record<PerformanceRange, Intl.DateTimeFormatOptions> = {
  "1G": { hour: "2-digit", minute: "2-digit" },
  // 1H de backend'de gunluk kovaya indi (bkz. _GUNLUK_KOVA_SINIR_SAAT):
  // nokta basina bir gun dustugu icin saat gostermek yaniltici olurdu.
  "1H": { day: "2-digit", month: "2-digit" },
  "1A": { day: "2-digit", month: "2-digit" },
  "1Y": { day: "2-digit", month: "short" },
};

function formatTime(value: string, language: "tr" | "en", range: PerformanceRange): string {
  return new Intl.DateTimeFormat(
    language === "tr" ? "tr-TR" : "en-US",
    TIME_FORMATS[range],
  ).format(new Date(value));
}

const ISTANBUL_DATE_FORMATTER = new Intl.DateTimeFormat("en-GB", {
  timeZone: "Europe/Istanbul",
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
});

function istanbulDateKey(timestamp: number): string {
  const parts = Object.fromEntries(
    ISTANBUL_DATE_FORMATTER.formatToParts(new Date(timestamp)).map((part) => [part.type, part.value]),
  );
  return `${parts.year}-${parts.month}-${parts.day}`;
}

/**
 * Uzun donem cizgisinin tarih araligini korurken bugunun yeniden hesaplanan
 * noktasini en yeni gercek snapshot ile degistirir.
 */
export function mergeLatestSnapshotIntoDailyHistory(
  history: PortfolioValueSnapshotPoint[],
  latestSnapshot: PortfolioValueSnapshotPoint | undefined,
): PortfolioValueSnapshotPoint[] {
  if (!latestSnapshot) {
    return history;
  }

  const latestTimestamp = new Date(latestSnapshot.ts).getTime();
  if (!Number.isFinite(latestTimestamp)) {
    return history;
  }

  const latestDay = istanbulDateKey(latestTimestamp);
  return [
    ...history.filter((point) => {
      const timestamp = new Date(point.ts).getTime();
      return !Number.isFinite(timestamp) || istanbulDateKey(timestamp) !== latestDay;
    }),
    latestSnapshot,
  ];
}

/** Yillik seride icinde bulunulan haftayi tek canli snapshot ile temsil eder. */
export function mergeLatestSnapshotIntoWeeklyHistory(
  history: PortfolioValueSnapshotPoint[],
  latestSnapshot: PortfolioValueSnapshotPoint | undefined,
): PortfolioValueSnapshotPoint[] {
  if (!latestSnapshot) {
    return history;
  }

  const latestTimestamp = new Date(latestSnapshot.ts).getTime();
  if (!Number.isFinite(latestTimestamp)) {
    return history;
  }

  const latestWeek = weekStartKey(istanbulDateKey(latestTimestamp));
  return [
    ...history.filter((point) => {
      const timestamp = new Date(point.ts).getTime();
      return !Number.isFinite(timestamp)
        || weekStartKey(istanbulDateKey(timestamp)) !== latestWeek;
    }),
    latestSnapshot,
  ];
}

function weekStartKey(dateKey: string): string {
  const date = new Date(`${dateKey}T00:00:00Z`);
  const daysSinceMonday = (date.getUTCDay() + 6) % 7;
  date.setUTCDate(date.getUTCDate() - daysSinceMonday);
  return date.toISOString().slice(0, 10);
}

/**
 * Doneme uygun, yalnizca TAMAMLANMIS portfoy mumlarini uretir.
 *
 * 1G: 5 dakikalik snapshot'lardan 30 dakikalik mum.
 * 1H/1A: ayni snapshot'lardan gunluk mum.
 * 1Y: backend'in gunluk toplamlarindan haftalik mum.
 */
export function buildCompletedPortfolioCandles(
  points: PortfolioValueSnapshotPoint[],
  range: PerformanceRange,
  now = Date.now(),
): CandlePoint[] {
  const halfHour = 30 * 60 * 1_000;
  const todayKey = istanbulDateKey(now);
  const currentWeekKey = weekStartKey(todayKey);
  const buckets = new Map<string, Array<{ timestamp: number; value: number }>>();

  points.forEach((point) => {
    const timestamp = new Date(point.ts).getTime();
    if (!Number.isFinite(timestamp)) {
      return;
    }

    const dateKey = istanbulDateKey(timestamp);
    const bucketKey = range === "1G"
      ? String(Math.floor(timestamp / halfHour) * halfHour)
      : range === "1Y"
        ? weekStartKey(dateKey)
        : dateKey;
    const bucket = buckets.get(bucketKey) ?? [];
    bucket.push({ timestamp, value: point.total_value_try });
    buckets.set(bucketKey, bucket);
  });

  return [...buckets.entries()]
    .sort(([left], [right]) => left.localeCompare(right, "en"))
    .flatMap(([bucketKey, values]) => {
      const complete = range === "1G"
        ? Number(bucketKey) + halfHour <= now
        : range === "1Y"
          ? bucketKey < currentWeekKey
          : bucketKey < todayKey;
      if (!complete || values.length === 0) {
        return [];
      }

      const completedValues = values
        .sort((left, right) => left.timestamp - right.timestamp)
        .map((item) => item.value);
      const open = completedValues[0];
      const close = completedValues.at(-1) ?? open;
      const high = Math.max(...completedValues);
      const low = Math.min(...completedValues);
      return [{
        ts: range === "1G"
          ? new Date(Number(bucketKey)).toISOString()
          : `${bucketKey}T00:00:00+03:00`,
        open,
        high,
        low,
        close,
        range: [low, high] as [number, number],
      }];
    });
}

export function buildCompletedHalfHourlyCandles(
  points: PortfolioValueSnapshotPoint[],
): CandlePoint[] {
  return buildCompletedPortfolioCandles(points, "1G");
}

function paddedDomain(minimum: number, maximum: number): [number, number] {
  const spread = maximum - minimum;
  const padding = Math.max(spread * 0.12, Math.abs(maximum) * 0.0005, 1);
  return [minimum - padding, maximum + padding];
}

export function buildChronologicalPortfolioPoints(
  points: PortfolioValueSnapshotPoint[],
  conversionDivisor: number,
): PortfolioValueSnapshotPoint[] {
  return [...points]
    .filter((point) => !Number.isNaN(new Date(point.ts).getTime()))
    .sort((left, right) => new Date(left.ts).getTime() - new Date(right.ts).getTime())
    .map((point) => ({
      ...point,
      holdings_value_try: point.holdings_value_try / conversionDivisor,
      cash_value_try: point.cash_value_try / conversionDivisor,
      total_value_try: point.total_value_try / conversionDivisor,
    }));
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
  range,
  periodChangeTry,
  periodChangePct,
  performancePoints,
  candleSourcePoints,
  currentTotalTry,
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
  range: PerformanceRange;
  /** Donem kar/zarari - grafigin ustundeki yuzde bundan turetilir. */
  periodChangeTry: number | null;
  periodChangePct: number | null;
  //: 1G/1H/1A'da scheduler'in olctugu gercek snapshot'lar, 1Y'de yeniden
  //: kurulan seri ayni bicime cevrilerek gelir (bkz. dashboard).
  performancePoints: PortfolioValueSnapshotPoint[];
  /** Mum icin ham kaynak: 1G/1H/1A snapshot, 1Y gunluk performans serisi. */
  candleSourcePoints: PortfolioValueSnapshotPoint[];
  /** Tum donemlerde kartlarla ortak kullanilan son snapshot toplami. */
  currentTotalTry: number | null;
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
    () => buildChronologicalPortfolioPoints(performancePoints, conversionDivisor),
    [conversionDivisor, performancePoints],
  );
  const convertedCandleSource = useMemo(
    () => buildChronologicalPortfolioPoints(candleSourcePoints, conversionDivisor),
    [candleSourcePoints, conversionDivisor],
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
  const current = currentTotalTry != null
    ? currentTotalTry / conversionDivisor
    : chartPoints.at(-1)?.total_value_try ?? totalValue;
  // Yuzde, ILK/SON NOKTA FARKINDAN degil backend'in donem kar/zararindan
  // gelir. Ikisi ayni degildir: donem icinde alim yapildiysa portfoy degeri
  // artar ama bu KAR degil, yatirilan paradir - ham fark "+%36" gibi
  // gercek disi bir getiri gosterirdi. Backend alim maliyetini dusuyor.
  // Donem verisi henuz gelmediyse ham farka duseriz (grafik bos kalmasin).
  const change = periodChangeTry ?? current - first;
  const changePct = periodChangePct ?? (first > 0 ? ((current - first) / first) * 100 : 0);
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
    () => buildCompletedPortfolioCandles(convertedCandleSource, range),
    [convertedCandleSource, range],
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
    <Card className="h-full">
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
              ? `${RANGE_SUBTITLES[range][language]} · ${displayCurrencyLabel} ${language === "tr" ? "bazlı" : "based"}`
              : mode === "candlestick"
                ? `${CANDLE_SUBTITLES[range][language]} · ${displayCurrencyLabel} ${language === "tr" ? "bazlı" : "based"}`
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
        className={`portfolio-chart-content mt-3 h-[420px] overflow-y-auto pr-1 ${mode === "pie" ? "lg:overflow-hidden" : ""}`}
      >
        {mode === "pie" ? (
          <div className="grid min-h-full items-center gap-8 lg:h-full lg:min-h-0 lg:grid-cols-[minmax(280px,.78fr)_minmax(0,1.35fr)]">
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

            <div className="min-w-0 lg:flex lg:h-full lg:min-h-0 lg:flex-col">
              <h3 className="mb-2 text-sm font-semibold app-heading">
                {language === "tr" ? "Varlıklar" : "Assets"}
              </h3>
              <div className="divide-y rounded-md border app-border app-border-soft lg:min-h-0 lg:flex-1 lg:overflow-y-auto lg:overscroll-contain">
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
            {language === "tr"
              ? `${RANGE_SUBTITLES[range].tr} için henüz yeterli gerçek fiyat geçmişi oluşmadı.`
              : `There is not enough real price history for ${RANGE_SUBTITLES[range].en.toLowerCase()} yet.`}
          </div>
        ) : mode === "candlestick" && candlePoints.length === 0 ? (
          <div className="grid min-h-[356px] place-items-center px-6 text-center text-sm app-muted">
            {range === "1G"
              ? language === "tr"
                ? "Henüz tamamlanmış bir 30 dakikalık portföy aralığı oluşmadı."
                : "A completed 30-minute portfolio interval is not available yet."
              : range === "1Y"
                ? language === "tr"
                  ? "Henüz tamamlanmış bir haftalık portföy aralığı oluşmadı."
                  : "A completed weekly portfolio interval is not available yet."
                : language === "tr"
                  ? "Henüz tamamlanmış bir günlük portföy aralığı oluşmadı."
                  : "A completed daily portfolio interval is not available yet."}
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
                    tickFormatter={(value) => formatTime(value, language, range)}
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
                            {formatTime(String(label), language, range)}
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
                    tickFormatter={(value) => formatTime(value, language, range)}
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
                    labelFormatter={(label) => formatTime(String(label), language, range)}
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
