"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import type { IdleCashSuggestion } from "../../models/chat";

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

export function IdleCashSuggestionModal({
  suggestion,
  onClose,
  title,
  subtitle,
}: {
  suggestion: IdleCashSuggestion | null;
  onClose: () => void;
  title?: string;
  subtitle?: string;
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
          <IdleCashSuggestionContent suggestion={suggestion} />
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
}: {
  suggestion: IdleCashSuggestion;
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
              </div>
              <div className="text-right">
                <p className="font-bold">{tryFormatter.format(item.estimated_amount)}</p>
                <p className="text-sm text-[var(--color-muted)]">
                  Sepetin %{item.weight_pct.toLocaleString("tr-TR")}
                </p>
              </div>
            </div>
            <ul className="mt-3 space-y-1 text-sm text-[var(--color-muted)]">
              {item.rationale.map((reason) => <li key={reason}>• {reason}</li>)}
            </ul>
          </article>
        ))}
      </div>

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

function Summary({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl bg-[var(--color-soft)] p-4">
      <p className="text-xs font-semibold uppercase tracking-wide text-[var(--color-muted)]">{label}</p>
      <p className="mt-1 text-lg font-bold">{value}</p>
    </div>
  );
}
