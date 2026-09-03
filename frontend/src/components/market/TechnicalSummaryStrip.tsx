"use client";

import type { TechnicalResponse } from "../../models/market";
import {
  SUMMARY_COLORS,
  SUMMARY_LABELS,
  formatDataTime,
  scorePosition,
} from "./technicalFormat";

const SCALE_STEPS = ["Güçlü Sat", "Sat", "Nötr", "Al", "Güçlü Al"];

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
        <div className="text-xs font-semibold uppercase tracking-wide app-muted">
          Teknik Analiz
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
        <div className="text-xs font-semibold uppercase tracking-wide app-muted">
          Teknik Analiz
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
