"use client";

import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import {
  CandlestickSeries,
  ColorType,
  CrosshairMode,
  HistogramSeries,
  LineSeries,
  LineStyle,
  TickMarkType,
  createChart,
  type Time,
  type UTCTimestamp,
} from "lightweight-charts";
import type {
  CandlesResponse,
  ChartInterval,
  ChartRange,
  Forecast,
} from "../../models/market";
import Card from "../ui/Card";
import { useLanguage } from "../../contexts/LanguageContext";

type ChartKind = "line" | "candles";

const MARKET_TIME_ZONE = "Europe/Istanbul";
function createChartFormatters(locale: string) {
  const options = { timeZone: MARKET_TIME_ZONE } as const;
  return {
    dateTime: new Intl.DateTimeFormat(locale, { ...options, day: "2-digit", month: "short", year: "2-digit", hour: "2-digit", minute: "2-digit", hourCycle: "h23" }),
    date: new Intl.DateTimeFormat(locale, { ...options, day: "2-digit", month: "short", year: "2-digit" }),
    time: new Intl.DateTimeFormat(locale, { ...options, hour: "2-digit", minute: "2-digit", hourCycle: "h23" }),
    day: new Intl.DateTimeFormat(locale, { ...options, day: "2-digit", month: "short" }),
    month: new Intl.DateTimeFormat(locale, { ...options, month: "short" }),
    year: new Intl.DateTimeFormat(locale, { ...options, year: "numeric" }),
  };
}

type ChartFormatters = ReturnType<typeof createChartFormatters>;

function chartTimeToDate(time: Time): Date {
  if (typeof time === "number") {
    return new Date(time * 1000);
  }
  if (typeof time === "string") {
    return new Date(`${time}T00:00:00Z`);
  }
  return new Date(Date.UTC(time.year, time.month - 1, time.day));
}

function formatChartTick(time: Time, tickMarkType: TickMarkType, formatters: ChartFormatters): string {
  const date = chartTimeToDate(time);
  if (tickMarkType === TickMarkType.Year) return formatters.year.format(date);
  if (tickMarkType === TickMarkType.Month) return formatters.month.format(date);
  if (tickMarkType === TickMarkType.DayOfMonth) return formatters.day.format(date);
  return formatters.time.format(date);
}

const INTERVALS: Array<{ value: ChartInterval; tr: string; en: string }> = [
  { value: "5m", tr: "5dk", en: "5m" },
  { value: "15m", tr: "15dk", en: "15m" },
  { value: "1h", tr: "1s", en: "1h" },
  { value: "4h", tr: "4s", en: "4h" },
  { value: "1d", tr: "1g", en: "1d" },
];

const RANGES: Array<{ value: ChartRange; tr: string; en: string }> = [
  { value: "1d", tr: "1G", en: "1D" },
  { value: "5d", tr: "5G", en: "5D" },
  { value: "1m", tr: "1A", en: "1M" },
  { value: "3m", tr: "3A", en: "3M" },
  { value: "1y", tr: "1Y", en: "1Y" },
];

const MARKET_UTC_OFFSET_SECONDS = 3 * 60 * 60;

function marketDateParts(timestamp: number) {
  const localDate = new Date((timestamp + MARKET_UTC_OFFSET_SECONDS) * 1000);
  return {
    year: localDate.getUTCFullYear(),
    month: localDate.getUTCMonth() + 1,
    day: localDate.getUTCDate(),
  };
}

function dateKey(year: number, month: number, day: number): string {
  return `${year.toString().padStart(4, "0")}-${month.toString().padStart(2, "0")}-${day.toString().padStart(2, "0")}`;
}

function marketDateKey(timestamp: number): string {
  const { year, month, day } = marketDateParts(timestamp);
  return dateKey(year, month, day);
}

function calendarCutoffKey(timestamp: number, monthsBack: number): string {
  const current = marketDateParts(timestamp);
  const monthIndex = current.year * 12 + current.month - 1 - monthsBack;
  const year = Math.floor(monthIndex / 12);
  const monthIndexInYear = ((monthIndex % 12) + 12) % 12;
  const month = monthIndexInYear + 1;
  const lastDay = new Date(Date.UTC(year, month, 0)).getUTCDate();
  return dateKey(year, month, Math.min(current.day, lastDay));
}

