"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import type { IdleCashBasketOption, IdleCashSuggestion } from "../../models/chat";

const riskLabels = { LOW: "Düşük", MEDIUM: "Orta", HIGH: "Yüksek" } as const;
const goalLabels = {
  LONG_TERM: "Uzun vadeli birikim",
  GROWTH: "Büyüme odaklı",
  MOMENTUM: "Momentum",
  LOW_VOLATILITY: "Düşük oynaklık",
} as const;

const assetClassLabels: Record<string, string> = {
  STOCK: "BIST hissesi",
  USA_STOCK: "ABD hissesi",
  EU_STOCK: "Avrupa hissesi",
  ETF: "ETF",
  GOLD: "Altın",
  COMMODITY: "Emtia",
  FOREX: "Döviz",
  CRYPTO: "Kripto varlık",
};

const tryFormatter = new Intl.NumberFormat("tr-TR", {
  style: "currency",
  currency: "TRY",
  maximumFractionDigits: 2,
});

const scoreComponentLabels: Record<string, string> = {
  yillik_performans: "Yıllık performans",
  haftalik_momentum: "Haftalık momentum",
  gunluk_momentum: "Günlük momentum",
  oynaklik: "Oynaklık",
  risk_profili: "Risk profili",
  profil_sinif_uyumu: "Profil-sınıf uyumu",
  hedef_sinif_uyumu: "Hedef-sınıf uyumu",
  mevcut_portfoy: "Mevcut portföy",
};

const suitabilityLabels = {
  HIGH: "Yüksek uygunluk",
  MEDIUM: "Orta uygunluk",
  LOW: "Düşük uygunluk",
} as const;

const suitabilityClasses = {
  HIGH: "bg-emerald-50 text-emerald-800",
  MEDIUM: "bg-amber-50 text-amber-800",
  LOW: "bg-slate-100 text-slate-700",
} as const;

export function IdleCashSuggestionModal({
  suggestion,
  onClose,
  title,
  subtitle,
  strategyLabel,
  metrics,
  backtest,
}: {
  suggestion: IdleCashSuggestion | null;
  onClose: () => void;
  title?: string;
  subtitle?: string;
  strategyLabel?: string;
  metrics?: IdleCashBasketOption["metrics"];
  backtest?: IdleCashBasketOption["backtest"];
}) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => setMounted(true), []);
  useEffect(() => {
    if (!suggestion) return;
    function closeOnEscape(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    document.addEventListener("keydown", closeOnEscape);
    return () => document.removeEventListener("keydown", closeOnEscape);
  }, [suggestion, onClose]);

  if (!mounted || !suggestion) return null;

  return createPortal(
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-950/55 p-4 backdrop-blur-[2px]"
      role="presentation"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <section
        role="dialog"
        aria-modal="true"
        aria-labelledby="idle-cash-title"
        className="flex max-h-[calc(100vh-2rem)] w-full max-w-4xl flex-col overflow-hidden rounded-2xl border app-card shadow-2xl"
      >
        <header className="flex items-start justify-between gap-4 border-b px-6 py-5">
          <div>
            <p className="mb-1 text-sm font-semibold text-[var(--color-primary)]">
              Kişiselleştirilmiş öneri
            </p>
            <h2 id="idle-cash-title" className="text-2xl font-bold">
              {title ?? (suggestion.mode === "basket" ? "Atıl bakiye için yatırım sepeti" : "Bakiyeye uygun tek varlık")}
            </h2>
            {subtitle && <p className="mt-2 text-sm text-[var(--color-muted)]">{subtitle}</p>}
            {strategyLabel && (
              <span className="mt-2 inline-flex rounded-full bg-[var(--color-soft)] px-3 py-1 text-xs font-semibold">
                {strategyLabel}
              </span>
            )}
            <p className="mt-2 text-sm text-[var(--color-muted)]">{suggestion.preference_summary}</p>
          </div>
          <button
            type="button"
            aria-label="Öneriyi kapat"
            className="rounded-lg px-3 py-1 text-2xl text-[var(--color-muted)] hover:bg-black/5"
            onClick={onClose}
          >
            ×
          </button>
        </header>

        <div className="overflow-y-auto px-6 py-5">
          <IdleCashSuggestionContent
            suggestion={suggestion}
            metrics={metrics}
            backtest={backtest}
          />
        </div>

        <footer className="flex flex-col-reverse gap-3 border-t px-6 py-4 sm:flex-row sm:justify-end">
          <button type="button" className="rounded-lg border px-5 py-3 font-semibold" onClick={onClose}>
            Kapat
          </button>
          <Link href="/market" onClick={onClose} className="rounded-lg app-primary px-5 py-3 text-center font-semibold">
            Sanal işlemlerde incele
          </Link>
        </footer>
      </section>
    </div>,
    document.body,
  );
}

