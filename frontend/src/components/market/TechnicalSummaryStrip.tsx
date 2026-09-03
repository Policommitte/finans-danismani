"use client";

import type { TechnicalResponse } from "../../models/market";
import {
  SUMMARY_COLORS,
  SUMMARY_LABELS,
  formatDataTime,
  scorePosition,
} from "./technicalFormat";

const SCALE_STEPS = ["Güçlü Sat", "Sat", "Nötr", "Al", "Güçlü Al"];

const TECHNICAL_INFO_TEXT =
  "Teknik göstergeler, geçmiş fiyat hareketlerinden hesaplanan istatistiksel " +
  "ölçümlerdir (RSI, MACD, hareketli ortalamalar gibi). Haber veya şirket " +
  "verisi içermez; yalnızca fiyat hareketine dayanır.";

/** Baslik yanindaki (i) ikonu - hover/focus'ta aciklama balonu gosterir. */
function InfoTooltip({ text }: { text: string }) {
  return (
    <span className="group/info relative inline-flex">
      <button
        type="button"
        aria-label="Teknik gösterge açıklaması"
        className="flex h-3.5 w-3.5 items-center justify-center rounded-full app-muted transition hover:opacity-80"
      >
        <svg
          width="13"
          height="13"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <circle cx="12" cy="12" r="10" />
          <line x1="12" y1="16" x2="12" y2="12" />
          <line x1="12" y1="8" x2="12.01" y2="8" />
        </svg>
      </button>
      <span
        role="tooltip"
        className="pointer-events-none absolute left-0 top-full z-20 mt-1.5 w-64 max-w-[80vw] rounded-lg border app-border app-surface px-3 py-2 text-[11px] font-normal normal-case tracking-normal leading-relaxed app-heading opacity-0 shadow-lg transition group-hover/info:opacity-100 group-focus-within/info:opacity-100"
      >
        {text}
      </span>
    </span>
  );
}

/**
 * Teknik görünümün özet şeridi: sonuç sınıfı, sayaçlar ve veri künyesi.
 *
 * Gösterge tabloları burada DEĞİL, "Ayrıntılar" ile açılan ikinci görünümde
 * durur - modalın boyu sabit kalsın diye.
 */
export function TechnicalSummaryStrip({
  data,
  loading,
  onShowDetail,
}: {
  data: TechnicalResponse | null;
  loading: boolean;
  onShowDetail: () => void;
}) {
  if (loading) {
    return (
      <div className="mt-4 rounded-xl border app-border app-surface px-3.5 py-3 text-sm app-muted">
        Teknik analiz hesaplanıyor…
      </div>
    );
  }

  if (!data) {
    return null;
  }

  if (!data.sufficient || !data.summary) {
    return (
      <div className="mt-4 rounded-xl border app-border bg-[var(--color-surface-muted)] px-3.5 py-3">
        <div className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide app-muted">
          <span>Teknik Analiz</span>
          <InfoTooltip text={TECHNICAL_INFO_TEXT} />
        </div>
        <p className="mt-1 text-sm app-heading">Analiz için veri yetersiz.</p>
        {data.reason && <p className="mt-1 text-xs app-muted">{data.reason}</p>}
      </div>
    );
  }

  const { summary } = data;
  const accent = SUMMARY_COLORS[summary.label];

  return (
    <div className="mt-4 rounded-xl border app-border app-surface px-3.5 py-3">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide app-muted">
          <span>Teknik Analiz</span>
          <InfoTooltip text={TECHNICAL_INFO_TEXT} />
        </div>
        <span
          className="rounded-full px-2.5 py-1 text-xs font-bold"
          style={{
            background: `color-mix(in srgb, ${accent} 15%, var(--color-surface))`,
            color: accent,
          }}
        >
          {SUMMARY_LABELS[summary.label]}
        </span>
      </div>

      <div className="mt-2.5">
        <div className="relative h-1.5 rounded-full bg-[var(--color-surface-muted)]">
          <div
            className="absolute -top-1 h-3.5 w-3.5 -translate-x-1/2 rounded-full border-2 border-[var(--color-surface)]"
            style={{ left: `${scorePosition(summary.score)}%`, background: accent }}
            aria-hidden="true"
          />
        </div>
        <div className="mt-1.5 flex justify-between text-[10px] app-muted">
          {SCALE_STEPS.map((step) => (
            <span key={step}>{step}</span>
          ))}
        </div>
      </div>

      <div className="mt-2.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs">
        <span className="app-success font-semibold">{summary.buy} Al</span>
        <span className="app-muted font-semibold">{summary.neutral} Nötr</span>
        <span className="app-danger font-semibold">{summary.sell} Sat</span>
        <button
          type="button"
          onClick={onShowDetail}
          className="ml-auto rounded-lg border app-border px-2.5 py-1 text-xs font-semibold app-heading transition hover:opacity-80"
        >
          Ayrıntılar
        </button>
      </div>

      <p className="mt-2 text-[11px] app-muted">
        Günlük mumlar · {data.candle_count} mum · veri: {formatDataTime(data.last_candle_ts)}
      </p>
    </div>
  );
}