export function visibleRangeStart(
  candles: CandlesResponse["candles"],
  range: ChartRange,
): number {
  if (range === "1d" || range === "5d") {
    const sessionCount = range === "1d" ? 1 : 5;
    const sessionDates = Array.from(new Set(candles.map((candle) => marketDateKey(candle.time))));
    const firstSession = sessionDates[Math.max(0, sessionDates.length - sessionCount)];
    return candles.find((candle) => marketDateKey(candle.time) === firstSession)?.time
      ?? candles[0].time;
  }

  const monthsBack = range === "1m" ? 1 : range === "3m" ? 3 : 12;
  const cutoff = calendarCutoffKey(candles[candles.length - 1].time, monthsBack);
  return candles.find((candle) => marketDateKey(candle.time) >= cutoff)?.time
    ?? candles[0].time;
}

/**
 * Tahmin bu grafige cizilebilir mi?
 *
 * SADECE GUNLUK (`1d`) grafikte. Tahmin gunluk mumdan uretilir ve 21 IS GUNU
 * ilerisini gosterir; 5dk'lik bir grafige eklenirse zaman ekseni 21 gunluk
 * bir bosluga yayilir ve gercek veri okunamaz hale gelir.
 */
const FORECAST_UP_COLOR = "#26a69a";
const FORECAST_DOWN_COLOR = "#ef5350";

/**
 * Colors every forecast point by its direction relative to the previous
 * point, so rising stretches render green and falling stretches red.
 */
export function colorForecastByDirection<T extends { value: number }>(
  points: T[],
): Array<T & { color: string }> {
  return points.map((point, index) => {
    const previous = index > 0 ? points[index - 1].value : point.value;
    return {
      ...point,
      color: point.value >= previous ? FORECAST_UP_COLOR : FORECAST_DOWN_COLOR,
    };
  });
}

function forecastCizilebilir(
  forecast: Forecast | null | undefined,
  interval: ChartInterval,
): forecast is Forecast {
  return Boolean(forecast && forecast.noktalar.length > 0 && interval === "1d");
}

/** `YYYY-AA-GG` -> lightweight-charts UTC saniye damgasi. */
function tariheDamga(tarih: string): UTCTimestamp {
  return (Date.parse(`${tarih}T00:00:00Z`) / 1000) as UTCTimestamp;
}

type Props = {
  data: CandlesResponse;
  /**
   * Ileriye donuk tahmin. `null`/`undefined` ise kesikli cizgi HIC cizilmez -
   * ozellik backend'de kapali olabilir (bkz. `marketService.getForecast`).
   *
   * ⚠️ YALNIZCA GUNLUK grafikte anlamlidir: tahmin gunluk mumla uretilir,
   * 5dk'lik bir grafige 21 GUNLUK tahmin cizmek olcegi tamamen bozar.
   * Bu kontrol `forecastCizilebilir()` icinde yapilir.
   */
  forecast?: Forecast | null;
  assetClass?: string;
  currency?: string;
  interval: ChartInterval;
  range: ChartRange;
  rangePresetActive: boolean;
  rangePresetRevision: number;
  onIntervalChange: (interval: ChartInterval) => void;
  onRangeChange: (range: ChartRange) => void;
  onRangePresetExit: () => void;
  loading?: boolean;
  children?: ReactNode;
};