export function IdleCashSuggestionContent({
  suggestion,
  metrics,
  backtest,
}: {
  suggestion: IdleCashSuggestion;
  metrics?: IdleCashBasketOption["metrics"];
  backtest?: IdleCashBasketOption["backtest"];
}) {
  return (
    <>
      <div className="mb-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Summary
          label={suggestion.balance_source === "idle_balance" ? "Atıl bakiye" : "Sanal bakiye"}
          value={tryFormatter.format(suggestion.available_balance)}
        />
        <Summary label="Önerilen toplam" value={tryFormatter.format(suggestion.estimated_total)} />
        <Summary label="Risk profili" value={riskLabels[suggestion.risk_profile]} />
        <Summary label="Hedef" value={goalLabels[suggestion.goal]} />
      </div>

      {metrics && (
        <div className="mb-5 rounded-xl border p-4 text-sm">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <Summary label="Sepet riski" value={riskLabels[metrics.risk_level]} />
            <Summary label="20 günlük oynaklık" value={`%${metrics.expected_volatility_20d_pct.toLocaleString("tr-TR")}`} />
            <Summary label="Çeşitlendirme" value={`${metrics.diversification_score.toLocaleString("tr-TR")} / 100`} />
            <Summary label="Dağılım" value={`${metrics.asset_class_count} sınıf · ${metrics.sector_count} sektör`} />
          </div>
          <div className="mt-3 flex flex-wrap gap-x-5 gap-y-1 text-xs text-[var(--color-muted)]">
            <span>Ortalama korelasyon: {metrics.average_correlation == null ? "Yeterli veri yok" : metrics.average_correlation.toLocaleString("tr-TR")}</span>
            <span>Bölge sayısı: {metrics.region_count}</span>
            <span>En yüksek tek varlık ağırlığı: %{metrics.largest_weight_pct.toLocaleString("tr-TR")}</span>
          </div>
        </div>
      )}

      {backtest && <BasketBacktestSummary backtest={backtest} />}

      <div className="space-y-3">
        {suggestion.items.map((item) => (
          <article key={item.asset_id} className="rounded-xl border p-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <div className="flex items-center gap-2">
                  <span className="rounded-md bg-[var(--color-primary)] px-2 py-1 text-sm font-bold text-white">
                    {item.symbol}
                  </span>
                  <h3 className="font-semibold">{item.name}</h3>
                </div>
                <p className="mt-2 text-sm text-[var(--color-muted)]">
                  {item.quantity.toLocaleString("tr-TR", { maximumFractionDigits: 6 })} birim · {assetClassLabels[item.asset_class] ?? item.asset_class} · referans {tryFormatter.format(item.reference_price)}
                </p>
                <p className="mt-1 text-xs text-[var(--color-muted)]">
                  {item.sector.replaceAll("_", " ")} · {item.region} · {item.currency}
                </p>
              </div>
              <div className="text-right">
                <p className="font-bold">{tryFormatter.format(item.estimated_amount)}</p>
                <p className="text-sm text-[var(--color-muted)]">
                  Sepetin %{item.weight_pct.toLocaleString("tr-TR")}
                </p>
                <span className={`mt-2 inline-flex rounded-full px-3 py-1 text-xs font-semibold ${suitabilityClasses[item.suitability_level]}`}>
                  {suitabilityLabels[item.suitability_level]}
                </span>
                <p className="mt-1 text-xs text-[var(--color-muted)]">
                  Bu hedefte {item.candidate_count} aday içinde {item.goal_rank}. sırada
                </p>
              </div>
            </div>
            <details className="mt-3 rounded-lg bg-[var(--color-soft)] p-3 text-xs">
              <summary className="cursor-pointer font-semibold">Hesaplama ayrıntısı</summary>
              <div className="mt-3 grid gap-2 sm:grid-cols-2">
                {Object.entries(item.score_components).map(([key, value]) => (
                  <div key={key} className="flex justify-between gap-3">
                    <span className="text-[var(--color-muted)]">{scoreComponentLabels[key] ?? key}</span>
                    <strong className={value < 0 ? "text-red-600" : value > 0 ? "text-emerald-700" : ""}>
                      {value > 0 ? "+" : ""}{value.toLocaleString("tr-TR", { maximumFractionDigits: 2 })}
                    </strong>
                  </div>
                ))}
              </div>
            </details>
            <ul className="mt-3 space-y-1 text-sm text-[var(--color-muted)]">
              {item.rationale.map((reason) => <li key={reason}>• {reason}</li>)}
            </ul>
          </article>
        ))}
      </div>

      <p className="mt-4 rounded-lg border border-blue-100 bg-blue-50 p-3 text-xs text-blue-900">
        Hedef içi uygunluk bir alım sinyali veya beklenen getiri değildir; varlıkları yalnızca seçilen hedefteki diğer adaylarla karşılaştırır.
      </p>

      <div className="mt-5 rounded-xl bg-[var(--color-soft)] p-4 text-sm">
        <div className="flex flex-wrap justify-between gap-2">
          <span>Dağıtım üst sınırı (%10 nakit tamponuyla)</span>
          <strong>{tryFormatter.format(suggestion.investable_amount)}</strong>
        </div>
        <div className="flex flex-wrap justify-between gap-2">
          <span>Sepet sonrası ayrılmamış bakiye</span>
          <strong>{tryFormatter.format(suggestion.unallocated_balance)}</strong>
        </div>
        <p className="mt-3 text-xs text-[var(--color-muted)]">{suggestion.disclaimer}</p>
      </div>
    </>
  );
}

