"use client";

import type { TechnicalResponse, TechnicalSignal, TechnicalSummary } from "../../models/market";
import {
  SIGNAL_COLORS,
  SIGNAL_LABELS,
  SUMMARY_COLORS,
  SUMMARY_LABELS,
  formatDataTime,
  formatIndicatorValue,
} from "./technicalFormat";

function SignalBadge({ signal }: { signal: TechnicalSignal }) {
  const color = SIGNAL_COLORS[signal];
  return (
    <span
      className="rounded-full px-2 py-0.5 text-xs font-semibold"
      style={{ background: `color-mix(in srgb, ${color} 14%, transparent)`, color }}
    >
      {SIGNAL_LABELS[signal]}
    </span>
  );
}

function SectionHeader({ title, summary }: { title: string; summary: TechnicalSummary | null }) {
  return (
    <div className="flex items-center justify-between gap-2 px-1 pb-1.5">
      <h3 className="text-sm font-bold app-heading">{title}</h3>
      {summary && (
        <span className="text-xs font-semibold" style={{ color: SUMMARY_COLORS[summary.label] }}>
          {SUMMARY_LABELS[summary.label]} · {summary.buy}/{summary.neutral}/{summary.sell}
        </span>
      )}
    </div>
  );
}

/** Gösterge ve hareketli ortalama tabloları - modalın ikinci görünümü. */
export function TechnicalDetailView({
  data,
  onBack,
}: {
  data: TechnicalResponse;
  onBack: () => void;
}) {
  return (
    <div>
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={onBack}
          aria-label="Özete dön"
          className="rounded-lg border app-border px-2 py-1 text-sm app-muted transition hover:opacity-80"
        >
          ←
        </button>
        <h2 className="text-base font-bold app-heading">{data.symbol} teknik analizi</h2>
      </div>

      <div className="mt-4">
        <SectionHeader title="Göstergeler" summary={data.indicator_summary} />
        <div className="overflow-hidden rounded-xl border app-border">
          {data.indicators.map((indicator, index) => (
            <div
              key={indicator.key}
              className={`flex items-center justify-between gap-3 px-3 py-2 text-sm ${
                index % 2 === 1 ? "bg-[var(--color-surface-muted)]" : ""
              }`}
            >
              <span className="app-heading">{indicator.label}</span>
              <span className="ml-auto tabular-nums app-muted">
                {formatIndicatorValue(indicator.value)}
              </span>
              <SignalBadge signal={indicator.signal} />
            </div>
          ))}
        </div>
      </div>

      <div className="mt-4">
        <SectionHeader title="Hareketli Ortalamalar" summary={data.moving_average_summary} />
        <div className="overflow-x-auto rounded-xl border app-border">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-[var(--color-surface-muted)] text-xs app-muted">
                <th className="px-3 py-2 text-left font-semibold">Periyot</th>
                <th className="px-3 py-2 text-right font-semibold">SMA</th>
                <th className="px-3 py-2 text-right font-semibold">EMA</th>
              </tr>
            </thead>
            <tbody>
              {data.moving_averages.map((average) => (
                <tr key={average.period} className="border-t app-border">
                  <td className="px-3 py-2 app-heading">{average.period}</td>
                  <td className="px-3 py-2 text-right">
                    <span className="mr-2 tabular-nums app-muted">
                      {formatIndicatorValue(average.sma)}
                    </span>
                    <SignalBadge signal={average.sma_signal} />
                  </td>
                  <td className="px-3 py-2 text-right">
                    <span className="mr-2 tabular-nums app-muted">
                      {formatIndicatorValue(average.ema)}
                    </span>
                    <SignalBadge signal={average.ema_signal} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <p className="mt-3 text-[11px] app-muted">
        Günlük mumlar · {data.candle_count} mum · veri: {formatDataTime(data.last_candle_ts)} ·
        Bu bilgiler yatırım tavsiyesi değildir.
      </p>
    </div>
  );
}