export function PriceHistoryChart({
  data,
  forecast,
  assetClass,
  currency,
  interval,
  range,
  rangePresetActive,
  rangePresetRevision,
  onIntervalChange,
  onRangeChange,
  onRangePresetExit,
  loading = false,
  children,
}: Props) {
  const { language } = useLanguage();
  const locale = language === "tr" ? "tr-TR" : "en-US";
  const chartFormatters = useMemo(() => createChartFormatters(locale), [locale]);
  const containerRef = useRef<HTMLDivElement>(null);
  const [kind, setKind] = useState<ChartKind>("candles");
  const precision = assetClass === "FOREX" ? 4 : 2;
  const latest = data.candles.at(-1);
  const hasVolume = data.candles.some((candle) => candle.volume !== null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container || data.candles.length === 0) return;

    const styles = getComputedStyle(document.documentElement);
    const textColor = styles.getPropertyValue("--color-muted").trim() || "#64748b";
    const gridColor = styles.getPropertyValue("--color-chart-grid").trim() || "#e2e8f0";
    const borderColor = styles.getPropertyValue("--color-border").trim() || "#e2e8f0";
    const primaryColor = styles.getPropertyValue("--color-primary").trim() || "#2563eb";
    const minMove = 10 ** -precision;
    const priceFormatter = (value: number) => value.toLocaleString(locale, {
      minimumFractionDigits: precision,
      maximumFractionDigits: precision,
    });

    const chart = createChart(container, {
      width: container.clientWidth,
      height: container.clientHeight,
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor,
        fontFamily: "inherit",
        attributionLogo: false,
      },
      grid: {
        vertLines: { color: gridColor },
        horzLines: { color: gridColor },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: { color: textColor, width: 1, style: 2, labelBackgroundColor: primaryColor },
        horzLine: { color: textColor, width: 1, style: 2, labelBackgroundColor: primaryColor },
      },
      localization: {
        locale,
        priceFormatter,
        timeFormatter: (time: Time) => {
          const date = chartTimeToDate(time);
          return data.interval === "1d"
            ? chartFormatters.date.format(date)
            : chartFormatters.dateTime.format(date);
        },
      },
      rightPriceScale: { borderColor, scaleMargins: { top: 0.12, bottom: 0.12 } },
      timeScale: {
        borderColor,
        timeVisible: data.interval !== "1d",
        secondsVisible: false,
        rightOffset: 3,
        barSpacing: kind === "candles" ? 10 : 7,
        minBarSpacing: 2,
        tickMarkFormatter: (time: Time, tickMarkType: TickMarkType) => formatChartTick(time, tickMarkType, chartFormatters),
      },
      handleScroll: true,
      handleScale: true,
    });

    let updateLineColor = (_color: string) => {};

    if (kind === "candles") {
      const upColor = "#26a69a";
      const downColor = "#ef5350";
      const series = chart.addSeries(CandlestickSeries, {
        upColor,
        downColor,
        borderUpColor: upColor,
        borderDownColor: downColor,
        wickUpColor: upColor,
        wickDownColor: downColor,
        priceLineVisible: true,
        lastValueVisible: true,
        priceFormat: { type: "price", precision, minMove },
      });
      series.setData(data.candles.map((candle) => ({
        time: candle.time as UTCTimestamp,
        open: candle.open,
        high: candle.high,
        low: candle.low,
        close: candle.close,
      })));

    } else {
      const series = chart.addSeries(LineSeries, {
        color: primaryColor,
        lineWidth: 2,
        crosshairMarkerVisible: false,
        priceLineVisible: true,
        lastValueVisible: true,
        priceFormat: { type: "price", precision, minMove },
      });
      series.setData(data.candles.map((candle) => ({
        time: candle.time as UTCTimestamp,
        value: candle.close,
      })));
      updateLineColor = (color: string) => series.applyOptions({ color });
    }

    // --- TAHMIN: gri kesikli cizgi + belirsizlik bandi ---
    //
    // Bant, cizgiden ONCE eklenir: lightweight-charts serileri ekleme
    // sirasina gore ust uste cizer, sonra eklenen ustte kalir. Bant once
    // gelmezse dolgu, kesikli cizgiyi orter.
    if (forecastCizilebilir(forecast, data.interval)) {
      const sonGercek = data.candles.at(-1);

      // Bant SINIRLARI: iki ince kesikli cizgi.
      //
      // DOLGULU bant DENENDI VE VAZGECILDI: lightweight-charts'ta hazir bir
      // "band" serisi yok, taklidi ancak alt siniri ARKA PLAN RENGIYLE
      // doldurarak yapiliyor - ama bu grafigin arka plani `transparent`
      // (tema degisiminde saydam kalsin diye). Saydam zeminde o numara
      // calismaz, alt dolgu grafigin altindaki her seyi de orterdi.
      // Iki ince cizgi hem calisir hem kullanicinin istedigi "gri kesikli"
      // gorunumle tutarlidir.
      // Ust bant (yukselis senaryosu) yesil, alt bant (dusus senaryosu)
      // kirmizi; ikisi de kalin noktali cizgi - eski gri cizgiler cok silikti.
      const bantCizgisi = (color: string) =>
        chart.addSeries(LineSeries, {
          color,
          lineWidth: 2,
          lineStyle: LineStyle.Dotted,
          priceLineVisible: false,
          lastValueVisible: false,
          crosshairMarkerVisible: false,
          priceFormat: { type: "price", precision, minMove },
        });
      const bantUst = bantCizgisi(FORECAST_UP_COLOR);
      const bantAlt = bantCizgisi(FORECAST_DOWN_COLOR);

      // Bant ve cizgi SON GERCEK NOKTADAN baslar - aksi halde gercek seri
      // ile tahmin arasinda gorsel bir kopukluk olusur.
      const kopru = sonGercek
        ? [{ time: sonGercek.time as UTCTimestamp, value: sonGercek.close }]
        : [];

      bantUst.setData([
        ...kopru,
        ...forecast.noktalar.map((n) => ({ time: tariheDamga(n.tarih), value: n.ust })),
      ]);
      bantAlt.setData([
        ...kopru,
        ...forecast.noktalar.map((n) => ({ time: tariheDamga(n.tarih), value: n.alt })),
      ]);

      // Tahmin cizgisi yon renkli NOKTALI cizgi: yukselen parcalar yesil,
      // dusen parcalar kirmizi (mum renkleriyle ayni). lightweight-charts'ta
      // bir noktanin `color`'u, ONCEKI noktadan o noktaya cizilen parcayi
      // boyar; bu yuzden her nokta bir onceki degerle karsilastirilir.
      const forecastLine = chart.addSeries(LineSeries, {
        color: FORECAST_UP_COLOR,
        lineWidth: 3,
        lineStyle: LineStyle.Dotted,
        priceLineVisible: false,
        lastValueVisible: false,
        crosshairMarkerVisible: false,
        priceFormat: { type: "price", precision, minMove },
      });
      forecastLine.setData(
        colorForecastByDirection([
          ...kopru,
          ...forecast.noktalar.map((n) => ({ time: tariheDamga(n.tarih), value: n.deger })),
        ]),
      );
    }

    if (hasVolume) {
      const volumeSeries = chart.addSeries(HistogramSeries, {
        priceFormat: { type: "volume" },
        priceScaleId: "",
        priceLineVisible: false,
        lastValueVisible: false,
      });
      volumeSeries.priceScale().applyOptions({ scaleMargins: { top: 0.8, bottom: 0 } });
      volumeSeries.setData(data.candles.map((candle) => ({
        time: candle.time as UTCTimestamp,
        value: candle.volume ?? 0,
        color: candle.close >= candle.open ? "rgba(38, 166, 154, 0.32)" : "rgba(239, 83, 80, 0.32)",
      })));
    }

    const applyChartTheme = () => {
      const themeStyles = getComputedStyle(document.documentElement);
      const nextTextColor = themeStyles.getPropertyValue("--color-muted").trim() || "#64748b";
      const nextGridColor = themeStyles.getPropertyValue("--color-chart-grid").trim() || "#e2e8f0";
      const nextBorderColor = themeStyles.getPropertyValue("--color-border").trim() || "#e2e8f0";
      const nextPrimaryColor = themeStyles.getPropertyValue("--color-primary").trim() || "#2563eb";

      chart.applyOptions({
        layout: { textColor: nextTextColor },
        grid: {
          vertLines: { color: nextGridColor },
          horzLines: { color: nextGridColor },
        },
        crosshair: {
          vertLine: { color: nextTextColor, labelBackgroundColor: nextPrimaryColor },
          horzLine: { color: nextTextColor, labelBackgroundColor: nextPrimaryColor },
        },
        rightPriceScale: { borderColor: nextBorderColor },
        timeScale: { borderColor: nextBorderColor },
      });
      updateLineColor(nextPrimaryColor);
    };
    const themeObserver = new MutationObserver(applyChartTheme);
    themeObserver.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["data-theme"],
    });

    const firstTime = data.candles[0].time;
    // ⚠️ GORUNUR ARALIK TAHMINI DE KAPSAMALI. Eskiden `to` son GERCEK
    // muma sabitleniyordu; tahmin serisi eklenince noktalari o sinirin
    // SAGINDA kaliyor ve kesikli cizgi hic gorunmuyordu (canli testte
    // birebir yasandi: istek 200 donuyor, veri geliyor, ekranda hicbir
    // sey yok). Tahmin varsa aralik onun son gunune kadar uzatilir.
    const sonGercekZaman = data.candles[data.candles.length - 1].time;
    const tahminSonZaman = forecastCizilebilir(forecast, data.interval)
      ? tariheDamga(forecast.noktalar[forecast.noktalar.length - 1].tarih)
      : sonGercekZaman;
    const lastTime = Math.max(sonGercekZaman, tahminSonZaman);
    const visibleFrom = Math.max(firstTime, visibleRangeStart(data.candles, data.range));
    if (visibleFrom < lastTime) {
      chart.timeScale().setVisibleRange({
        from: visibleFrom as UTCTimestamp,
        to: lastTime as UTCTimestamp,
      });
    } else {
      chart.timeScale().fitContent();
    }

    let userChangingVisibleRange = false;
    let interactionEndTimer: number | undefined;
    const beginVisibleRangeInteraction = () => {
      userChangingVisibleRange = true;
      if (interactionEndTimer !== undefined) {
        window.clearTimeout(interactionEndTimer);
      }
    };
    const endVisibleRangeInteraction = () => {
      interactionEndTimer = window.setTimeout(() => {
        userChangingVisibleRange = false;
      }, 0);
    };
    const handleVisibleRangeChange = () => {
      if (userChangingVisibleRange) {
        onRangePresetExit();
      }
    };

    container.addEventListener("pointerdown", beginVisibleRangeInteraction, true);
    window.addEventListener("pointerup", endVisibleRangeInteraction, true);
    container.addEventListener("wheel", beginVisibleRangeInteraction, { capture: true, passive: true });
    container.addEventListener("wheel", endVisibleRangeInteraction, { capture: true, passive: true });
    chart.timeScale().subscribeVisibleLogicalRangeChange(handleVisibleRangeChange);

    const observer = new ResizeObserver(([entry]) => {
      chart.applyOptions({ width: Math.floor(entry.contentRect.width) });
    });
    observer.observe(container);

    return () => {
      container.removeEventListener("pointerdown", beginVisibleRangeInteraction, true);
      window.removeEventListener("pointerup", endVisibleRangeInteraction, true);
      container.removeEventListener("wheel", beginVisibleRangeInteraction, true);
      container.removeEventListener("wheel", endVisibleRangeInteraction, true);
      chart.timeScale().unsubscribeVisibleLogicalRangeChange(handleVisibleRangeChange);
      if (interactionEndTimer !== undefined) {
        window.clearTimeout(interactionEndTimer);
      }
      themeObserver.disconnect();
      observer.disconnect();
      chart.remove();
    };
    // `forecast` bagimliligi ZORUNLU: tahmin sonradan (ayri bir istekle)
    // gelir; listede olmazsa grafik yeniden cizilmez ve kesikli cizgi
    // ancak bir sonraki aralik/sembol degisiminde belirir.
  }, [chartFormatters, data.candles, data.interval, data.range, forecast, hasVolume, kind, locale, onRangePresetExit, precision, rangePresetRevision]);

  const latestPrice = latest?.close.toLocaleString(locale, {
    minimumFractionDigits: precision,
    maximumFractionDigits: precision,
  });

  return (
    <Card className="overflow-hidden">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex items-baseline gap-3">
            <h2 className="text-lg font-semibold app-heading">{data.symbol}</h2>
            {latestPrice && (
              <strong className="text-lg app-heading">{latestPrice} {currency}</strong>
            )}
          </div>
          <p className="mt-1 text-xs app-muted">
            {language === "tr" ? "Doğrulanmış fiyat geçmişi · Yakınlaştırmak için kaydırın" : "Verified price history · Scroll to zoom"}
          </p>
        </div>

        <div className="flex rounded-lg app-card-muted p-1" aria-label={language === "tr" ? "Grafik türü" : "Chart type"}>
          {(["line", "candles"] as const).map((value) => (
            <button
              key={value}
              type="button"
              onClick={() => setKind(value)}
              className={`rounded-md px-3 py-1.5 text-xs font-semibold transition ${kind === value ? "bg-[#454466] text-white" : "app-muted"}`}
            >
              {value === "line" ? (language === "tr" ? "Çizgi" : "Line") : (language === "tr" ? "Mum" : "Candles")}
            </button>
          ))}
        </div>
      </div>

      <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-y app-border py-2">
        <div className="flex flex-wrap gap-1" aria-label={language === "tr" ? "Mum aralığı" : "Candle interval"}>
          {INTERVALS.map((item) => (
            <button
              key={item.value}
              type="button"
              onClick={() => onIntervalChange(item.value)}
              className={`rounded-md px-2.5 py-1.5 text-xs font-semibold transition ${interval === item.value ? "bg-emerald-600 text-white" : "app-muted hover:app-card-muted"}`}
            >
              {item[language]}
            </button>
          ))}
        </div>
        <div className="flex flex-wrap gap-1" aria-label={language === "tr" ? "Tarih aralığı" : "Date range"}>
          {RANGES.map((item) => (
            <button
              key={item.value}
              type="button"
              onClick={() => onRangeChange(item.value)}
              className={`rounded-md px-2.5 py-1.5 text-xs font-semibold transition ${rangePresetActive && range === item.value ? "bg-[#454466] text-white" : "app-muted hover:app-card-muted"}`}
            >
              {item[language]}
            </button>
          ))}
        </div>
      </div>

      <div className="relative mt-3 overflow-hidden" aria-busy={loading}>
        {data.candles.length > 0 ? (
          <div
            ref={containerRef}
            className={`h-[320px] w-full transition duration-200 sm:h-[390px] ${loading ? "pointer-events-none scale-[0.995] blur-sm" : ""}`}
            role="img"
            aria-label={`${data.symbol} ${language === "tr" ? "interaktif fiyat grafiği" : "interactive price chart"}`}
          />
        ) : (
          <div className={`grid h-64 place-items-center text-sm app-muted transition duration-200 ${loading ? "blur-sm" : ""}`}>
            {language === "tr" ? "Bu zaman aralığında doğrulanmış fiyat verisi bulunamadı." : "No verified price data was found for this period."}
          </div>
        )}

        {loading && (
          <div
            className="absolute inset-0 z-10 grid place-items-center"
            role="status"
            aria-label={language === "tr" ? "Grafik verileri güncelleniyor" : "Updating chart data"}
          >
            <div className="relative flex flex-col items-center gap-4 rounded-2xl border app-border bg-[var(--color-surface)] px-8 py-6 shadow-lg">
              <span
                aria-hidden="true"
                className="block h-9 w-32 bg-[var(--color-heading)] [mask-image:url('/polifin-logo-clean.svg')] [mask-position:center] [mask-repeat:no-repeat] [mask-size:contain]"
              />
              <span
                aria-hidden="true"
                className="h-7 w-7 animate-spin rounded-full border-[3px] border-[var(--color-border)] border-t-[var(--color-cta)]"
              />
              <span className="sr-only">{language === "tr" ? "Grafik verileri güncelleniyor" : "Updating chart data"}</span>
            </div>
          </div>
        )}
      </div>

      {kind === "candles" && !hasVolume && (
        <p className="mt-2 text-xs app-muted">
          {language === "tr"
            ? "Mumlar mevcut doğrulanmış fiyat noktalarından oluşturulur; hacim verisi henüz bulunmuyor."
            : "Candles are built from available verified price points; volume data is not available yet."}
        </p>
      )}
      {children && <div className="mt-3 border-t app-border pt-4">{children}</div>}
    </Card>
  );
}