function BasketBacktestSummary({ backtest }: { backtest: IdleCashBasketOption["backtest"] }) {
  const statusLabels = {
    SUFFICIENT: "Yeterli veri",
    LIMITED: "Sınırlı veri",
    INSUFFICIENT: "Yetersiz veri",
  } as const;
  const statusClasses = {
    SUFFICIENT: "bg-emerald-50 text-emerald-800",
    LIMITED: "bg-amber-50 text-amber-800",
    INSUFFICIENT: "bg-slate-100 text-slate-700",
  } as const;
  const pct = (value: number | null) => value == null
    ? "—"
    : `%${value.toLocaleString("tr-TR", { maximumFractionDigits: 2 })}`;

  return (
    <section className="mb-5 rounded-xl border p-4 text-sm" aria-label="Geçmiş performans simülasyonu">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h3 className="font-bold">Geçmiş performans simülasyonu</h3>
          <p className="mt-1 text-xs text-[var(--color-muted)]">
            {backtest.observation_count} ortak işlem günü
            {backtest.start_date && backtest.end_date
              ? ` · ${backtest.start_date} – ${backtest.end_date}`
              : ""}
          </p>
        </div>
        <span className={`rounded-full px-3 py-1 text-xs font-semibold ${statusClasses[backtest.status]}`}>
          {statusLabels[backtest.status]}
        </span>
      </div>

      {backtest.status !== "INSUFFICIENT" && (
        <>
          <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <Summary label="Maliyet sonrası getiri" value={pct(backtest.net_return_pct)} />
            <Summary label="Evren karşılaştırması" value={pct(backtest.benchmark_return_pct)} />
            <Summary label="En büyük düşüş" value={pct(backtest.max_drawdown_pct)} />
            <Summary label="Yıllıklandırılmış oynaklık" value={pct(backtest.annualized_volatility_pct)} />
          </div>
          <div className="mt-3 flex flex-wrap gap-x-5 gap-y-1 text-xs text-[var(--color-muted)]">
            <span>Fark: {pct(backtest.excess_return_pct)}</span>
            <span>Risk/getiri oranı: {backtest.risk_adjusted_return?.toLocaleString("tr-TR") ?? "—"}</span>
            <span>Tahmini maliyet etkisi: {pct(backtest.transaction_cost_impact_pct)}</span>
            <span>Ağırlık dengeleme: {backtest.rebalance_count} kez</span>
          </div>
          <p className="mt-2 text-xs text-[var(--color-muted)]">
            Karşılaştırma: {backtest.benchmark_label}
          </p>
        </>
      )}

      <p className="mt-3 rounded-lg bg-[var(--color-soft)] p-3 text-xs">{backtest.note}</p>
    </section>
  );
}

function Summary({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl bg-[var(--color-soft)] p-4">
      <p className="text-xs font-semibold uppercase tracking-wide text-[var(--color-muted)]">{label}</p>
      <p className="mt-1 text-lg font-bold">{value}</p>
    </div>
  );
}
